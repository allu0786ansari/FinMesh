"""Week-1 ingestion pipeline: raw AMLworld files to typed, linked, hashed Parquet.

Outputs under ``data/parquet/<dataset>/``:

* ``transactions.parquet``  every row, canonical schema, ``tx_id`` = CSV row
* ``schemes.parquet``       one row per pattern-file scheme
* ``scheme_links.parquet``  ``tx_id`` to ``scheme_id``
* ``accounts.parquet``      account to entity (when the accounts file is usable)
* ``manifest.json``         SHA-256 of raw inputs and outputs, fixture flag
* ``ingest_report.json``    provenance-stamped quality and linking report
"""

from __future__ import annotations

from typing import Any

from finmesh.data.accounts import load_accounts
from finmesh.data.ingest import ingest_transactions
from finmesh.data.manifest import Manifest
from finmesh.data.patterns import link_schemes, parse_pattern_file, summarise_schemes
from finmesh.data.schema import FIXTURE_DATASET, dataset_files
from finmesh.eval.provenance import Stamp, write_artifact
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak, peak_rss_mb, timed


class MissingRawDataError(FileNotFoundError):
    pass


def ingest_dataset(paths: DatasetPaths) -> dict[str, Any]:
    """Run the full ingestion for one dataset and return the report payload."""
    with AnonPeak() as anon:
        report = _ingest(paths)
    report["peak_anon_mb"] = anon.mb
    _stamp_and_write(paths, report)
    return report


def _ingest(paths: DatasetPaths) -> dict[str, Any]:
    files = dataset_files(paths.name)
    trans_csv = paths.raw / files.transactions
    pattern_txt = paths.raw / files.patterns
    accounts_csv = paths.raw / files.accounts
    if not trans_csv.exists():
        raise MissingRawDataError(
            f"{trans_csv} not found. Download AMLworld first (docs/runlog/week-01.md, step 3)."
        )
    is_fixture = paths.name == FIXTURE_DATASET
    timings: dict[str, float] = {}
    report: dict[str, Any] = {"dataset": paths.name, "fixture": is_fixture}

    with timed(timings, "transactions_s"):
        report["transactions"] = ingest_transactions(trans_csv, paths.transactions)

    if pattern_txt.exists():
        with timed(timings, "patterns_s"):
            rows, parse_report = parse_pattern_file(pattern_txt)
            summarise_schemes(rows).write_parquet(paths.schemes)
            links, link_report = link_schemes(paths.transactions, rows)
            links.write_parquet(paths.scheme_links)
        report["patterns"] = parse_report.to_dict()
        report["linking"] = link_report
    else:
        report["patterns"] = None
        report["linking"] = None

    accounts = load_accounts(accounts_csv)
    if accounts is not None:
        accounts.write_parquet(paths.accounts)
        report["accounts"] = {"rows": accounts.height, "status": "loaded"}
    else:
        status = "missing" if not accounts_csv.exists() else "unrecognised header"
        report["accounts"] = {"rows": 0, "status": status}

    manifest = Manifest(dataset=paths.name, fixture=is_fixture)
    for role, path in (
        ("raw_transactions", trans_csv),
        ("raw_patterns", pattern_txt),
        ("raw_accounts", accounts_csv),
        ("transactions", paths.transactions),
        ("schemes", paths.schemes),
        ("scheme_links", paths.scheme_links),
        ("accounts", paths.accounts),
    ):
        if path.exists():
            manifest.add(role, path, relative_to=paths.root)
    manifest.write(paths.manifest)

    report["timings"] = timings
    report["peak_rss_mb"] = peak_rss_mb()
    report["manifest_hash"] = manifest.manifest_hash
    return report


def _stamp_and_write(paths: DatasetPaths, report: dict[str, Any]) -> None:
    stamp = Stamp(
        kind="ingest_report",
        dataset=paths.name,
        manifest_hash=report["manifest_hash"],
        fixture=bool(report["fixture"]),
        params={"raw_dir": str(paths.raw)},
    )
    write_artifact(paths.ingest_report, stamp, report)


def raw_files_present(paths: DatasetPaths) -> dict[str, bool]:
    files = dataset_files(paths.name)
    return {
        name: (paths.raw / fname).exists()
        for name, fname in (
            ("transactions", files.transactions),
            ("patterns", files.patterns),
            ("accounts", files.accounts),
        )
    }
