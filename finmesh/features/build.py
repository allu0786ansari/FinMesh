"""Build the current feature schema for every account-window of a federation (week 4).

Storage, per dataset, window length, federation option and schema version:

    data/parquet/<ds>/features_w6_B8_v<N>/{train,val,test}/feat_<slice>.parquet
    data/parquet/<ds>/features_w6_B8_v<N>/meta.json

Rows are exactly the evaluation universe's account-windows (finmesh.eval.
universe), split into the same account hash slices and sorted by member,
account, window, so a feature file and the matching label file line up row
for row and scores attach to labels without a join.

Passes:

1. **edges**: one streaming pass writes the label-free edge table.
2. **neighbourhood**: for each day-sized chunk of windows, load the chunk's
   edges plus the lookback, then for each member and window compute the
   member-view graph features; results are split by account slice.
3. **accounts**: for each account slice, both sides of its edges give the
   behaviour, graph and history features; the slice's neighbourhood rows are
   joined on, and the result is written per partition.

Test-partition features are written to the open area: they hold no labels,
and the seal (finmesh.eval.sealed) protects labels, not inputs.
"""

from __future__ import annotations

import json
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import polars as pl

from finmesh.data.lowmem import slices_for
from finmesh.data.splits import SplitPlan
from finmesh.eval.guard import FeatureFrame
from finmesh.eval.split_io import load_plan
from finmesh.features.account import account_features, legs_for_slice
from finmesh.features.edges import (
    chain_rates,
    currencies,
    pair_ratios,
    rate_report,
    write_edges,
)
from finmesh.features.neighbourhood import NEIGHBOURHOOD_COUNTS, window_features
from finmesh.features.schema import KEYS, FeatureSchema, load_schema
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak

PARTITIONS: tuple[str, ...] = ("train", "val", "test")
CHUNK_HOURS = 24
LEGS_PER_SUBSLICE = 1_000_000


@dataclass(frozen=True)
class FeatureLayout:
    paths: DatasetPaths
    window_hours: int
    option: str
    version: int

    @property
    def root(self) -> Path:
        return self.paths.parquet / f"features_w{self.window_hours}_{self.option}_v{self.version}"

    def partition_dir(self, partition: str) -> Path:
        return self.root / partition

    @property
    def meta(self) -> Path:
        return self.root / "meta.json"

    @property
    def work(self) -> Path:
        return self.root / "_work"


