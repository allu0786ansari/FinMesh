"""Account-window labels: what every detector is scored against (proposal Section 9).

The evaluation unit is an **account-window**: one account held at a federation
member, in one window, in which it sent or received at least one transaction
(an inactive account is never scored, as in a bank's monitoring). Its label:

* **positive** if it touches a laundering transaction that is not masked;
* **masked** (neither positive nor negative) if it touches only masked
  laundering transactions, i.e. legs of a scheme assigned to another partition;
* **negative** otherwise.

Scheme-level metrics also need, per scheme, its account-windows in its own
partition (``scheme_windows``) and a summary row (``schemes``).

Storage, per dataset, window length and federation option:

    data/parquet/<ds>/eval_w6_B8/{train,val}/universe_<slice>.parquet
    data/parquet/<ds>/eval_w6_B8/{train,val}/scheme_windows.parquet, schemes.parquet
    data/parquet/<ds>/eval_w6_B8/accounts_per_member.parquet, meta.json
    data/sealed/<ds>/eval_w6_B8/test/...        (only through finmesh.eval.sealed)

Accounts are 64-bit hashes of the ``<bank>:<account>`` key (as in
``finmesh.data.lowmem``); the universe is built in hash slices so HI-Medium
(about 24 M account-windows) stays within a few hundred MB.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from finmesh.data.consortium import ConsortiumSpec, bank_sizes
from finmesh.data.lowmem import hashed_key, slices_for
from finmesh.data.splits import partition_expr, window_index_expr
from finmesh.eval.split_io import load_plan
from finmesh.paths import DatasetPaths

EVAL_PARTITIONS: tuple[str, ...] = ("train", "val", "test")

# Amendment A9: a positive account-window with at least INCIDENTAL_MIN_LEGS legs,
# of which under INCIDENTAL_MAX_SHARE are unmasked laundering legs, is a busy
# account a scheme passed through once. It is masked in the primary label and
# positive in the "touch" sensitivity variant.
INCIDENTAL_MIN_LEGS = 20
INCIDENTAL_MAX_SHARE = 0.1
LABEL_VARIANTS: tuple[str, ...] = ("primary", "touch")


def incidental_expr() -> pl.Expr:
    """Over aggregated columns ``pos``, ``tx`` and ``bad_legs``."""
    return (
        pl.col("pos")
        & (pl.col("tx") >= INCIDENTAL_MIN_LEGS)
        & (pl.col("bad_legs") < INCIDENTAL_MAX_SHARE * pl.col("tx"))
    )


SEALED_PARTITIONS: frozenset[str] = frozenset({"test"})


def sealed_root(paths: DatasetPaths) -> Path:
    return paths.root / "sealed" / paths.name


@dataclass(frozen=True)
class EvalLayout:
    paths: DatasetPaths
    window_hours: int
    option: str

    @property
    def tag(self) -> str:
        return f"eval_w{self.window_hours}_{self.option}"

    @property
    def open_root(self) -> Path:
        return self.paths.parquet / self.tag

    @property
    def sealed_root(self) -> Path:
        return sealed_root(self.paths) / self.tag

    def partition_dir(self, partition: str) -> Path:
        base = self.sealed_root if partition in SEALED_PARTITIONS else self.open_root
        return base / partition

    @property
    def meta(self) -> Path:
        return self.open_root / "meta.json"

    @property
    def sealed_meta(self) -> Path:
        return self.sealed_root / "meta.json"

    @property
    def accounts_per_member(self) -> Path:
        return self.open_root / "accounts_per_member.parquet"


def _membership(paths: DatasetPaths, option: str) -> pl.DataFrame:
    path = paths.parquet / f"membership_{option}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run `finmesh g0 --dataset {paths.name}` first")
    return pl.read_parquet(path)


def _scheme_links_with_partition(paths: DatasetPaths, window_hours: int) -> pl.DataFrame:
    assignment = pl.read_parquet(paths.parquet / f"scheme_assignment_w{window_hours}.parquet")
    return pl.read_parquet(paths.scheme_links).join(
        assignment.select(
            "scheme_id", pl.col("partition").cast(pl.String).alias("scheme_partition")
        ),
        on="scheme_id",
        how="left",
    )


def _sides(paths: DatasetPaths, plan: Any, links: pl.DataFrame) -> pl.LazyFrame:
    """Two rows per transaction (sender side, receiver side) inside train/val/test."""
    tx = (
        pl.scan_parquet(paths.transactions)
        .select("tx_id", "timestamp", "from_bank", "to_bank", "src_key", "dst_key", "is_laundering")
        .with_columns(
            partition_expr(plan).cast(pl.String).alias("partition"),
            window_index_expr(plan).alias("window"),
        )
        .filter(
            (pl.col("partition") == "train")
            | (pl.col("partition") == "val")
            | (pl.col("partition") == "test")
        )
        .join(links.lazy().select("tx_id", "scheme_partition"), on="tx_id", how="left")
        .with_columns(
            (
                pl.col("scheme_partition").is_not_null()
                & (pl.col("scheme_partition") != pl.col("partition"))
            ).alias("tx_masked"),
            (pl.col("is_laundering") == 1).alias("bad"),
        )
    )
    common = ("window", "partition", "bad", "tx_masked")
    return pl.concat(
        [
            tx.select(
                pl.col("from_bank").alias("bank"), hashed_key("src_key").alias("account"), *common
            ),
            tx.select(
                pl.col("to_bank").alias("bank"), hashed_key("dst_key").alias("account"), *common
            ),
        ]
    )


def build_universe(paths: DatasetPaths, option: str = "B8") -> dict[str, Any]:
    """Write account-window labels for every partition; return counts per partition."""
    plan = load_plan(paths)
    layout = EvalLayout(paths, plan.window_hours, option)
    membership = _membership(paths, option)
    links = _scheme_links_with_partition(paths, plan.window_hours)
    rows = pl.scan_parquet(paths.transactions).select(pl.len()).collect(engine="streaming").item()
    n_slices = slices_for(2 * rows)

    for p in EVAL_PARTITIONS:
        d = layout.partition_dir(p)
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("universe_*.parquet"):
            old.unlink()

    sides = _sides(paths, plan, links)
    for i in range(n_slices):
        part = (
            sides.filter(pl.col("account") % n_slices == i)
            .group_by("bank", "account", "window", "partition")
            .agg(
                pl.len().alias("tx"),
                (pl.col("bad") & ~pl.col("tx_masked")).any().alias("pos"),
                (pl.col("bad") & pl.col("tx_masked")).any().alias("masked_bad"),
                (pl.col("bad") & ~pl.col("tx_masked")).sum().alias("bad_legs"),
            )
            .join(membership.lazy(), on="bank", how="inner")
            .with_columns(incidental_expr().alias("incidental"))
            .select(
                "member",
                "bank",
                "account",
                pl.col("window").cast(pl.Int32),
                "partition",
                pl.col("tx").cast(pl.UInt32),
                (pl.col("pos") & ~pl.col("incidental")).cast(pl.Int8).alias("label"),
                ((pl.col("masked_bad") & ~pl.col("pos")) | pl.col("incidental")).alias("masked"),
                "incidental",
            )
            .collect(engine="streaming")
        )
        for p in EVAL_PARTITIONS:
            # Sorted by member, account, window: deterministic, and the same row
            # order as the feature files (finmesh.features.build), so scores
            # attach to labels without a join.
            part.filter(pl.col("partition") == p).drop("partition").sort(
                "member", "account", "window"
            ).write_parquet(layout.partition_dir(p) / f"universe_{i:03d}.parquet")
        del part

    _write_scheme_tables(paths, plan, layout, membership, links)
    _mark_incidental_scheme_windows(layout)
    sizes = bank_sizes(paths.transactions)
    accounts = (
        sizes.join(membership, on="bank", how="inner")
        .group_by("member")
        .agg(pl.col("accounts").sum())
        .sort("member")
    )
    accounts.write_parquet(layout.accounts_per_member)

    counts = {p: partition_counts(layout, p) for p in EVAL_PARTITIONS}
    open_meta = {
        "dataset": paths.name,
        "option": option,
        "spec": ConsortiumSpec.parse(option).name,
        "window_hours": plan.window_hours,
        "slices": n_slices,
        "label_rule": {
            "positive": "touches an unmasked laundering leg and is not incidental (amendment A9)",
            "incidental_min_legs": INCIDENTAL_MIN_LEGS,
            "incidental_max_share": INCIDENTAL_MAX_SHARE,
        },
        "partition_hours": {p: plan.period(p).hours for p in EVAL_PARTITIONS},
        "partition_windows": {p: _window_range(plan, p) for p in EVAL_PARTITIONS},
        "counts": {p: counts[p] for p in EVAL_PARTITIONS if p not in SEALED_PARTITIONS},
        "members": accounts.to_dicts(),
    }
    layout.meta.write_text(json.dumps(open_meta, indent=2) + "\n")
    layout.sealed_meta.parent.mkdir(parents=True, exist_ok=True)
    layout.sealed_meta.write_text(json.dumps({"counts": {"test": counts["test"]}}, indent=2) + "\n")
    return open_meta


def _window_range(plan: Any, partition: str) -> list[int]:
    period = plan.period(partition)
    start = int(
        (period.start - plan.observation.start).total_seconds() // (plan.window_hours * 3600)
    )
    return [start, start + plan.windows_in(partition) - 1]


def _write_scheme_tables(
    paths: DatasetPaths,
    plan: Any,
    layout: EvalLayout,
    membership: pl.DataFrame,
    links: pl.DataFrame,
) -> None:
    schemes = pl.read_parquet(paths.schemes).select("scheme_id", "pattern")
    own = (
        pl.scan_parquet(paths.transactions)
        .select("tx_id", "timestamp", "from_bank", "to_bank", "src_key", "dst_key")
        .join(links.lazy(), on="tx_id", how="inner")
        .with_columns(
            partition_expr(plan).cast(pl.String).alias("partition"),
            window_index_expr(plan).alias("window"),
        )
        .filter(pl.col("partition") == pl.col("scheme_partition"))
        .collect(engine="streaming")
    )
    sides = pl.concat(
        [
            own.select(
                "scheme_id",
                "partition",
                "window",
                pl.col("from_bank").alias("bank"),
                hashed_key("src_key").alias("account"),
            ),
            own.select(
                "scheme_id",
                "partition",
                "window",
                pl.col("to_bank").alias("bank"),
                hashed_key("dst_key").alias("account"),
            ),
        ]
    ).unique()
    sides = sides.join(membership, on="bank", how="left").with_columns(
        pl.col("window").cast(pl.Int32)
    )
    for p in EVAL_PARTITIONS:
        sw = sides.filter(pl.col("partition") == p).drop("partition")
        member_sw = sw.filter(pl.col("member").is_not_null())
        member_sw.select("scheme_id", "member", "bank", "account", "window").write_parquet(
            layout.partition_dir(p) / "scheme_windows.parquet"
        )
        summary = (
            sw.group_by("scheme_id")
            .agg(
                pl.col("window").min().alias("first_window"),
                pl.col("window").max().alias("last_window"),
                pl.col("account").n_unique().alias("accounts"),
                pl.col("member").drop_nulls().n_unique().alias("members"),
                pl.col("account")
                .filter(pl.col("member").is_not_null())
                .n_unique()
                .alias("member_accounts"),
            )
            .join(schemes, on="scheme_id", how="left")
            .sort("scheme_id")
        )
        summary.write_parquet(layout.partition_dir(p) / "schemes.parquet")


def _mark_incidental_scheme_windows(layout: EvalLayout) -> None:
    """Flag scheme account-windows that are incidental; the primary label ignores them."""
    for p in EVAL_PARTITIONS:
        d = layout.partition_dir(p)
        flagged = (
            pl.scan_parquet(d / "universe_*.parquet")
            .filter(pl.col("incidental"))
            .select("account", "window", pl.lit(True).alias("incidental"))
            .collect(engine="streaming")
        )
        sw = pl.read_parquet(d / "scheme_windows.parquet").drop("incidental", strict=False)
        sw.join(flagged, on=["account", "window"], how="left").with_columns(
            pl.col("incidental").fill_null(False)
        ).write_parquet(d / "scheme_windows.parquet")


def partition_counts(layout: EvalLayout, partition: str) -> dict[str, int]:
    u = pl.scan_parquet(layout.partition_dir(partition) / "universe_*.parquet")
    row = (
        u.select(
            pl.len().alias("account_windows"),
            pl.col("label").sum().alias("positives"),
            pl.col("masked").sum().alias("masked"),
            pl.col("incidental").sum().alias("incidental"),
            pl.col("account").n_unique().alias("accounts"),
        )
        .collect(engine="streaming")
        .row(0, named=True)
    )
    schemes = pl.read_parquet(layout.partition_dir(partition) / "schemes.parquet")
    row["schemes"] = schemes.height
    row["multi_member_schemes"] = int((schemes["members"] >= 2).sum())
    return {k: int(v or 0) for k, v in row.items()}
