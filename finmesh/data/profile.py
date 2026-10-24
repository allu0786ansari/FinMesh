"""Week-1 data profile: the numbers needed before any design is frozen.

Reports per dataset: size, time span, label balance, data quality, per-bank
volumes and laundering share, currencies and payment formats, pattern and
scheme statistics (including how many schemes cross banks), and, when the
accounts file is usable, how many entities hold accounts at several banks.

Federation-specific counts (multi-bank schemes among the chosen banks, legs
leaving the federation) belong to week 2 and Gate G0, not here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from finmesh.data.lowmem import distinct_keys_per_group, hashed_key
from finmesh.data.manifest import load_manifest
from finmesh.eval.provenance import Stamp, write_artifact
from finmesh.paths import DatasetPaths, artifacts_dir
from finmesh.reporting import fmt as _fmt
from finmesh.reporting import table as _table
from finmesh.sysinfo import peak_rss_mb

TOP_BANKS_IN_REPORT = 25


def per_bank(transactions: Path) -> pl.DataFrame:
    """Transactions and laundering touching each bank, as sender, receiver or both."""
    lf = pl.scan_parquet(transactions).select(
        "from_bank", "to_bank", "is_laundering", "src_key", "dst_key"
    )
    sent = lf.group_by(pl.col("from_bank").alias("bank")).agg(
        pl.len().alias("sent"), pl.col("is_laundering").sum().alias("sent_laundering")
    )
    received = lf.group_by(pl.col("to_bank").alias("bank")).agg(
        pl.len().alias("received"), pl.col("is_laundering").sum().alias("received_laundering")
    )
    internal = (
        lf.filter(pl.col("from_bank") == pl.col("to_bank"))
        .group_by(pl.col("from_bank").alias("bank"))
        .agg(pl.len().alias("internal"), pl.col("is_laundering").sum().alias("internal_laundering"))
    )
    rows = lf.select(pl.len()).collect(engine="streaming").item()
    owned = pl.concat(
        [
            lf.select(pl.col("from_bank").alias("bank"), hashed_key("src_key").alias("key")),
            lf.select(pl.col("to_bank").alias("bank"), hashed_key("dst_key").alias("key")),
        ]
    )
    accounts = distinct_keys_per_group(owned, "bank", rows=2 * rows, out="accounts").lazy()
    table = (
        accounts.join(sent, on="bank", how="left")
        .join(received, on="bank", how="left")
        .join(internal, on="bank", how="left")
        .fill_null(0)
        .with_columns(
            (pl.col("sent") + pl.col("received") - pl.col("internal")).alias("touching"),
            (
                pl.col("sent_laundering")
                + pl.col("received_laundering")
                - pl.col("internal_laundering")
            ).alias("touching_laundering"),
            (pl.col("sent") - pl.col("internal") + pl.col("received") - pl.col("internal")).alias(
                "cross_bank"
            ),
        )
        .with_columns(
            (pl.col("touching_laundering") / pl.col("touching")).alias("laundering_share"),
            (pl.col("cross_bank") / pl.col("touching")).alias("cross_bank_share"),
        )
        .sort("touching", descending=True)
        .collect(engine="streaming")
    )
    return table


def _as_float(value: Any) -> float:
    return float(value) if isinstance(value, int | float) else 0.0


def scheme_stats(paths: DatasetPaths, laundering_rows: int) -> dict[str, Any] | None:
    if not paths.schemes.exists():
        return None
    schemes = pl.read_parquet(paths.schemes)
    links = pl.read_parquet(paths.scheme_links)
    by_pattern = (
        schemes.group_by("pattern")
        .agg(
            pl.len().alias("schemes"),
            pl.col("n_rows").sum().alias("rows"),
            pl.col("n_rows").median().alias("median_rows"),
            pl.col("n_accounts").median().alias("median_accounts"),
            (pl.col("n_banks") >= 2).sum().alias("multi_bank_schemes"),
        )
        .sort("schemes", descending=True)
    )
    banks_hist = (
        schemes.with_columns(
            pl.when(pl.col("n_banks") >= 4)
            .then(pl.lit("4+"))
            .otherwise(pl.col("n_banks").cast(pl.String))
            .alias("banks_touched")
        )
        .group_by("banks_touched")
        .agg(pl.len().alias("schemes"))
        .sort("banks_touched")
    )
    duration_h = schemes.select(
        ((pl.col("end") - pl.col("start")).dt.total_minutes() / 60).alias("h")
    )["h"]
    labelled = links["tx_id"].n_unique()
    return {
        "schemes": schemes.height,
        "multi_bank_schemes": int((schemes["n_banks"] >= 2).sum()),
        "by_pattern": by_pattern.to_dicts(),
        "banks_touched_histogram": banks_hist.to_dicts(),
        "scheme_duration_hours": {
            "median": _as_float(duration_h.median()),
            "p90": _as_float(duration_h.quantile(0.9)),
            "max": _as_float(duration_h.max()),
        },
        "pattern_labelled_laundering_rows": labelled,
        "pattern_labelled_share": labelled / laundering_rows if laundering_rows else None,
    }


def entity_stats(paths: DatasetPaths) -> dict[str, Any] | None:
    if not paths.accounts.exists():
        return None
    accounts = pl.read_parquet(paths.accounts)
    per_entity = accounts.group_by("entity_id").agg(
        pl.col("bank").n_unique().alias("banks"), pl.len().alias("accounts")
    )
    multi = per_entity.filter(pl.col("banks") >= 2).height
    return {
        "entities": per_entity.height,
        "accounts": accounts.height,
        "entities_with_accounts_at_2plus_banks": multi,
        "share_entities_multi_bank": multi / per_entity.height if per_entity.height else None,
    }


def build_profile(paths: DatasetPaths) -> dict[str, Any]:
    ingest = json.loads(paths.ingest_report.read_text())["result"]
    tx = ingest["transactions"]
    lf = pl.scan_parquet(paths.transactions)
    currencies = (
        lf.group_by("payment_currency")
        .agg(pl.len().alias("rows"))
        .sort("rows", descending=True)
        .collect(engine="streaming")
    )
    formats = (
        lf.group_by("payment_format")
        .agg(pl.len().alias("rows"), pl.col("is_laundering").mean().alias("laundering_rate"))
        .sort("rows", descending=True)
        .collect(engine="streaming")
    )
    daily = (
        lf.group_by(pl.col("timestamp").dt.date().alias("day"))
        .agg(pl.len().alias("rows"), pl.col("is_laundering").sum().alias("laundering"))
        .sort("day")
        .collect(engine="streaming")
    )
    banks = per_bank(paths.transactions)
    span_days = None
    if tx["first_timestamp"] and tx["last_timestamp"]:
        span = pl.Series([tx["last_timestamp"], tx["first_timestamp"]]).str.to_datetime()
        span_days = round((span[0] - span[1]).total_seconds() / 86400, 2)
    rows = tx["rows"]
    return {
        "dataset": paths.name,
        "summary": {
            "rows": rows,
            "accounts": tx["accounts"],
            "banks": tx["banks"],
            "first_timestamp": tx["first_timestamp"],
            "last_timestamp": tx["last_timestamp"],
            "span_days": span_days,
            "laundering_rows": tx["laundering_rows"],
            "laundering_rate": tx["laundering_rows"] / rows if rows else None,
            "one_in": round(rows / tx["laundering_rows"]) if tx["laundering_rows"] else None,
        },
        "quality": {
            k: tx[k]
            for k in (
                "malformed_cells",
                "duplicate_extra_rows",
                "duplicate_groups",
                "self_transfers",
                "negative_amount_paid",
                "invalid_label_values",
            )
        },
        "linking": ingest.get("linking"),
        "pattern_parse": ingest.get("patterns"),
        "schemes": scheme_stats(paths, tx["laundering_rows"]),
        "entities": entity_stats(paths),
        "banks_total": banks.height,
        "banks_top": banks.head(TOP_BANKS_IN_REPORT).to_dicts(),
        "currencies": currencies.to_dicts(),
        "payment_formats": formats.to_dicts(),
        "daily": [{**d, "day": str(d["day"])} for d in daily.to_dicts()],
        "ingest_timings": ingest.get("timings"),
        "ingest_peak_rss_mb": ingest.get("peak_rss_mb"),
        "profile_peak_rss_mb": peak_rss_mb(),
    }


def render_markdown(profile: dict[str, Any]) -> str:
    s = profile["summary"]
    q = profile["quality"]
    lines = [
        f"## {profile['dataset']}",
        "",
        f"{_fmt(s['rows'])} transactions between {_fmt(s['accounts'])} accounts at "
        f"{_fmt(s['banks'])} banks, from {s['first_timestamp']} to {s['last_timestamp']} "
        f"({_fmt(s['span_days'])} days). {_fmt(s['laundering_rows'])} rows are laundering, "
        f"about 1 in {_fmt(s['one_in'])}.",
        "",
        "### Data quality",
        "",
        _table([q], [(k, k.replace("_", " ")) for k in q]),
        "",
    ]
    sch = profile["schemes"]
    if sch:
        lines += [
            "### Schemes from the pattern file",
            "",
            f"{_fmt(sch['schemes'])} schemes; {_fmt(sch['multi_bank_schemes'])} touch two or more "
            f"banks. {_fmt(sch['pattern_labelled_laundering_rows'])} laundering rows carry a "
            f"pattern label (share {_fmt(sch['pattern_labelled_share'])}). Median scheme duration "
            f"{_fmt(sch['scheme_duration_hours']['median'])} h, 90th percentile "
            f"{_fmt(sch['scheme_duration_hours']['p90'])} h.",
            "",
            _table(
                sch["by_pattern"],
                [
                    ("pattern", "Pattern"),
                    ("schemes", "Schemes"),
                    ("rows", "Rows"),
                    ("median_rows", "Median rows"),
                    ("median_accounts", "Median accounts"),
                    ("multi_bank_schemes", "Multi-bank"),
                ],
            ),
            "",
            _table(
                sch["banks_touched_histogram"],
                [("banks_touched", "Banks touched"), ("schemes", "Schemes")],
            ),
            "",
        ]
    link = profile["linking"]
    if link:
        lines += [
            "### Linking pattern lines to transactions",
            "",
            _table([link], [(k, k.replace("_", " ")) for k in link]),
            "",
        ]
    ent = profile["entities"]
    lines += ["### Entities across banks", ""]
    if ent:
        lines += [
            f"{_fmt(ent['entities'])} entities own {_fmt(ent['accounts'])} accounts; "
            f"{_fmt(ent['entities_with_accounts_at_2plus_banks'])} hold accounts at two or more "
            f"banks (share {_fmt(ent['share_entities_multi_bank'])}). This is why an account-level "
            "privacy unit is not a customer-level unit.",
            "",
        ]
    else:
        lines += ["Accounts file missing or unrecognised; entity statistics unavailable.", ""]
    lines += [
        f"### Banks (top {min(TOP_BANKS_IN_REPORT, profile['banks_total'])} of "
        f"{_fmt(profile['banks_total'])} by transactions touched)",
        "",
        _table(
            profile["banks_top"],
            [
                ("bank", "Bank"),
                ("accounts", "Accounts"),
                ("touching", "Tx touching"),
                ("cross_bank_share", "Cross-bank share"),
                ("touching_laundering", "Laundering tx"),
                ("laundering_share", "Laundering share"),
            ],
        ),
        "",
        "### Payment formats",
        "",
        _table(
            profile["payment_formats"],
            [
                ("payment_format", "Format"),
                ("rows", "Rows"),
                ("laundering_rate", "Laundering rate"),
            ],
        ),
        "",
        "### Currencies (payment side)",
        "",
        _table(profile["currencies"], [("payment_currency", "Currency"), ("rows", "Rows")]),
        "",
        "### Rows per day",
        "",
        _table(profile["daily"], [("day", "Day"), ("rows", "Rows"), ("laundering", "Laundering")]),
        "",
        f"Resources: ingest {profile['ingest_timings']}, peak memory ingest "
        f"{_fmt(profile['ingest_peak_rss_mb'])} MB, "
        f"profile {_fmt(profile['profile_peak_rss_mb'])} MB.",
        "",
    ]
    return "\n".join(lines)


def write_profile(paths: DatasetPaths, report_path: Path | None = None) -> tuple[Path, Path | None]:
    """Write the stamped JSON artifact and, optionally, the markdown report."""
    manifest = load_manifest(paths.manifest)
    profile = build_profile(paths)
    stamp = Stamp(
        kind="data_profile",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
    )
    artifact = write_artifact(
        artifacts_dir(paths.root) / "week01" / f"data_profile_{paths.name}.json", stamp, profile
    )
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"<!-- generated by `finmesh profile --dataset {paths.name}`; "
            f"manifest {manifest.manifest_hash[:12]}; fixture={manifest.fixture} -->\n\n"
        )
        report_path.write_text(header + render_markdown(profile))
    return artifact, report_path