def window_partitions(plan: SplitPlan) -> dict[int, str]:
    """Partition of every window inside the observation (gap windows included)."""
    hours = plan.window_hours
    span = plan.observation.end - plan.observation.start
    out: dict[int, str] = {}
    for w in range(int(span.total_seconds() // (hours * 3600))):
        ws = plan.observation.start + timedelta(hours=w * hours)
        out[w] = next((p.name for p in plan.periods if p.start <= ws < p.end), "gap")
    return out


def _membership(paths: DatasetPaths, option: str) -> pl.DataFrame:
    path = paths.parquet / f"membership_{option}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run `finmesh g0 --dataset {paths.name}` first")
    return pl.read_parquet(path)


def slice_count(paths: DatasetPaths) -> int:
    """Same slicing rule as the evaluation universe: two sides per transaction."""
    rows = pl.scan_parquet(paths.transactions).select(pl.len()).collect(engine="streaming").item()
    return slices_for(2 * int(rows))


def _neighbourhood_pass(
    edges: Path,
    membership: pl.DataFrame,
    plan: SplitPlan,
    schema: FeatureSchema,
    slices: int,
    work: Path,
) -> dict[str, Any]:
    hours = plan.window_hours
    lookback = max(1, int(schema.params["lookback_hours"]) // hours)
    cap = int(schema.params["hub_degree_cap"])
    per_chunk = max(1, CHUNK_HOURS // hours)
    parts = window_partitions(plan)
    scored = sorted(w for w, p in parts.items() if p in PARTITIONS)
    members = sorted(membership["member"].unique().to_list())
    m = membership.lazy()
    seconds: dict[int, float] = defaultdict(float)
    visible_rows: dict[int, int] = defaultdict(int)
    rows_out = 0
    for d in range(slices):
        (work / f"s{d:03d}").mkdir(parents=True, exist_ok=True)
    if not scored:
        return {"lookback_windows": lookback, "cap": cap, "rows": 0, "members": {}}
    for first in range(scored[0], scored[-1] + 1, per_chunk):
        wins = [w for w in range(first, first + per_chunk) if w in set(scored)]
        if not wins:
            continue
        chunk = (
            pl.scan_parquet(edges)
            .filter(
                pl.col("window").is_between(wins[0] - lookback + 1, wins[-1])
                & (pl.col("src") != pl.col("dst"))
            )
            .select("src", "dst", "from_bank", "to_bank", "window")
            .unique(subset=["src", "dst", "window"])
            .join(
                m.select(pl.col("bank").alias("from_bank"), pl.col("member").alias("src_member")),
                on="from_bank",
                how="left",
            )
            .join(
                m.select(pl.col("bank").alias("to_bank"), pl.col("member").alias("dst_member")),
                on="to_bank",
                how="left",
            )
            .select("src", "dst", "src_member", "dst_member", "window")
            .collect(engine="streaming")
        )
        results = []
        for member in members:
            t0 = time.perf_counter()
            vis = chunk.filter((pl.col("src_member") == member) | (pl.col("dst_member") == member))
            visible_rows[member] += vis.height
            for w in wins:
                f = window_features(vis, member, w, lookback, cap)
                if f.height:
                    results.append(
                        f.rename({"a": "account"}).with_columns(pl.lit(w, pl.Int32).alias("window"))
                    )
            seconds[member] += time.perf_counter() - t0
        if results:
            out = pl.concat(results)
            rows_out += out.height
            for d in range(slices):
                part = out.filter(pl.col("account") % slices == d)
                if part.height:
                    part.write_parquet(work / f"s{d:03d}" / f"w{first:04d}.parquet")
        del chunk, results
    return {
        "lookback_windows": lookback,
        "cap": cap,
        "rows": rows_out,
        "members": {
            int(k): {"seconds": round(seconds[k], 2), "visible_edge_rows": visible_rows[k]}
            for k in members
        },
    }


def _neighbourhood_for_slice(work: Path, d: int) -> pl.DataFrame:
    files = sorted((work / f"s{d:03d}").glob("*.parquet"))
    if not files:
        return pl.DataFrame(
            schema={
                "account": pl.UInt64,
                "window": pl.Int32,
                **{c: pl.UInt32 for c in NEIGHBOURHOOD_COUNTS},
            }
        )
    return pl.concat([pl.read_parquet(f) for f in files])


def _finish(
    acct: pl.DataFrame, part_of: pl.DataFrame, nbr: pl.DataFrame, schema: FeatureSchema
) -> pl.DataFrame:
    """Account features of scored windows, neighbourhood joined on, in schema dtypes."""
    full = (
        acct.join(part_of, on="window", how="left")
        .filter(pl.col("partition").is_in(PARTITIONS))
        .join(nbr, on=["account", "window"], how="left")
        .with_columns(pl.col(c).fill_null(0) for c in NEIGHBOURHOOD_COUNTS)
    )
    return schema.cast(full).with_columns(full["partition"])


def build_features(paths: DatasetPaths, option: str = "B8") -> dict[str, Any]:
    """Write the current feature schema for every account-window; return the build summary."""
    schema = load_schema()
    plan = load_plan(paths)
    layout = FeatureLayout(paths, plan.window_hours, option, schema.version)
    membership = _membership(paths, option)
    if layout.root.exists():
        shutil.rmtree(layout.root)
    layout.work.mkdir(parents=True)
    timings: dict[str, Any] = {}

    with AnonPeak() as anon:
        t0 = time.perf_counter()
        names = currencies(paths.transactions, plan)
        ratios = pair_ratios(paths.transactions, plan)
        rates = chain_rates(names, ratios, str(schema.params["reference_currency"]))
        edges = layout.work / "edges.parquet"
        edge_rows = write_edges(paths.transactions, plan, edges, rates, names)
        timings["edges"] = {"seconds": round(time.perf_counter() - t0, 1)}
    timings["edges"]["peak_anon_mb"] = anon.mb

    slices = slice_count(paths)
    with AnonPeak() as anon:
        t0 = time.perf_counter()
        nb = _neighbourhood_pass(edges, membership, plan, schema, slices, layout.work)
        timings["neighbourhood"] = {"seconds": round(time.perf_counter() - t0, 1)}
    timings["neighbourhood"]["peak_anon_mb"] = anon.mb

    parts = window_partitions(plan)
    part_of = pl.DataFrame(
        {"window": list(parts), "partition": list(parts.values())},
        schema={"window": pl.Int32, "partition": pl.String},
    )
    for p in PARTITIONS:
        layout.partition_dir(p).mkdir(parents=True, exist_ok=True)
    counts = {p: 0 for p in PARTITIONS}
    tolerance = float(schema.params["delay_tolerance_hours"])
    history = max(1, int(schema.params["history_hours"]) // plan.window_hours)
    # Sub-slices of about LEGS_PER_SUBSLICE legs keep the per-counterparty
    # group-bys near 1 GB however large the dataset (4 M legs took 3.7 GB).
    sub = max(1, -(-2 * edge_rows // (slices * LEGS_PER_SUBSLICE)))
    with AnonPeak() as anon:
        t0 = time.perf_counter()
        for d in range(slices):
            nbr = _neighbourhood_for_slice(layout.work, d)
            pieces = []
            for j in range(sub):
                legs = legs_for_slice(edges, membership, slices, d, sub, j)
                acct = account_features(legs, tolerance, history)
                del legs
                pieces.append(_finish(acct, part_of, nbr, schema))
                del acct
            full = pl.concat(pieces)
            del pieces, nbr
            for p in PARTITIONS:
                frame = full.filter(pl.col("partition") == p).drop("partition").sort(*KEYS)
                FeatureFrame(frame)  # refuses label columns, by construction
                frame.write_parquet(layout.partition_dir(p) / f"feat_{d:03d}.parquet")
                counts[p] += frame.height
            del full
        timings["accounts"] = {"seconds": round(time.perf_counter() - t0, 1)}
    timings["accounts"]["peak_anon_mb"] = anon.mb
    shutil.rmtree(layout.work)

    meta: dict[str, Any] = {
        "dataset": paths.name,
        "option": option,
        "window_hours": plan.window_hours,
        "schema_version": schema.version,
        "schema_sha256": schema.sha256,
        "slices": slices,
        "subslices": sub,
        # Windows before this one have incomplete history or lookback: training burn-in.
        "history_complete_from_window": max(history, nb["lookback_windows"]),
        "edge_rows": edge_rows,
        "currencies": rate_report(ratios, rates),
        "neighbourhood": nb,
        "rows": counts,
        "timings": timings,
    }
    layout.meta.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


class FeatureStore:
    """Read features per partition, in the universe's row order."""

    def __init__(self, paths: DatasetPaths, option: str = "B8") -> None:
        schema = load_schema()
        plan = load_plan(paths)
        self.schema = schema
        self.layout = FeatureLayout(paths, plan.window_hours, option, schema.version)
        if not self.layout.meta.exists():
            raise FileNotFoundError(
                f"{self.layout.meta} missing; run `finmesh features --dataset {paths.name}` first"
            )
        self.meta: dict[str, Any] = json.loads(self.layout.meta.read_text())
        if self.meta["schema_sha256"] != schema.sha256:
            raise RuntimeError(
                "features were built with a different schema file; rebuild them with "
                f"`finmesh features --dataset {paths.name}`"
            )

    def partition(self, partition: str, columns: list[str] | None = None) -> FeatureFrame:
        files = sorted(self.layout.partition_dir(partition).glob("feat_*.parquet"))
        cols = None if columns is None else [*KEYS, *columns]
        return FeatureFrame(pl.concat([pl.read_parquet(f, columns=cols) for f in files]))
