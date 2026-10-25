"""Diagnostics behind the week-5 protocol decisions (train and validation only).

1. **Positive profile.** An account-window is positive when it touches any
   unmasked laundering leg. A busy account that received one laundering
   payment among hundreds of legitimate ones is then positive too; ranking
   by activity finds such accounts first. This counts them, so the label
   definition can be fixed knowingly in the preregistration.
2. **Pattern visibility.** For each AMLworld pattern, how often its signature
   feature fires on at least one of the scheme's account-windows, against
   how often the scheme lies wholly inside one member's view and inside the
   24 h lookback. Misses explained by visibility are the gap evidence
   sharing should close; misses explained by the lookback are a feature
   design question for schema v2.

Test schemes are never touched: their membership is label information.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from finmesh.data.lowmem import hashed_key
from finmesh.data.splits import partition_expr, window_index_expr
from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.eval.universe import INCIDENTAL_MAX_SHARE, INCIDENTAL_MIN_LEGS
from finmesh.features.build import FeatureStore
from finmesh.features.schema import SCHEMA_VERSION
from finmesh.paths import DatasetPaths
from finmesh.reporting import table

OPEN_PARTITIONS: tuple[str, ...] = ("train", "val")

SIGNATURES: dict[str, tuple[str, pl.Expr]] = {
    "CYCLE": (
        "cyc2, cyc3 or cyc4 > 0",
        (pl.col("cyc2") > 0) | (pl.col("cyc3") > 0) | (pl.col("cyc4") > 0),
    ),
    "SCATTER-GATHER": (
        "sg_out_max or sg_in_max >= 2",
        (pl.col("sg_out_max") >= 2) | (pl.col("sg_in_max") >= 2),
    ),
    "GATHER-SCATTER": ("gs_min_fan >= 2", pl.col("gs_min_fan") >= 2),
    "FAN-OUT": ("fan_out >= 3", pl.col("fan_out") >= 3),
    "FAN-IN": ("fan_in >= 3", pl.col("fan_in") >= 3),
    "BIPARTITE": (
        "sg_out_max or sg_in_max >= 2",
        (pl.col("sg_out_max") >= 2) | (pl.col("sg_in_max") >= 2),
    ),
    "STACK": (
        "sg_out_max or sg_in_max >= 2",
        (pl.col("sg_out_max") >= 2) | (pl.col("sg_in_max") >= 2),
    ),
}
SIGNATURE_COLUMNS = (
    "cyc2",
    "cyc3",
    "cyc4",
    "sg_out_max",
    "sg_in_max",
    "gs_min_fan",
    "fan_out",
    "fan_in",
)


def _bad_legs(paths: DatasetPaths) -> pl.DataFrame:
    plan = load_plan(paths)
    bad = pl.scan_parquet(paths.transactions).filter(pl.col("is_laundering") == 1)
    sides = pl.concat(
        [
            bad.select(hashed_key("src_key").alias("account"), window_index_expr(plan).alias("w")),
            bad.select(hashed_key("dst_key").alias("account"), window_index_expr(plan).alias("w")),
        ]
    )
    return (
        sides.drop_nulls("w")
        .group_by("account", "w")
        .agg(pl.len().alias("bad_legs"))
        .rename({"w": "window"})
        .with_columns(pl.col("window").cast(pl.Int32))
        .collect(engine="streaming")
    )


def positive_profile(paths: DatasetPaths, store: EvalStore) -> dict[str, Any]:
    bad = _bad_legs(paths)
    out: dict[str, Any] = {
        "incidental_rule": {
            "min_legs": INCIDENTAL_MIN_LEGS,
            "max_laundering_share": INCIDENTAL_MAX_SHARE,
        }
    }
    for part in OPEN_PARTITIONS:
        lab = store.partition(part, variant="touch").labels.frame.filter(~pl.col("masked"))
        lab = lab.select("account", "window", "tx", "label")
        pos = (
            lab.filter(pl.col("label") == 1)
            .join(bad, on=["account", "window"], how="left")
            .with_columns(
                (pl.col("bad_legs").fill_null(0) / pl.col("tx")).alias("share"),
            )
        )
        incidental = (pl.col("tx") >= INCIDENTAL_MIN_LEGS) & (
            pl.col("share") < INCIDENTAL_MAX_SHARE
        )

        def q(frame: pl.DataFrame) -> dict[str, float]:
            t = frame["tx"].cast(pl.Float64)
            return {
                "p50": float(t.quantile(0.5) or 0),
                "p90": float(t.quantile(0.9) or 0),
                "p99": float(t.quantile(0.99) or 0),
                "max": float(t.max() or 0),  # type: ignore[arg-type]
            }

        top = {}
        ranked = lab.sort("tx", descending=True)
        for k in (100, 1000):
            head = ranked.head(k).join(
                pos.select("account", "window", "share"), on=["account", "window"], how="left"
            )
            hits = head.filter(pl.col("label") == 1)
            top[str(k)] = {
                "positives": hits.height,
                "incidental": hits.filter(incidental).height,
            }
        out[part] = {
            "account_windows": lab.height,
            "positives": pos.height,
            "legs_positive": q(pos),
            "legs_negative": q(lab.filter(pl.col("label") == 0)),
            "incidental": pos.filter(incidental).height,
            "incidental_share": pos.filter(incidental).height / pos.height if pos.height else None,
            "positives_with_share_at_least": {
                str(t): pos.filter(pl.col("share") >= t).height for t in (0.5, 0.25, 0.1)
            },
            "top_by_activity": top,
        }
    return out


def pattern_visibility(
    paths: DatasetPaths, features: FeatureStore, membership: pl.DataFrame
) -> dict[str, Any]:
    plan = load_plan(paths)
    lookback_h = float(features.schema.params["lookback_hours"])
    assignment = pl.read_parquet(
        paths.parquet / f"scheme_assignment_w{plan.window_hours}.parquet"
    ).select("scheme_id", pl.col("partition").cast(pl.String).alias("scheme_partition"))
    schemes = pl.read_parquet(paths.schemes).select("scheme_id", "pattern")
    links = (
        pl.read_parquet(paths.scheme_links)
        .select("tx_id", "scheme_id")
        .join(assignment, on="scheme_id")
        .filter(pl.col("scheme_partition").is_in(OPEN_PARTITIONS))
        .join(schemes, on="scheme_id")
    )
    m = membership.lazy()
    tx = (
        pl.scan_parquet(paths.transactions)
        .join(links.lazy(), on="tx_id", how="inner")
        .with_columns(
            partition_expr(plan).cast(pl.String).alias("row_partition"),
            window_index_expr(plan).alias("window"),
        )
        .filter(pl.col("row_partition") == pl.col("scheme_partition"))
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
        .select(
            "scheme_id",
            "pattern",
            "scheme_partition",
            "timestamp",
            "window",
            hashed_key("src_key").alias("src"),
            hashed_key("dst_key").alias("dst"),
            "src_member",
            "dst_member",
        )
        .collect(engine="streaming")
    )
    if tx.height == 0:
        return {"lookback_hours": lookback_h, "patterns": []}

    per_scheme = tx.group_by("scheme_id", "pattern").agg(
        pl.len().alias("legs"),
        pl.concat_list("src", "dst").explode(empty_as_null=False).n_unique().alias("accounts"),
        ((pl.col("timestamp").max() - pl.col("timestamp").min()).dt.total_minutes() / 60).alias(
            "duration_h"
        ),
    )
    touch = (
        pl.concat(
            [
                tx.select(
                    "scheme_id",
                    pl.int_range(pl.len()).alias("leg"),
                    pl.col("src_member").alias("m"),
                ),
                tx.select(
                    "scheme_id",
                    pl.int_range(pl.len()).alias("leg"),
                    pl.col("dst_member").alias("m"),
                ),
            ]
        )
        .drop_nulls("m")
        .unique()
        .group_by("scheme_id", "m")
        .agg(pl.len().alias("legs_seen"))
        .group_by("scheme_id")
        .agg(pl.col("legs_seen").max().alias("best_member_legs"))
    )
    per_scheme = per_scheme.join(touch, on="scheme_id", how="left").with_columns(
        (pl.col("best_member_legs").fill_null(0) == pl.col("legs")).alias("one_member_sees_all"),
        (pl.col("duration_h") <= lookback_h).alias("within_lookback"),
    )

    windows = pl.concat(
        [
            tx.select("scheme_id", "scheme_partition", pl.col("src").alias("account"), "window"),
            tx.select("scheme_id", "scheme_partition", pl.col("dst").alias("account"), "window"),
        ]
    ).unique()
    feats = []
    for part in OPEN_PARTITIONS:
        keys = windows.filter(pl.col("scheme_partition") == part).select("account", "window")
        feats.append(
            pl.scan_parquet(features.layout.partition_dir(part) / "feat_*.parquet")
            .select("account", "window", *SIGNATURE_COLUMNS)
            .join(keys.unique().lazy(), on=["account", "window"], how="semi")
            .collect(engine="streaming")
        )
    scheme_feats = windows.join(pl.concat(feats), on=["account", "window"], how="inner")

    background = (
        pl.scan_parquet(features.layout.partition_dir("val") / "feat_*.parquet")
        .select(
            *[expr.mean().alias(p) for p, (_, expr) in SIGNATURES.items()],
        )
        .collect(engine="streaming")
        .row(0, named=True)
    )

    rows = []
    for pattern in sorted(per_scheme["pattern"].unique().to_list()):
        sch = per_scheme.filter(pl.col("pattern") == pattern)
        row: dict[str, Any] = {
            "pattern": pattern,
            "schemes": sch.height,
            "accounts_median": sch["accounts"].median(),
            "legs_median": sch["legs"].median(),
            "duration_h_median": sch["duration_h"].median(),
            "within_lookback": sch["within_lookback"].mean(),
            "one_member_sees_all": sch["one_member_sees_all"].mean(),
        }
        if pattern in SIGNATURES:
            text, expr = SIGNATURES[pattern]
            fired = (
                scheme_feats.filter(pl.col("scheme_id").is_in(sch["scheme_id"].implode()))
                .group_by("scheme_id")
                .agg(expr.any().alias("fired"))
            )
            sch = sch.join(fired, on="scheme_id", how="left").with_columns(
                pl.col("fired").fill_null(False)
            )
            easy = pl.col("one_member_sees_all") & pl.col("within_lookback")
            row.update(
                {
                    "signature": text,
                    "fired": sch["fired"].mean(),
                    "fired_if_visible_and_short": sch.filter(easy)["fired"].mean(),
                    "fired_otherwise": sch.filter(~easy)["fired"].mean(),
                    "background": background[pattern],
                }
            )
        rows.append(row)
    return {"lookback_hours": lookback_h, "patterns": rows}


def render_diagnostics(
    dataset: str,
    option: str,
    profile: dict[str, Any],
    visibility: dict[str, Any],
    drift: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Diagnostics · {dataset}",
        "",
        f"Federation {option}, feature schema v{SCHEMA_VERSION}; train and validation only "
        "(test schemes are never read). Generated by `finmesh diagnose`.",
        "",
        "## 1. Who the positives are",
        "",
        "Positive = account-window touching an unmasked laundering leg. **Incidental** = "
        f"positive with at least {INCIDENTAL_MIN_LEGS} legs of which under "
        f"{INCIDENTAL_MAX_SHARE:.0%} are laundering: a busy account that a scheme passed "
        "through once.",
        "",
    ]
    prof_rows = []
    for part in OPEN_PARTITIONS:
        p = profile[part]
        at = p["positives_with_share_at_least"]
        prof_rows.append(
            {
                "partition": part,
                "positives": p["positives"],
                "incidental": p["incidental"],
                "incidental_share": p["incidental_share"],
                "share50": at["0.5"],
                "legs_pos": f"{p['legs_positive']['p50']:.0f} / {p['legs_positive']['p99']:.0f} "
                f"/ {p['legs_positive']['max']:,.0f}",
                "legs_neg": f"{p['legs_negative']['p50']:.0f} / {p['legs_negative']['p99']:.0f} "
                f"/ {p['legs_negative']['max']:,.0f}",
                "top100": f"{p['top_by_activity']['100']['positives']} "
                f"({p['top_by_activity']['100']['incidental']} incidental)",
                "top1000": f"{p['top_by_activity']['1000']['positives']} "
                f"({p['top_by_activity']['1000']['incidental']} incidental)",
            }
        )
    lines.append(
        table(
            prof_rows,
            [
                ("partition", "Partition"),
                ("positives", "Positives"),
                ("incidental", "Incidental"),
                ("incidental_share", "Share"),
                ("share50", "Laundering share >= 50%"),
                ("legs_pos", "Legs, positives (median / p99 / max)"),
                ("legs_neg", "Legs, negatives (median / p99 / max)"),
                ("top100", "Positives in top 100 by legs"),
                ("top1000", "Positives in top 1,000 by legs"),
            ],
        )
    )
    lines += [
        "",
        "## 2. Can a member see each pattern?",
        "",
        "Per scheme (train and validation): does one member see every leg, does the scheme fit "
        f"in the {visibility['lookback_hours']:.0f} h lookback, and does the pattern's "
        "signature fire on at least one of its account-windows? Background = share of all "
        "validation account-windows where the same signature fires.",
        "",
        table(
            visibility["patterns"],
            [
                ("pattern", "Pattern"),
                ("schemes", "Schemes"),
                ("accounts_median", "Accounts (median)"),
                ("duration_h_median", "Duration h (median)"),
                ("within_lookback", "Within lookback"),
                ("one_member_sees_all", "One member sees all"),
                ("signature", "Signature"),
                ("fired", "Fires"),
                ("fired_if_visible_and_short", "Fires if visible and short"),
                ("fired_otherwise", "Fires otherwise"),
                ("background", "Background"),
            ],
        ),
        "",
        "## 3. Feature drift, train to validation",
        "",
        'PSI on training deciles (above 0.25 is large); "absent later" = non-zero in at least '
        "0.1% of training rows and never in validation.",
        "",
        table(
            [r for r in drift if r["flag"] or r["psi"] > 0.1],
            [
                ("feature", "Feature"),
                ("nonzero_train", "Non-zero (train)"),
                ("nonzero_val", "Non-zero (val)"),
                ("psi", "PSI"),
                ("flag", "Flag"),
            ],
        ),
        "",
        f"Features with PSI at most 0.1 and no flag: "
        f"{sum(1 for r in drift if not r['flag'] and r['psi'] <= 0.1)} of {len(drift)}.",
    ]
    return "\n".join(lines) + "\n"
