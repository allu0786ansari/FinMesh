"""Command-line entry point: ``finmesh <command>`` (or ``uv run finmesh <command>``).

Week-1 commands:

    finmesh check                          environment and data-file status
    finmesh fixture                        write the synthetic test dataset
    finmesh download --dataset HI-Small    fetch AMLworld files from Kaggle
    finmesh ingest   --dataset HI-Small    raw files -> typed, linked Parquet
    finmesh profile  --dataset HI-Small    data profile (JSON artifact + markdown)
    finmesh week1    --dataset HI-Small    ingest + profile in one go

Week-2 commands:

    finmesh g0 --dataset HI-Small --dataset LI-Small
                                           observation window, window length, splits,
                                           federation options and Gate G0 evidence
    finmesh feature-timing --dataset HI-Small
                                           time a prototype per-bank feature pass
    finmesh llm-probe --model llama3.2:3b  latency and JSON validity of a local model

Week-3 commands:

    finmesh labels --dataset HI-Medium     account-window labels per partition (test sealed)
    finmesh harness-check --dataset HI-Medium
                                           reference scorers through the full harness
    finmesh sealed-log --dataset HI-Medium every opening of the sealed test
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
    print(
        f"  timings {report['timings']}  peak memory {report['peak_anon_mb']} MB "
        f"(peak RSS incl. mapped files {report['peak_rss_mb']} MB)"
    )
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


def _g0_report_path(dataset: str) -> Path:
    if dataset == FIXTURE_DATASET:
        return data_root() / "artifacts" / "week02" / f"G0_evidence_{dataset}.md"
    return REPO_ROOT / "docs" / "gates" / f"G0_evidence_{dataset}.md"


def cmd_g0(args: argparse.Namespace) -> int:
    from finmesh.eval.g0 import render_summary, write_g0

    results = []
    for name in args.dataset:
        paths = dataset_paths(name)
        if not paths.ingest_report.exists():
            print(f"{name}: not ingested; run `finmesh week1 --dataset {name}` first")
            return 1
        print(f"G0 evidence for {name} ...")
        artifact, report, result = write_g0(paths, _g0_report_path(name))
        t = result["test"]
        print(
            f"  window {result['window_hours']} h  schemes {result['schemes_total']}  "
            f"option {t['option']}  multi-member test schemes {t['multi_member_schemes']}  "
            f"band {t['band']}  peak memory {result['peak_anon_mb']} MB"
        )
        print(f"  artifact {artifact}")
        print(f"  report   {report}")
        results.append(result)
    from finmesh.eval.g0 import load_result

    # The summary covers every real dataset with G0 evidence, not just this run's.
    real = []
    for path in sorted((data_root() / "artifacts" / "week02").glob("g0_*.json")):
        name = path.stem.removeprefix("g0_")
        if name != FIXTURE_DATASET:
            real.append(load_result(path))
    if real:
        summary = REPO_ROOT / "docs" / "gates" / "G0_evidence_summary.md"
        summary.write_text(render_summary(real))
        print(f"summary  {summary}")
    return 0


def cmd_feature_timing(args: argparse.Namespace) -> int:
    from finmesh.features.prototype import time_member_day

    out = time_member_day(dataset_paths(args.dataset), option=args.option)
    for key, value in out.items():
        print(f"  {key}: {value}")
    if args.dataset != FIXTURE_DATASET:
        target = REPO_ROOT / "docs" / "gates" / f"feature_timing_{args.dataset}.json"
        target.write_text(json.dumps(out, indent=2) + "\n")
        print(f"written to {target}")
    return 0


def cmd_llm_probe(args: argparse.Namespace) -> int:
    from finmesh.attribution.llm_probe import run_probe

    result = run_probe(model=args.model, n=args.n, url=args.url, constrained=not args.free)
    suffix = "_free" if args.free else ""
    name = f"llm_probe_{args.model.replace(':', '_').replace('/', '_')}{suffix}.json"
    out = (REPO_ROOT / "docs" / "gates" / name) if args.save else (data_root() / "artifacts" / name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(f"written to {out}")
    return 0 if "error" not in result else 1


def cmd_labels(args: argparse.Namespace) -> int:
    from finmesh.eval.universe import build_universe
    from finmesh.sysinfo import AnonPeak

    paths = dataset_paths(args.dataset)
    with AnonPeak() as anon:
        meta = build_universe(paths, option=args.option)
    if args.dataset != FIXTURE_DATASET:
        # Freeze the split: the plan is committed, so later runs can be checked against it.
        frozen = REPO_ROOT / "docs" / "protocol" / f"split_plan_{args.dataset}.json"
        frozen.write_text((paths.parquet / "split_plan.json").read_text())
        counts = REPO_ROOT / "docs" / "protocol" / f"eval_counts_{args.dataset}.json"
        counts.write_text(
            json.dumps(
                {k: meta[k] for k in ("option", "window_hours", "partition_windows", "counts")},
                indent=2,
            )
            + "\n"
        )
        print(f"  frozen split plan -> {frozen}")
    for part, c in meta["counts"].items():
        print(
            f"  {part:<5} account-windows {c['account_windows']:,}  positives {c['positives']:,}  "
            f"masked {c['masked']:,}  schemes {c['schemes']}  "
            f"multi-member {c['multi_member_schemes']}"
        )
    print("  test  sealed (counts in data/sealed/.../meta.json)")
    print(f"  slices {meta['slices']}  peak memory {anon.mb} MB")
    return 0


def cmd_harness_check(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.harness import harness_check
    from finmesh.eval.harness_report import render_harness_check
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.eval.sealed import EvalStore
    from finmesh.sysinfo import AnonPeak

    paths = dataset_paths(args.dataset)
    store = EvalStore(paths, option=args.option)
    with AnonPeak() as anon:
        result = harness_check(store, seed=args.seed, reps=args.reps)
    result["peak_anon_mb"] = anon.mb
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="harness_check",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        seed=args.seed,
        split=f"w{store.window_hours}",
        params={"option": args.option, "reps": args.reps},
    )
    artifact = write_artifact(
        data_root() / "artifacts" / "week03" / f"harness_check_{paths.name}.json", stamp, result
    )
    if args.dataset == FIXTURE_DATASET:
        report = data_root() / "artifacts" / "week03" / f"harness_check_{paths.name}.md"
    else:
        report = REPO_ROOT / "docs" / "eval" / f"harness_check_{paths.name}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_harness_check(result) + f"\nPeak memory {anon.mb} MB.\n")
    for name, rep in result["scorers"].items():
        w = rep["window"]
        auprc = w["auprc"]["estimate"] if w.get("auprc") else None
        print(f"  {name:<9} prevalence {w['prevalence']:.5f}  AUPRC {auprc}")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    print(f"  peak memory {anon.mb} MB")
    return 0


def cmd_sealed_log(args: argparse.Namespace) -> int:
    from finmesh.eval.sealed import read_access_log

    entries = read_access_log(dataset_paths(args.dataset))
    if not entries:
        print("  the sealed test has never been opened")
    for e in entries:
        print(f"  {e['time']}  config {e['config_hash'][:12]}  seed {e['seed']}  {e['purpose']}")
    return 0


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

    g0 = sub.add_parser("g0", help="Gate G0 evidence (week 2)")
    g0.add_argument("--dataset", action="append", required=True, help="repeat for several datasets")
    g0.set_defaults(func=cmd_g0)

    ft = sub.add_parser("feature-timing", help="time a prototype per-bank feature pass (week 2)")
    add_dataset(ft)
    ft.add_argument("--option", default=None, help="membership option; default: the G0 choice")
    ft.set_defaults(func=cmd_feature_timing)

    lp = sub.add_parser("llm-probe", help="latency and JSON validity of a local Ollama model")
    lp.add_argument("--model", default="llama3.2:3b")
    lp.add_argument("--n", type=int, default=20)
    lp.add_argument("--url", default="http://localhost:11434")
    lp.add_argument("--save", action="store_true", help="write the result to docs/gates/")
    lp.add_argument(
        "--free", action="store_true", help="JSON-only decoding (no schema enum); amendment A7"
    )
    lp.set_defaults(func=cmd_llm_probe)

    lb = sub.add_parser("labels", help="account-window labels per partition (week 3)")
    add_dataset(lb)
    lb.add_argument("--option", default="B8")
    lb.set_defaults(func=cmd_labels)

    hc = sub.add_parser("harness-check", help="reference scorers through the harness (week 3)")
    add_dataset(hc)
    hc.add_argument("--option", default="B8")
    hc.add_argument("--seed", type=int, default=0)
    hc.add_argument("--reps", type=int, default=1000)
    hc.set_defaults(func=cmd_harness_check)

    sl = sub.add_parser("sealed-log", help="show every opening of the sealed test")
    add_dataset(sl)
    sl.set_defaults(func=cmd_sealed_log)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
