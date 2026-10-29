"""Indirect influence of an account on its neighbours' features (week 11; A18).

The account unit's DP guarantee bounds what an account's own windows do to the
model. Graph features of *other* accounts are computed from shared
transactions, so an account also moves its neighbours' rows, and through
2-hop features (cycles, scatter-gather, counterparty degrees) their
neighbours' rows. The proposal asks for this to be measured by recomputing
features with accounts removed, and mitigated by a degree cap.

Procedure, for the member-view features and for the degree-capped variant:

1. Sample :data:`SAMPLE` training accounts by a fixed hash, half of them with
   at least one laundering training row (influence matters most there).
2. Rebuild every feature with all their transactions removed.
3. Compare training-partition rows: a row of another account *changed* if any
   feature differs.
4. Attribute changed accounts to each removed account within two hops of it
   in the training-period graph (an account near several removed accounts
   counts for each, so the attribution is conservative).

The **empirical group size** of an account is 1 (its own bag) plus the number
of other accounts at the same member whose rows it changes: under the account
unit, DP-SGD's guarantee for the account including its indirect influence is
the group guarantee for that many units, (g ε, g e^((g-1)ε) δ).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import polars as pl

from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.features.build import FeatureStore, build_features
from finmesh.features.variants import DEFAULT_DEGREE_CAP, degree_cap, remove_accounts
from finmesh.fusion.local import link_edges
from finmesh.paths import DatasetPaths
from finmesh.reporting import table
from finmesh.training.baselines import feature_sets
from finmesh.training.data import training_rows, training_windows

SAMPLE = 200
QUANTILES = (0.5, 0.9, 0.99, 1.0)
EPSILONS = (1.0, 3.0, 10.0)


def sample_accounts(fit_account: np.ndarray, fit_y: np.ndarray, n: int = SAMPLE) -> np.ndarray:
    """Half laundering-touched accounts, half others, each by a fixed hash."""
    frame = (
        pl.DataFrame({"account": fit_account, "y": fit_y})
        .group_by("account")
        .agg(pl.col("y").max())
    )
    frame = frame.with_columns(pl.col("account").hash(seed=909).alias("h")).sort("h")
    pos = frame.filter(pl.col("y") == 1)["account"].head(n // 2)
    neg = frame.filter(pl.col("y") == 0)["account"].head(n - len(pos))
    return np.concatenate([pos.to_numpy(), neg.to_numpy()]).astype(np.uint64)


def _changed_accounts(a: FeatureStore, b: FeatureStore, removed: set[int]) -> pl.DataFrame:
    """Other accounts with a training row whose features differ (account, member, rows).

    Compared slice by slice: the builds line up row for row.
    """
    gone = pl.DataFrame({"account": list(removed)}, schema={"account": pl.UInt64})
    parts = []
    files_a = sorted(a.layout.partition_dir("train").glob("feat_*.parquet"))
    files_b = sorted(b.layout.partition_dir("train").glob("feat_*.parquet"))
    for fa_path, fb_path in zip(files_a, files_b, strict=True):
        fa, fb = pl.read_parquet(fa_path), pl.read_parquet(fb_path)
        cols = [c for c in fa.columns if c not in ("member", "account", "window")]
        diff = (
            (
                fa.select(cols).fill_null(-1.0).fill_nan(-1.0)
                != fb.select(cols).fill_null(-1.0).fill_nan(-1.0)
            )
            .select(pl.any_horizontal(pl.all()))
            .to_series()
        )
        parts.append(fa.select("member", "account").filter(diff))
        del fa, fb
    changed = pl.concat(parts).join(gone, on="account", how="anti")
    return changed.group_by("account", "member").agg(pl.len().alias("rows"))


def _two_hop(
    paths: DatasetPaths, plan: Any, first: int, last: int, lookback: int, accounts: np.ndarray
) -> pl.DataFrame:
    """(u, v) for v within two hops of u (either direction), v != u.

    Only edges touching the removed accounts, then their neighbours, are read.
    """
    u = pl.DataFrame({"account": accounts}, schema={"account": pl.UInt64})

    def hop(frontier: pl.DataFrame) -> pl.DataFrame:
        e = link_edges(paths.transactions, plan, first, last, lookback, touching=frontier)
        und = pl.concat(
            [
                e.select(pl.col("src").alias("x"), pl.col("dst").alias("y")),
                e.select(pl.col("dst").alias("x"), pl.col("src").alias("y")),
            ]
        ).unique()
        return und.join(frontier.select(pl.col("account").alias("x")), on="x", how="semi")

    one = hop(u).rename({"x": "u", "y": "v"})
    nbrs = one.select(pl.col("v").alias("account")).unique()
    two = one.join(hop(nbrs).rename({"x": "v", "y": "w"}), on="v").select(
        "u", pl.col("w").alias("v")
    )
    return pl.concat([one, two]).filter(pl.col("u") != pl.col("v")).unique()


def _summary(sizes: np.ndarray) -> dict[str, float]:
    return {f"q{int(q * 100)}": float(np.quantile(sizes, q)) for q in QUANTILES} | {
        "mean": float(sizes.mean())
    }


def run_influence(
    paths: DatasetPaths, option: str = "B8", cap: int = DEFAULT_DEGREE_CAP, sample: int = SAMPLE
) -> dict[str, Any]:
    t0 = time.perf_counter()
    plan = load_plan(paths)
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    windows = training_windows(store, feats)
    cols = feature_sets()["all"]
    fit, _ = training_rows(store, feats, cols, windows, 0)
    assert fit.account is not None
    removed = sample_accounts(fit.account, fit.y, sample)
    units = pl.DataFrame(
        {"u": fit.account, "u_member": fit.member}, schema={"u": pl.UInt64, "u_member": pl.Int64}
    ).unique("u")
    trained = units.select(pl.col("u").alias("account"))  # accounts with training units
    lookback = int(feats.meta["neighbourhood"]["lookback_windows"])
    hood = _two_hop(paths, plan, windows.burn_in, windows.train_last, lookback, removed)
    out: dict[str, Any] = {
        "dataset": paths.name,
        "sample": len(removed),
        "cap": cap,
        "views": {},
    }
    cap_tag, cap_fn = degree_cap(cap)
    variants = {
        "member": (None, "member"),
        cap_tag: ((cap_tag, cap_fn), cap_tag),
    }
    for name, (base_variant, base_view) in variants.items():
        if base_variant is not None and not _has_view(paths, option, base_view):
            build_features(paths, option, variant=base_variant)
        rm_tag, rm_fn = remove_accounts(removed.tolist(), f"{base_view}-minus{len(removed)}")
        if base_variant is None:
            build_features(paths, option, variant=(rm_tag, rm_fn))
        else:
            _, cfn = base_variant

            def both(path: Any, cfn: Any = cfn, rm_fn: Any = rm_fn) -> dict[str, Any]:
                info = cfn(path)
                return {**info, **{f"then_{k}": v for k, v in rm_fn(path).items()}}

            build_features(paths, option, variant=(rm_tag, both))
        changed = _changed_accounts(
            FeatureStore(paths, option, base_view),
            FeatureStore(paths, option, rm_tag),
            set(removed.tolist()),
        ).join(trained, on="account", how="semi")  # only accounts that train the model
        per = (
            hood.join(changed, left_on="v", right_on="account")
            .join(units, on="u", how="left")
            .group_by("u")
            .agg(
                pl.len().alias("accounts_any"),
                (pl.col("member") == pl.col("u_member")).sum().alias("accounts_same"),
                pl.col("rows").sum().alias("rows"),
            )
        )
        sizes = (
            pl.DataFrame({"u": removed}, schema={"u": pl.UInt64})
            .join(per, on="u", how="left")
            .fill_null(0)
        )
        g = 1 + sizes["accounts_same"].to_numpy().astype(np.float64)
        out["views"][name] = {
            "changed_accounts": int(changed.height),
            "changed_rows": int(changed["rows"].sum() or 0),
            "group_size": _summary(g),
            "other_accounts_any_member": _summary(sizes["accounts_any"].to_numpy().astype(float)),
            "rows_changed_per_account": _summary(sizes["rows"].to_numpy().astype(float)),
            "group_epsilon": {
                f"{e:g}": {k: v * e for k, v in _summary(g).items()} for e in EPSILONS
            },
        }
    out["seconds"] = round(time.perf_counter() - t0, 1)
    return out


def _has_view(paths: DatasetPaths, option: str, view: str) -> bool:
    try:
        FeatureStore(paths, option, view)
    except FileNotFoundError:
        return False
    return True


def render_influence(r: dict[str, Any]) -> str:
    rows = []
    for name, v in r["views"].items():
        g = v["group_size"]
        rows.append(
            {
                "view": name,
                "changed": v["changed_accounts"],
                "g50": g["q50"],
                "g90": g["q90"],
                "g99": g["q99"],
                "gmax": g["q100"],
                "any": v["other_accounts_any_member"]["q50"],
                "rows": v["rows_changed_per_account"]["q50"],
                "eps1": v["group_epsilon"]["1"]["q50"],
                "eps1_max": v["group_epsilon"]["1"]["q100"],
            }
        )
    return "\n".join(
        [
            f"# Indirect influence of an account · {r['dataset']}",
            "",
            f"{r['sample']} training accounts (half with a laundering row, each half by a fixed "
            "hash) are removed and every feature is rebuilt; another account counts as "
            "influenced when any of its training rows changes and it lies within two hops of the "
            "removed account. **Group size** = 1 + influenced accounts at the same member: the "
            "number of account-unit bags one account moves, so the account-unit guarantee "
            "including indirect influence is the group guarantee (g ε, g e^((g−1)ε) δ). The "
            f"capped view keeps at most {r['cap']} distinct counterparties per account. "
            f"Total {r['seconds']:,.0f} s.",
            "",
            table(
                rows,
                [
                    ("view", "Features"),
                    ("changed", "Accounts changed (all removals)"),
                    ("g50", "Group size, median"),
                    ("g90", "p90"),
                    ("g99", "p99"),
                    ("gmax", "max"),
                    ("any", "Influenced at any member, median"),
                    ("rows", "Rows changed per account, median"),
                    ("eps1", "Group ε at ε = 1, median"),
                    ("eps1_max", "Group ε at ε = 1, max"),
                ],
            ),
            "",
            "Formal group bounds grow with g (δ by e^((g−1)ε)), so for g above a few they say "
            "little; the measured sizes are what the cap changes.",
            "",
        ]
    )


__all__ = ["render_influence", "run_influence", "sample_accounts"]
