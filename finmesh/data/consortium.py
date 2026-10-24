"""Who the federation members are (proposal Section 7.2, decided at Gate G0).

AMLworld has tens of thousands of bank IDs, most of them small (week-1
finding 3), so "four to eight real banks" covers only a few percent of
accounts. Two label-free families of membership are compared at G0:

* **Option A, real banks.** The top ``k`` bank IDs by number of accounts
  (week-1 finding 4: accounts, not transaction volume, so that hub bank 70
  with 15 accounts and 9% of traffic is not picked first). Every other bank
  is the "outside world": its transactions with members are visible to the
  member involved, but it cannot be queried.
* **Option B, grouped institutions.** Bank IDs are treated as branches and
  every one is assigned to one of ``k`` institutions, balancing the number of
  accounts per institution (longest-processing-time greedy: banks in
  decreasing size order, each to the currently smallest institution). Every
  account belongs to some member; nothing is outside.

Ties are broken by bank ID, so membership is deterministic and never depends
on labels.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl

from finmesh.data.lowmem import distinct_keys_per_group, hashed_key

Option = Literal["A", "B"]


@dataclass(frozen=True, order=True)
class ConsortiumSpec:
    option: Option
    k: int

    @property
    def name(self) -> str:
        return f"{self.option}{self.k}"

    @classmethod
    def parse(cls, text: str) -> ConsortiumSpec:
        option, k = text[0].upper(), int(text[1:])
        if option not in ("A", "B") or k < 2:
            raise ValueError(f"bad consortium spec {text!r}; use A8, B8, ...")
        return cls(option=option, k=k)  # type: ignore[arg-type]


# Candidates compared at G0. B8 matches the proposal's "four to eight" members.
CANDIDATES: tuple[ConsortiumSpec, ...] = (
    ConsortiumSpec("A", 8),
    ConsortiumSpec("A", 16),
    ConsortiumSpec("A", 32),
    ConsortiumSpec("A", 64),
    ConsortiumSpec("B", 4),
    ConsortiumSpec("B", 8),
    ConsortiumSpec("B", 16),
)
DEFAULT_GROUPED = ConsortiumSpec("B", 8)


def bank_sizes(transactions: Path) -> pl.DataFrame:
    """Accounts owned and transactions touched per bank, ranked largest first.

    An account belongs to the bank in its key, so a bank's accounts are the
    distinct keys appearing on its side of any transaction.
    """
    lf = pl.scan_parquet(transactions)
    rows = lf.select(pl.len()).collect(engine="streaming").item()
    owned = pl.concat(
        [
            lf.select(pl.col("from_bank").alias("bank"), hashed_key("src_key").alias("key")),
            lf.select(pl.col("to_bank").alias("bank"), hashed_key("dst_key").alias("key")),
        ]
    )
    accounts = distinct_keys_per_group(owned, "bank", rows=2 * rows, out="accounts").lazy()
    touching = (
        pl.concat(
            [
                lf.select(pl.col("from_bank").alias("bank")),
                lf.filter(pl.col("from_bank") != pl.col("to_bank")).select(
                    pl.col("to_bank").alias("bank")
                ),
            ]
        )
        .group_by("bank")
        .agg(pl.len().alias("tx_touching"))
    )
    return (
        accounts.join(touching, on="bank", how="left")
        .with_columns(pl.col("tx_touching").fill_null(0))
        .sort(["accounts", "bank"], descending=[True, False])
        .with_row_index("rank", offset=1)
        .collect(engine="streaming")
    )


def build_membership(sizes: pl.DataFrame, spec: ConsortiumSpec) -> pl.DataFrame:
    """Return ``bank, member`` (member 0..k-1); banks absent from it are outside."""
    ranked = sizes.sort(["accounts", "bank"], descending=[True, False])
    if spec.option == "A":
        return ranked.head(spec.k).select(
            "bank", pl.int_range(0, pl.len(), dtype=pl.Int32).alias("member")
        )
    heap: list[tuple[int, int]] = [(0, m) for m in range(spec.k)]
    banks: list[int] = []
    members: list[int] = []
    for bank, accounts in ranked.select("bank", "accounts").iter_rows():
        load, member = heapq.heappop(heap)
        banks.append(int(bank))
        members.append(member)
        heapq.heappush(heap, (load + int(accounts), member))
    return pl.DataFrame(
        {"bank": banks, "member": members}, schema={"bank": pl.Int64, "member": pl.Int32}
    )


def membership_summary(sizes: pl.DataFrame, membership: pl.DataFrame) -> pl.DataFrame:
    """Accounts, banks and transactions per member."""
    return (
        sizes.join(membership, on="bank", how="inner")
        .group_by("member")
        .agg(
            pl.len().alias("banks"),
            pl.col("accounts").sum().alias("accounts"),
            pl.col("tx_touching").sum().alias("tx_touching_upper_bound"),
            pl.col("bank").sort_by("accounts", descending=True).first().alias("largest_bank"),
        )
        .sort("member")
    )
