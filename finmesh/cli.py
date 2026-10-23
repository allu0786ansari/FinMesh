"""Command-line entry point: ``finmesh <command>`` (or ``uv run finmesh <command>``).

Week-1 commands:

    finmesh check                          environment and data-file status
    finmesh fixture                        write the synthetic test dataset
    finmesh download --dataset HI-Small    fetch AMLworld files from Kaggle
    finmesh ingest   --dataset HI-Small    raw files -> typed, linked Parquet
    finmesh profile  --dataset HI-Small    data profile (JSON artifact + markdown)
    finmesh week1    --dataset HI-Small    ingest + profile in one go
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
from pathlib import Path

from finmesh import __version__
from finmesh.data.schema import FIXTURE_DATASET, PRIMARY_DATASETS
from finmesh.paths import REPO_ROOT, data_root, dataset_paths


def _report_path(dataset: str, explicit: str | None) -> Path | None:
    if explicit == "none":
        return None
    if explicit:
        return Path(explicit)
    if dataset == FIXTURE_DATASET:
        # Fixture profiles never go into docs/, so they cannot be mistaken for findings.
        return data_root() / "artifacts" / "week01" / f"data_profile_{dataset}.md"
    return REPO_ROOT / "docs" / "data_profile" / f"{dataset}.md"


def cmd_check(_: argparse.Namespace) -> int:
    print(f"finmesh {__version__} | Python {platform.python_version()} | {platform.platform()}")
    ok = True
    for mod in ("polars", "pyarrow", "yaml"):
        try:
            m = importlib.import_module(mod)
            print(f"  {mod:<8} {getattr(m, '__version__', 'ok')}")
        except ImportError:
            ok = False
            print(f"  {mod:<8} MISSING")
    root = data_root()
    print(f"data root: {root}")
    from finmesh.data.pipeline import raw_files_present

    for name in (*PRIMARY_DATASETS, FIXTURE_DATASET):
        paths = dataset_paths(name)
        present = raw_files_present(paths)
        ingested = paths.transactions.exists()
        flags = ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in present.items())
        print(f"  {name:<14} raw: {flags}; ingested={'yes' if ingested else 'no'}")
    return 0 if ok else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    from finmesh.data.fixture import write_fixture

    paths = dataset_paths(FIXTURE_DATASET)
    truth = write_fixture(paths.raw, seed=args.seed)
    print(f"fixture written to {paths.raw}")
    print(json.dumps(truth.__dict__, indent=2))
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    from finmesh.data.download import download

    for path in download(dataset_paths(args.dataset)):
        print(f"  ok {path}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    from finmesh.data.pipeline import ingest_dataset

    paths = dataset_paths(args.dataset, raw_dir=Path(args.raw_dir) if args.raw_dir else None)
    print(f"ingesting {args.dataset} from {paths.raw}")
    report = ingest_dataset(paths)
    tx = report["transactions"]
    print(
        f"  rows {tx['rows']:,}  laundering {tx['laundering_rows']:,}  "
        f"banks {tx['banks']:,}  accounts {tx['accounts']:,}"
    )
    print(
        f"  malformed cells {tx['malformed_cells']}  "
        f"duplicate extra rows {tx['duplicate_extra_rows']}"
    )
    if report["linking"]:
        lk = report["linking"]
        print(
            f"  schemes {report['patterns']['schemes']}  pattern rows {lk['pattern_rows']}  "
            f"unmatched {lk['unmatched_pattern_rows']}  ambiguous {lk['ambiguous_pattern_rows']}"
        )
    print(f"  accounts file: {report['accounts']['status']}")
    print(f"  timings {report['timings']}  peak RSS {report['peak_rss_mb']} MB")
    print(f"  manifest {report['manifest_hash'][:16]}  -> {paths.parquet}")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    from finmesh.data.profile import write_profile

    paths = dataset_paths(args.dataset)
    artifact, report = write_profile(paths, _report_path(args.dataset, args.report))
    print(f"profile artifact: {artifact}")
    if report:
        print(f"profile report:   {report}")
    return 0


def cmd_week1(args: argparse.Namespace) -> int:
    rc = cmd_ingest(args)
    return rc or cmd_profile(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finmesh", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="show environment and data status").set_defaults(func=cmd_check)

    fx = sub.add_parser("fixture", help="write the synthetic FIXTURE-Small dataset")
    fx.add_argument("--seed", type=int, default=7)
    fx.set_defaults(func=cmd_fixture)

    def add_dataset(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--dataset", required=True, help="HI-Small, LI-Small, HI-Medium or FIXTURE-Small"
        )

    dl = sub.add_parser("download", help="download AMLworld files from Kaggle")
    add_dataset(dl)
    dl.set_defaults(func=cmd_download)

    for name, func, helptext in (
        ("ingest", cmd_ingest, "convert raw files to Parquet and link schemes"),
        ("week1", cmd_week1, "ingest then profile"),
    ):
        p = sub.add_parser(name, help=helptext)
        add_dataset(p)
        p.add_argument("--raw-dir", help="folder holding the raw files, if not data/raw/<dataset>")
        if name == "week1":
            p.add_argument("--report", help="markdown path, or 'none'")
        p.set_defaults(func=func)

    pr = sub.add_parser("profile", help="write the data profile")
    add_dataset(pr)
    pr.add_argument(
        "--report", help="markdown path, or 'none' (default docs/data_profile/<dataset>.md)"
    )
    pr.set_defaults(func=cmd_profile)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
