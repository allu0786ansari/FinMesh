"""Per-member alert budgets (proposal Section 11.1, operating points).

At roughly one laundering transaction per thousand, a fixed 1% false-positive
rate floods analysts, so every bank works to a budget:

* ``fpr``: at most a share of the member's negative account-windows may be
  alerted. The threshold is fitted per member on an earlier partition
  (validation for test, train for validation) and applied unchanged later.
  Ties are broken by a deterministic pseudo-random key ``u`` (a hash of
  account and window): the threshold is a (score, u) pair and an alert needs
  (score, u) above it. Without this, a scorer with tied scores (counts,
  trees) either floods or raises nothing at the cut.
* ``per_1000_per_day``: each member alerts its top ``k`` account-windows in
  every window, with ``k = value / 1000 x accounts x window_hours / 24``. This
  is a rank rule; it needs no fitting and reads no labels.

Budgets are per member, so evidence sharing cannot raise recall simply by
adding alerts (proposal Section 8.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import polars as pl

BudgetKind = Literal["fpr", "per_1000_per_day"]


@dataclass(frozen=True)
class Budget:
    kind: BudgetKind
    value: float

    @property
    def name(self) -> str:
        if self.kind == "fpr":
            return f"fpr_{self.value:g}"
        return f"alerts_{self.value:g}_per_1000_per_day"


DEFAULT_BUDGETS: tuple[Budget, ...] = (
    Budget("fpr", 0.001),
    Budget("fpr", 0.0001),
    Budget("per_1000_per_day", 1.0),
)


TIE_SALT = 0x46494E4D45534800  # fixed: the tie-break key never changes between runs


def tie_key() -> pl.Expr:
    """Deterministic pseudo-random tie-break key in [0, 1) per (account, window)."""
    return (pl.struct("account", "window").hash(seed=TIE_SALT).cast(pl.Float64) / 2.0**64).alias(
        "u"
    )


def fit_thresholds(scored: pl.DataFrame, budget: Budget) -> pl.DataFrame:
    """Per-member (score, u) threshold from negatives of an earlier partition.

    ``scored`` needs ``member, account, window, score, label, masked``. With
    ``n`` negatives at a member, the threshold is the negative ranked
    ``floor(b n) + 1`` from the top in (score, u) order, so exactly
    ``floor(b n)`` negatives lie above it. Only that many rows are kept per
    member (``top_k``), never a full sort: 30 M training negatives fit easily.
    """
    if budget.kind != "fpr":
        raise ValueError("only fpr budgets are fitted")
    negative = (pl.col("label") == 0) & ~pl.col("masked")
    rows = []
    for member in sorted(scored["member"].unique().to_list()):
        # One member's negatives at a time: never a copy of the whole partition.
        sub = scored.filter((pl.col("member") == member) & negative).select("score", tie_key())
        if sub.height == 0:
            continue
        k = int(sub.height * budget.value) + 1
        top = sub.top_k(k, by=["score", "u"]).sort("score", "u", descending=True)
        last = top.row(top.height - 1, named=True)
        rows.append({"member": member, "threshold": last["score"], "threshold_u": last["u"]})
        del sub, top
    return pl.DataFrame(
        rows, schema={"member": pl.Int32, "threshold": pl.Float64, "threshold_u": pl.Float64}
    )


def apply_budget(
    scored: pl.DataFrame,
    budget: Budget,
    *,
    thresholds: pl.DataFrame | None = None,
    accounts_per_member: pl.DataFrame | None = None,
    window_hours: int | None = None,
) -> pl.DataFrame:
    """Add a boolean ``alert`` column to ``member, account, window, score`` rows."""
    if budget.kind == "fpr":
        if thresholds is None:
            raise ValueError("fpr budgets need thresholds fitted on an earlier partition")
        above = (pl.col("score") > pl.col("threshold")) | (
            (pl.col("score") == pl.col("threshold")) & (tie_key() > pl.col("threshold_u"))
        )
        return (
            scored.join(thresholds, on="member", how="left")
            .with_columns((pl.col("threshold").is_not_null() & above).alias("alert"))
            .drop("threshold", "threshold_u")
        )
    if accounts_per_member is None or window_hours is None:
        raise ValueError("per-day budgets need accounts per member and the window length")
    quota = accounts_per_member.select(
        "member",
        (pl.col("accounts") * budget.value / 1000 * window_hours / 24)
        .round()
        .cast(pl.Int64)
        .alias("k"),
    )
    # Rank inside each (member, window) by score, ties to the lower account id:
    # sort once, then a running count per group (cheaper than rank().over()).
    ranked = scored.sort(
        ["member", "window", "score", "account"], descending=[False, False, True, False]
    ).with_columns((pl.int_range(pl.len()).over("member", "window") + 1).alias("rank"))
    return (
        ranked.join(quota, on="member", how="left")
        .with_columns((pl.col("rank") <= pl.col("k").fill_null(0)).alias("alert"))
        .drop("rank", "k")
    )
