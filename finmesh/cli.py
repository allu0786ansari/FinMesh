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
from typing import Any

from finmesh import __version__
from finmesh.data.schema import FIXTURE_DATASET, PRIMARY_DATASETS
from finmesh.paths import REPO_ROOT, DatasetPaths, data_root, dataset_paths


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
    from finmesh.eval.g0 import is_current, load_result

    # The summary covers every real dataset with G0 evidence, not just this run's,
    # but never mixes in results made under an older selection rule.
    real = []
    for path in sorted((data_root() / "artifacts" / "week02").glob("g0_*.json")):
        name = path.stem.removeprefix("g0_")
        if name == FIXTURE_DATASET:
            continue
        loaded = load_result(path)
        if is_current(loaded):
            real.append(loaded)
        else:
            print(f"  skipped  {name}: made before amendment A5; run `finmesh g0 --dataset {name}`")
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


def cmd_federation(args: argparse.Namespace) -> int:
    """Write membership_<option>.parquet for a federation option (A20: the real-bank check)."""
    from finmesh.data.consortium import (
        ConsortiumSpec,
        bank_sizes,
        build_membership,
        membership_summary,
    )

    paths = dataset_paths(args.dataset)
    spec = ConsortiumSpec.parse(args.option)
    out = paths.parquet / f"membership_{spec.name}.parquet"
    if out.exists() and not args.force:
        print(f"  {out} exists (use --force to rebuild); the G0 choice is never rebuilt silently")
        return 0
    sizes = bank_sizes(paths.transactions)
    membership = build_membership(sizes, spec)
    membership.write_parquet(out)
    summary = membership_summary(sizes, membership)
    covered = int(summary["accounts"].sum()) if "accounts" in summary.columns else 0
    total = int(sizes["accounts"].sum())
    print(f"  {spec.name}: {membership.height} banks in {membership['member'].n_unique()} members")
    print(f"  accounts held by members: {covered:,} of {total:,} ({covered / max(total, 1):.1%})")
    print(f"  written {out}")
    return 0


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
        counts = (
            REPO_ROOT
            / "docs"
            / "protocol"
            / f"eval_counts_{option_tag(args.dataset, args.option)}.json"
        )
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


def cmd_features(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.features.build import build_features
    from finmesh.features.report import render_build

    paths = dataset_paths(args.dataset)
    if args.degree_cap:
        from finmesh.features.variants import degree_cap

        variant = degree_cap(args.degree_cap)
        meta = build_features(paths, option=args.option, variant=variant)
        args.view = variant[0]
    else:
        meta = build_features(paths, option=args.option, view=args.view)
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="features",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split=f"w{meta['window_hours']}",
        params={
            "option": args.option,
            "view": args.view,
            "schema_version": meta["schema_version"],
        },
    )
    base = option_tag(paths.name, args.option)
    tag = base if args.view == "member" else f"{base}_{args.view}"
    artifact = write_artifact(
        data_root() / "artifacts" / "week04" / f"features_{tag}.json", stamp, meta
    )
    if args.dataset == FIXTURE_DATASET:
        report = data_root() / "artifacts" / "week04" / f"features_{tag}.md"
    else:
        report = REPO_ROOT / "docs" / "eval" / f"features_{tag}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_build(meta))
    for part, n in meta["rows"].items():
        print(f"  {part:<5} account-windows {n:,}")
    for stage, t in meta["timings"].items():
        print(f"  {stage:<13} {t['seconds']:>7.1f} s  peak {t['peak_anon_mb']:,.0f} MB")
    unreachable = meta["currencies"]["unreachable"]
    if unreachable:
        print(f"  no exchange rate for: {', '.join(unreachable)}")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_feature_report(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.feature_report import feature_signal, render_feature_signal
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.eval.sealed import EvalStore
    from finmesh.features.build import FeatureStore
    from finmesh.sysinfo import AnonPeak

    paths = dataset_paths(args.dataset)
    with AnonPeak() as anon:
        result = feature_signal(
            EvalStore(paths, option=args.option), FeatureStore(paths, option=args.option)
        )
    if args.dataset == FIXTURE_DATASET:
        report = data_root() / "artifacts" / "week04" / f"feature_signal_{paths.name}.md"
    else:
        report = REPO_ROOT / "docs" / "eval" / f"feature_signal_{paths.name}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_feature_signal(paths.name, args.option, result))
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="feature_signal",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={"option": args.option},
    )
    write_artifact(
        data_root() / "artifacts" / "week04" / f"feature_signal_{paths.name}.json", stamp, result
    )
    for r in result["features"][:8]:
        print(f"  {r['feature']:<24} AUPRC {r['auprc']:.4f}  AUROC {r['auroc']:.4f}")
    print(f"  prevalence {result['prevalence']:.4f}  flagged: {result['flagged'] or 'none'}")
    print(f"  report   {report}")
    print(f"  peak memory {anon.mb} MB")
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    import polars as pl

    from finmesh.data.manifest import load_manifest
    from finmesh.eval.diagnostics import pattern_visibility, positive_profile, render_diagnostics
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.eval.sealed import EvalStore
    from finmesh.features.build import FeatureStore
    from finmesh.features.drift import feature_drift
    from finmesh.sysinfo import AnonPeak

    paths = dataset_paths(args.dataset)
    membership = pl.read_parquet(paths.parquet / f"membership_{args.option}.parquet")
    with AnonPeak() as anon:
        store = EvalStore(paths, option=args.option)
        features = FeatureStore(paths, option=args.option)
        profile = positive_profile(paths, store)
        visibility = pattern_visibility(paths, features, membership)
        drift = feature_drift(features)
    result = {"profile": profile, "visibility": visibility, "drift": drift, "peak_anon_mb": anon.mb}
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="diagnostics",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="train+val",
        params={"option": args.option},
    )
    write_artifact(
        data_root() / "artifacts" / "week04" / f"diagnostics_{paths.name}.json", stamp, result
    )
    if args.dataset == FIXTURE_DATASET:
        report = data_root() / "artifacts" / "week04" / f"diagnostics_{paths.name}.md"
    else:
        report = REPO_ROOT / "docs" / "eval" / f"diagnostics_{paths.name}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_diagnostics(paths.name, args.option, profile, visibility, drift))
    v = profile["val"]
    print(f"  val positives {v['positives']:,}  incidental {v['incidental']:,}")
    for r in visibility["patterns"]:
        if "fired" in r:
            print(
                f"  {r['pattern']:<15} schemes {r['schemes']:>5}  signature fires {r['fired']:.2f}"
            )
    print(f"  drift flags: {[r['feature'] for r in drift if r['flag']] or 'none'}")
    print(f"  report   {report}")
    print(f"  peak memory {anon.mb} MB")
    return 0


def cmd_baselines(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.baselines import run_with_memory
    from finmesh.training.report import render_baselines

    paths = dataset_paths(args.dataset)
    result = run_with_memory(
        paths, option=args.option, seed=args.seed, reps=args.reps, linked_draws=args.draws
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="baselines",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        seed=args.seed,
        split="val",
        params={"option": args.option, "reps": args.reps, "draws": args.draws},
    )
    artifact = write_artifact(
        data_root() / "artifacts" / "week05" / f"baselines_{paths.name}_seed{args.seed}.json",
        stamp,
        result,
    )
    page = render_baselines(result)
    if args.dataset == FIXTURE_DATASET or args.seed != 0:
        report = data_root() / "artifacts" / "week05" / f"baselines_{paths.name}_seed{args.seed}.md"
    else:
        report = REPO_ROOT / "docs" / "eval" / f"baselines_{paths.name}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(page)
    primary = result["primary_budget"]
    for name, res in result["results"].items():
        b = next(x for x in res["budgets"] if x["budget"] == primary)
        auprc = res["window"]["auprc"]["estimate"] if res["window"].get("auprc") else float("nan")
        print(
            f"  {name:<9} AUPRC {auprc:.4f}  detected {b['detected']['estimate']:.3f}  "
            f"linked {b['linked']['estimate']:.3f}"
        )
    gap = result["comparisons"]["oracle - S0-BG"]["linked"]["difference"]
    print(f"  oracle - S0 linked {gap['estimate']:+.3f} [{gap['low']:+.3f}, {gap['high']:+.3f}]")
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_g1(args: argparse.Namespace) -> int:
    from finmesh.eval.g1 import load_summaries, render_g1

    summaries = load_summaries(data_root() / "artifacts" / "week05")
    out = REPO_ROOT / "docs" / "gates" / "G1_evidence.md"
    out.write_text(render_g1(summaries))
    for s in summaries:
        verdict = "met" if s["criterion_met"] else "not met"
        print(
            f"  {s['dataset']:<10} S0 linked {s['s0_linked']:.3f}  "
            f"oracle {s['oracle_linked']:.3f}  "
            f"gap {s['gap']:+.3f} [{s['gap_low']:+.3f}, {s['gap_high']:+.3f}]  criterion {verdict}"
        )
    if not summaries:
        print("  no real-data baseline artifacts yet; run `finmesh baselines` first")
    print(f"  report   {out}")
    return 0


def cmd_share(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.sharing_report import render_sharing
    from finmesh.training.sharing_run import run_with_memory

    paths = dataset_paths(args.dataset)
    result = run_with_memory(paths, option=args.option, seed=args.seed, reps=args.reps)
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="sharing_run",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        seed=args.seed,
        split="val",
        params={"option": args.option, "reps": args.reps},
    )
    artifact = write_artifact(
        data_root() / "artifacts" / "week06" / f"sharing_{paths.name}_seed{args.seed}.json",
        stamp,
        result,
    )
    if args.dataset == FIXTURE_DATASET or args.seed != 0:
        report = data_root() / "artifacts" / "week06" / f"sharing_{paths.name}_seed{args.seed}.md"
    else:
        report = REPO_ROOT / "docs" / "eval" / f"sharing_{paths.name}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_sharing(result))
    primary = result["primary_budget"]
    for name, res in result["results"].items():
        b = next(x for x in res["budgets"] if x["budget"] == primary)
        p = result["protocol"].get(name, {})
        print(
            f"  {name:<15} linked {b['linked']['estimate']:.3f}  "
            f"requests {p.get('requests', 0):>7,}  links {p.get('links', 0):>6,}"
        )
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def option_tag(name: str, option: str) -> str:
    """Report and artifact name: the dataset for the primary federation (B8), else + option."""
    return name if option == "B8" else f"{name}_{option}"


def cmd_x1(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.x1 import run_x1
    from finmesh.training.x1_report import (
        frontier_figure,
        ladder_figure,
        render_audit,
        render_x1,
        render_x3,
        x3_figure,
    )

    paths = dataset_paths(args.dataset)
    seeds = tuple(int(s) for s in args.seeds.split(","))
    result = run_x1(
        paths,
        option=args.option,
        seeds=seeds,
        reps=args.reps,
        progress=lambda m: print(f"  {m}"),
        sweeps=not args.no_sweeps,
        audit=not args.no_audit,
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="x1",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={
            "option": args.option,
            "seeds": list(seeds),
            "reps": args.reps,
            "sweeps": not args.no_sweeps,
            "audit": not args.no_audit,
        },
    )
    name = option_tag(paths.name, args.option)  # B8 keeps the frozen names (G2 reads them)
    artifact = write_artifact(
        data_root() / "artifacts" / "week09" / f"x1_{name}.json", stamp, result
    )
    if args.dataset == FIXTURE_DATASET:
        out_dir = data_root() / "artifacts" / "week09"
    else:
        out_dir = REPO_ROOT / "docs" / "eval"
    ladder = ladder_figure(result, out_dir / f"ladder_{name}.png")
    (out_dir / f"x1_{name}.md").write_text(render_x1(result, ladder.name))
    pages = [out_dir / f"x1_{name}.md"]
    if result.get("sweeps"):
        fig = x3_figure(result, out_dir / f"x3_{name}.png")
        (out_dir / f"x3_{name}.md").write_text(render_x3(result, fig.name if fig else None))
        pages.append(out_dir / f"x3_{name}.md")
    if result.get("audit"):
        fig = frontier_figure(result, out_dir / f"frontier_{name}.png")
        (out_dir / f"audit_{name}.md").write_text(render_audit(result, fig.name if fig else None))
        pages.append(out_dir / f"audit_{name}.md")
    s = result["summary"]
    for key in (
        "S0",
        "S1/stacker",
        "S2/stacker",
        "S4/stacker",
        "propagation",
        "oracle",
        "oracle-relational",
    ):
        v = s.get(key)
        if v:
            print(f"  {key:<18} linked {v['linked']['estimate']:.3f}")
    for ceiling, per in s.get("H1b", {}).items():
        h = per.get("S2/stacker") or {}
        if h.get("estimate") is None:
            print(f"  S2 recovery against {ceiling}: undefined (no linked gain over S0)")
        else:
            print(
                f"  S2 recovers {h['estimate']:.2f} [{h['low']:.2f}, {h['high']:.2f}]"
                f" of the {ceiling} gain"
            )
    h1c = (result.get("audit") or {}).get("H1c", {})
    if h1c:
        print(f"  H1c: S1 and S3 (eps <= 2) within margin: {h1c.get('S1_and_S3_le2_within')}")
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    for page in pages:
        print(f"  report   {page}")
    return 0


def cmd_g2(args: argparse.Namespace) -> int:
    from finmesh.eval.g2 import DATASETS, load, run_g2, summarise

    out = run_g2(REPO_ROOT / "docs" / "gates" / "G2_evidence.md")
    for ds in DATASETS:
        got = load(ds)
        if got is None:
            print(f"  {ds:<10} no X1 artifact yet; run `finmesh x1 --dataset {ds}` first")
            continue
        s = summarise(ds, *got)
        flags = {k: s[k] for k in s if k.endswith("_met") or k.endswith("_ok")}
        print(f"  {ds:<10} ({s['week']}) " + ", ".join(f"{k}={v}" for k, v in flags.items()))
    print(f"  report   {out}" if out else "  no real-data X1 artifact: G2 page left unchanged")
    return 0


def cmd_demo_slice(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.demo.slice import render_slice, run_slice
    from finmesh.eval.provenance import Stamp, write_artifact

    paths = dataset_paths(args.dataset)
    result = run_slice(paths, option=args.option, n_alerts=args.alerts, seed=args.seed)
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="demo_slice",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={"option": args.option, "alerts": args.alerts, "seed": args.seed},
    )
    artifact = write_artifact(
        data_root() / "artifacts" / "week09" / f"demo_slice_{paths.name}.json", stamp, result
    )
    out_dir = (
        data_root() / "artifacts" / "week09"
        if args.dataset == FIXTURE_DATASET
        else REPO_ROOT / "docs" / "eval"
    )
    report = out_dir / f"demo_slice_{paths.name}.md"
    report.write_text(render_slice(result))
    lat = result["latency"]
    if result["sessions"]:
        print(
            f"  {result['sessions']} sessions; latency p50 {lat['p50']:.3f} s, "
            f"p95 {lat['p95']:.3f} s; PT6 {'met' if result['pt6_met'] else 'not met'}"
        )
    else:
        print("  no alert with a counterparty at another member (expected on the fixture)")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_x4(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.x4 import run_x4
    from finmesh.training.x4_report import render_x4

    paths = dataset_paths(args.dataset)
    seeds = tuple(int(s) for s in args.seeds.split(","))
    out_root = data_root() / "artifacts" / "week10"
    result = run_x4(
        paths,
        out_root,
        option=args.option,
        seeds=seeds,
        reps=args.reps,
        rounds=args.rounds,
        local_steps=args.local_steps,
        progress=lambda m: print(f"  {m}"),
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="x4",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={
            "option": args.option,
            "seeds": list(seeds),
            "reps": args.reps,
            "rounds": args.rounds,
            "local_steps": args.local_steps,
            "run_id": result["run_id"],
        },
    )
    artifact = write_artifact(out_root / f"x4_{paths.name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    report = out_dir / f"x4_{paths.name}.md"
    report.write_text(render_x4(result))
    for name, v in result["summary"].items():
        if name != "H2a":
            print(f"  {name:<26} AUPRC {v['auprc']['estimate']:.4f}")
    for name, v in result["summary"]["H2a"].items():
        share = v["share_of_centralised"]["estimate"]
        print(f"  H2a {name}: {share:.2f} of centralised; met {v['met_on_validation']}")
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_dp_tune(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.dp_tune import PROXY_DATASETS, render_tuning, run_tuning
    from finmesh.training.neural import DpHparams, write_dp_hparams

    if args.dataset not in (*PROXY_DATASETS, FIXTURE_DATASET):
        print(f"  dp-tune runs on the proxy federations only: {', '.join(PROXY_DATASETS)} (A18)")
        return 2
    paths = dataset_paths(args.dataset)
    out_root = data_root() / "artifacts" / ("week11" if args.grid == "A18" else "week12")
    grid = None
    if args.quick:  # CI: two settings, few steps
        grid = [(1.0, 512, 1e-3, 5), (3.0, 512, 3e-3, 5)]
    result = run_tuning(
        paths,
        out_root,
        option=args.option,
        rounds=args.rounds,
        local_steps=args.local_steps,
        grid=grid,
        progress=lambda m: print(f"  {m}"),
        grid_name=args.grid,
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="dp_tune",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="train",
        params={
            "option": args.option,
            "rounds": args.rounds,
            "local_steps": args.local_steps,
            "grid": args.grid,
        },
    )
    artifact = write_artifact(out_root / f"dp_tune_{paths.name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    suffix = "" if args.grid == "A18" else f"_{args.grid}"
    report = out_dir / f"dp_tune_{paths.name}{suffix}.md"
    report.write_text(render_tuning(result))
    best = result["best"]
    if best and args.dataset != FIXTURE_DATASET:
        hp = DpHparams(
            best["clip"],
            best["batch"],
            best["lr"],
            f"dp-tune {paths.name} ({args.grid})",
            best["local_steps"],
        )
        path = write_dp_hparams(
            paths.name,
            hp,
            {
                "run_id": result["run_id"],
                "grid": args.grid,
                "holdout_auprc": best["holdout_auprc"],
                "non_private_holdout_auprc": (result.get("non_private") or {}).get("holdout_auprc"),
            },
        )
        print(
            f"  chosen: clip {best['clip']:g}, batch {best['batch']}, lr {best['lr']:g} -> {path}"
        )
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_influence(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.influence import render_influence, run_influence

    paths = dataset_paths(args.dataset)
    result = run_influence(paths, option=args.option, cap=args.cap, sample=args.sample)
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="influence",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="train",
        params={"option": args.option, "cap": args.cap, "sample": args.sample},
    )
    out_root = data_root() / "artifacts" / "week11"
    artifact = write_artifact(out_root / f"influence_{paths.name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    report = out_dir / f"influence_{paths.name}.md"
    report.write_text(render_influence(result))
    for view, v in result["views"].items():
        g = v["group_size"]
        print(
            f"  {view:<8} group size median {g['q50']:.0f}, p99 {g['q99']:.0f}, max {g['q100']:.0f}"
        )
    print(f"  {result['seconds']:.0f} s")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_membership(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.membership import run_membership
    from finmesh.training.membership_report import render_membership
    from finmesh.training.neural import dp_hparams

    paths = dataset_paths(args.dataset)
    hp = dp_hparams(paths.name)
    if hp.source == "A17 defaults" and args.dataset != FIXTURE_DATASET:
        print("  no tuned DP settings for this regime; run `finmesh dp-tune` first")
        return 2
    out_root = data_root() / "artifacts" / "week12"
    result = run_membership(
        paths,
        out_root,
        option=args.option,
        cap=args.cap,
        reps=args.reps,
        rounds=args.rounds,
        local_steps=args.local_steps,
        progress=lambda m: print(f"  {m}"),
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="membership",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="train",
        params={
            "option": args.option,
            "cap": args.cap,
            "rounds": args.rounds,
            "local_steps": args.local_steps,
            "hparams": hp.to_dict(),
            "run_id": result["run_id"],
        },
    )
    artifact = write_artifact(out_root / f"membership_{paths.name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    report = out_dir / f"membership_{paths.name}.md"
    report.write_text(render_membership(result))
    for name, res in result["results"].items():
        m = res["attacks"]["REF"]["all"]
        t = (m.get("tpr@0.01") or {}).get("estimate")
        print(f"  {name}: REF AUC {m.get('auc', float('nan')):.3f}, TPR at 1% FPR {t}")
    print(f"  audit violation: {result['audit_violation']}")
    print(f"  {result['seconds']['total']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_ensemble(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, read_artifact, write_artifact
    from finmesh.training.ensemble import run_ensemble
    from finmesh.training.ensemble_report import render_ensemble

    paths = dataset_paths(args.dataset)
    out_root = data_root() / "artifacts" / "week12"
    x5_path = out_root / f"x5_{paths.name}.json"
    if not x5_path.exists():
        print(
            f"  no week-12 X5 run for {paths.name}; run `finmesh x5 --dataset {paths.name}` first"
        )
        return 2
    _, x5 = read_artifact(x5_path)
    result = run_ensemble(
        paths, x5, option=args.option, reps=args.reps, progress=lambda m: print(f"  {m}")
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="ensemble",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={"option": args.option, "x5_run": x5["run_id"], "reps": args.reps},
    )
    artifact = write_artifact(out_root / f"ensemble_{paths.name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    report = out_dir / f"ensemble_{paths.name}.md"
    report.write_text(render_ensemble(result))
    s = result["summary"]
    print(f"  local ensemble AUPRC {s['stack[local]']['auprc']['estimate']:.4f}")
    for k, g in s["gain_over_local"].items():
        print(f"  + {k}: {g['estimate']:+.4f} [{g['low']:+.4f}, {g['high']:+.4f}]")
    print(f"  smallest qualifying eps: {s['smallest_qualifying_epsilon']}")
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_g3(args: argparse.Namespace) -> int:
    from finmesh.eval.g3 import run_g3

    out, decision = run_g3(REPO_ROOT / "docs" / "gates" / "G3_evidence.md")
    print(f"  decision: {decision['decision']} ({decision['reason']})")
    print(f"  report   {out}" if out else "  no real-data week-12 artifact: G3 page left unchanged")
    return 0


def cmd_x6(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.x6 import run_x6
    from finmesh.training.x6_report import render_x6

    paths = dataset_paths(args.dataset)
    seeds = tuple(int(s) for s in args.seeds.split(","))
    result = run_x6(
        paths, option=args.option, seeds=seeds, reps=args.reps, progress=lambda m: print(f"  {m}")
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="x6",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={"option": args.option, "seeds": list(seeds), "reps": args.reps},
    )
    out_root = data_root() / "artifacts" / "week13"
    name = option_tag(paths.name, args.option)
    artifact = write_artifact(out_root / f"x6_{name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    report = out_dir / f"x6_{name}.md"
    report.write_text(render_x6(result))
    lv = result["summary"]["levels"]
    for level, v in lv.items():
        a = v["attributor"]["accuracy"]
        print(
            f"  {level:<7} detected {v['detected_share']:.3f}  attributor accuracy "
            f"{a['estimate'] if a else float('nan'):.3f}  majority "
            f"{(v['majority']['accuracy'] or {}).get('estimate', float('nan')):.3f}"
        )
    print(f"  H3a met on validation: {result['summary']['H3a']['met_on_validation']}")
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    """A21: assemble the coverage curve from the X1 artifacts of A64, B8c{p} and B8."""
    from finmesh.eval.coverage import collect, coverage_figure, render_coverage

    paths = dataset_paths(args.dataset)
    rows = collect(paths.name, data_root() / "artifacts" / "week09", paths.parquet)
    out_dir = (
        data_root() / "artifacts" / "week14"
        if args.dataset == FIXTURE_DATASET
        else REPO_ROOT / "docs" / "eval"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    fig = coverage_figure(rows, paths.name, out_dir / f"coverage_{paths.name}.png")
    report = out_dir / f"coverage_{paths.name}.md"
    report.write_text(render_coverage(rows, paths.name, fig.name if fig else None))
    for r in rows:
        s0, s2 = (r["S0"] or {}).get("estimate"), (r["S2"] or {}).get("estimate")
        share = r["account_share"]
        print(
            f"  {r['option']:<7} covered {'—' if share is None else f'{share:.1%}':>6}  "
            f"S0 {fmt_float(s0)}  S2 {fmt_float(s2)}"
        )
    print(f"  report   {report}")
    return 0 if rows else 1


def cmd_narrative(args: argparse.Namespace) -> int:
    """A21/A22, H3b: constrained narratives for sampled S2 cases with a local model."""
    from finmesh.attribution.narrative import run_narrative
    from finmesh.attribution.narrative_report import (
        render_narrative,
        write_cases,
        write_review,
        write_review_ab,
    )
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, read_artifact, write_artifact

    paths = dataset_paths(args.dataset)
    if args.pages_only:  # week 18: rebuild the test pages from the saved result, no opening
        from finmesh.eval.provenance import read_artifact

        saved = data_root() / "artifacts" / "week18"
        saved = saved / f"narrative_test_{option_tag(paths.name, args.option)}_A23.json"
        if not args.test or not saved.exists():
            print(f"  --pages-only needs --test and a saved result ({saved})")
            return 1
        return _narrative_test_outputs(paths, args, read_artifact(saved)[1])
    result = run_narrative(
        paths,
        option=args.option,
        n=args.n,
        model=args.model,
        url=args.url,
        timeout=args.timeout,
        progress=lambda m: print(f"  {m}"),
        protocol=args.protocol,
        split="test" if args.test else "val",
        allow_repeat=args.allow_repeat,
    )
    if "error" in result:
        print(f"  {result['error']}")
        return 1
    if args.test:
        return _narrative_test_outputs(paths, args, result)
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="narrative",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={
            "option": args.option,
            "n": args.n,
            "model": args.model,
            "protocol": args.protocol,
        },
    )
    out_root = data_root() / "artifacts" / "week14"
    base = option_tag(paths.name, args.option)
    name = base if args.protocol == "A21" else f"{base}_{args.protocol}"  # A21 keeps its names
    artifact = write_artifact(out_root / f"narrative_{name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    previous = None
    before = {"A22": f"narrative_{base}.json", "A23": f"narrative_{base}_A22.json"}
    if args.protocol in before and (out_root / before[args.protocol]).exists():
        previous = read_artifact(out_root / before[args.protocol])[1]
    report = out_dir / f"narrative_{name}.md"
    report.write_text(render_narrative(result, previous))
    cases = write_cases(result, out_dir / f"narrative_{name}_cases.jsonl")
    if args.protocol == "A22":
        review = write_review(result, out_dir / f"narrative_{name}_review.csv")
        print(f"  review   {review} (rate these blind; see the run log)")
    if args.protocol == "A23":
        review = write_review_ab(
            result,
            out_dir / f"narrative_{name}_review.csv",
            out_dir / f"narrative_{name}_review_KEY_do_not_open.csv",
        )
        print(f"  review   {review} (rate these blind; see the run log)")
        print(f"  claim-consistent delivered text {result['summary']['final_consistent']}")
        st = result["summary"]["strict_grounding"]
        if st["estimate"] is not None:
            print(f"  strict grounding {st['estimate']:.3f} [{st['low']:.3f}, {st['high']:.3f}]")
        for lv, v in (result.get("topk") or {}).get("levels", {}).items():
            print(f"  {lv} top-3 end to end {v['top3']['estimate']:.3f}")
    s = result["summary"]
    g = s["H3b"]["grounding"]
    tau = result["selective"]["tau"]
    print(f"  tau {'none' if tau is None else f'{tau:.2f}'}; cases {s['cases']}")
    if g["estimate"] is not None:
        print(f"  H3b grounding {g['estimate']:.3f} [{g['low']:.3f}, {g['high']:.3f}]")
    print(f"  met on validation: {s['H3b']['met_on_validation']}")
    print(f"  fallback {s['fallback_rate']}; latency p95 {s['latency_s']['p95']} s")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    print(f"  cases    {cases}")
    return 0


def _narrative_test_outputs(
    paths: DatasetPaths, args: argparse.Namespace, result: dict[str, Any]
) -> int:
    from finmesh.attribution.narrative_report import render_narrative, write_cases, write_review_ab
    from finmesh.eval.provenance import write_artifact

    art, out = _test_out(paths)
    name = f"{option_tag(paths.name, args.option)}_A23"
    params = {"option": args.option, "n": args.n, "model": args.model, "protocol": "A23"}
    artifact = art / f"narrative_test_{name}.json"
    if not getattr(args, "pages_only", False):
        write_artifact(artifact, _stamp(paths, "narrative-test", params), result)
    (out / f"narrative_{name}.md").write_text(as_test_page(render_narrative(result)))
    write_cases(result, out / f"narrative_{name}_cases.jsonl")
    write_review_ab(
        result,
        out / f"narrative_{name}_review.csv",
        out / f"narrative_{name}_review_KEY_do_not_open.csv",
    )
    s = result["summary"]
    g = s["H3b"]["grounding"]
    if g["estimate"] is not None:
        print(f"  H3b grounding {g['estimate']:.3f} [{g['low']:.3f}, {g['high']:.3f}]")
    st = s["strict_grounding"]
    if st["estimate"] is not None:
        print(f"  strict grounding {st['estimate']:.3f} [{st['low']:.3f}, {st['high']:.3f}]")
    for lv, v in (result.get("topk") or {}).get("levels", {}).items():
        print(f"  {lv} top-3 end to end {v['top3']['estimate']:.3f}")
    print(f"  artifact {artifact}")
    return 0


def cmd_narrative_review(args: argparse.Namespace) -> int:
    """A23: score the owner's blind A/B ratings against the hidden key."""
    from finmesh.attribution.narrative_report import (
        prepare_rater_sheets,
        render_review,
        render_two_raters,
        score_review,
        score_two_raters,
    )

    paths = dataset_paths(args.dataset)
    out_dir = (
        data_root() / "artifacts" / "week14"
        if args.dataset == FIXTURE_DATASET
        else REPO_ROOT / "docs" / "eval"
    )
    name = f"narrative_{option_tag(paths.name, args.option)}_A23"
    rated = out_dir / f"{name}_review.csv"
    key = out_dir / f"{name}_review_KEY_do_not_open.csv"
    if not rated.exists() or not key.exists():
        print(f"  {rated.name} or its key is missing; run `finmesh narrative` (A23) first")
        return 1
    raters = [r.strip().lower() for r in args.raters.split(",") if r.strip()]
    if args.prepare:
        for sheet in prepare_rater_sheets(rated, raters):
            print(f"  sheet    {sheet}")
        print("  each rater fills only their own copy; do not open the KEY file")
        return 0
    sheets = {r: rated.with_name(rated.stem + f"_{r}.csv") for r in raters}
    sheets = {r: p for r, p in sheets.items() if p.exists()}
    if sheets:
        two = score_two_raters(sheets, key)
        if not any(v["rated"] for v in two["per_rater"].values()):
            print("  no rated rows yet in the raters' sheets")
            return 1
        report = out_dir / f"{name}_review_result.md"
        report.write_text(render_two_raters(two, paths.name))
        for r, v in two["per_rater"].items():
            m = v["sources"]["model"]
            print(f"  {r:<9} rated {v['rated']}; model faithful yes {m['faithful_yes']}")
        ag = two.get("agreement")
        if ag:
            print(
                f"  agreement: faithful kappa {ag['faithful_kappa']}, useful kappa "
                f"{ag['useful_kappa']}; claim check vs both "
                f"{two['checker_vs_consensus']['kappa']}"
            )
        print(f"  report   {report}")
        return 0
    result = score_review(rated, key)
    if not result["rated"]:
        print(f"  no rated rows in {rated}; fill in the faithful and useful columns first")
        return 1
    report = out_dir / f"{name}_review_result.md"
    report.write_text(render_review(result, paths.name))
    for src, v in result["sources"].items():
        print(f"  {src:<9} faithful yes {v['faithful_yes']}  useful {v['useful_mean']}")
    print(f"  preferred {result['prefer']}; claim check kappa {result['checker']['kappa']}")
    print(f"  report   {report}")
    return 0


def demo_folder(dataset: str) -> Path:
    return data_root() / "demo" / dataset


def cmd_demo_build(args: argparse.Namespace) -> int:
    """Week 16: build the demo world from real validation data (data/demo/<dataset>/)."""
    from finmesh.services.world import build_world

    paths = dataset_paths(args.dataset)
    folder = demo_folder(paths.name)
    meta = build_world(paths, folder, option=args.option, n_alerts=args.alerts, seed=args.seed)
    print(f"  {meta['alerts']} alerts across {len(meta['members'])} members, level {meta['level']}")
    print(f"  setup {meta['setup_seconds']:.0f} s; world in {folder}")
    return 0 if meta["alerts"] else 1


def cmd_demo_run(args: argparse.Namespace) -> int:
    """Week 16: every alert of the demo world through the HTTP services and orchestrators."""
    from finmesh.services.world import load_world, run_world

    folder = demo_folder(dataset_paths(args.dataset).name)
    if not (folder / "meta.json").exists():
        print(f"  no demo world in {folder}; run `finmesh demo-build --dataset {args.dataset}`")
        return 1
    r = run_world(load_world(folder), limit=args.limit)
    lat = r["latency_s"]
    print(f"  sessions {r['sessions']}: {r['states']}")
    if lat["p50"] is not None:
        print(f"  latency per alert p50 {lat['p50']:.3f} s, p95 {lat['p95']:.3f} s (PT6: 3 s)")
    print(f"  sessions in {folder / 'sessions.db'}; open them with `finmesh console`")
    return 0 if r["states"]["closed"] else 1


def cmd_console(args: argparse.Namespace) -> int:
    """Week 16: the analyst console and privacy ledger on 127.0.0.1 only."""
    import uvicorn

    from finmesh.services.console import console_app
    from finmesh.services.store import BudgetLedger, SessionStore
    from finmesh.services.world import load_world

    folder = demo_folder(dataset_paths(args.dataset).name)
    if not (folder / "sessions.db").exists():
        print(f"  no sessions in {folder}; run `finmesh demo-run --dataset {args.dataset}` first")
        return 1
    world = load_world(folder)
    app = console_app(
        SessionStore(folder / "sessions.db"), BudgetLedger(folder / "budget.db"), world.meta
    )
    print(f"  console on http://127.0.0.1:{args.port}  (Ctrl+C to stop)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_x7(args: argparse.Namespace) -> int:
    """Week 17 (X7): the demo path as real processes, under load and faults."""
    from finmesh.services.x7 import build_smoke_world, render_x7, run_x7

    if args.smoke:
        name = "SMOKE"
        world = data_root() / "demo" / name
        build_smoke_world(world)
        out_dir = data_root() / "artifacts" / "week17"
    else:
        if not args.dataset:
            print("  give --dataset (after `finmesh demo-build`) or --smoke")
            return 2
        name = dataset_paths(args.dataset).name
        world = demo_folder(name)
        if not (world / "meta.json").exists():
            print(f"  no demo world in {world}; run `finmesh demo-build --dataset {name}` first")
            return 1
        out_dir = REPO_ROOT / "docs" / "eval"
    result = run_x7(
        world,
        data_root() / "demo" / f"{name}_x7",
        node_timeout=args.node_timeout,
        progress=lambda m: print(f"  {m}"),
    )
    artifacts = data_root() / "artifacts" / "week17"
    artifacts.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (artifacts / f"x7_{name}.json").write_text(json.dumps(result, indent=2, default=str))
    report = out_dir / f"x7_{name}.md"
    report.write_text(render_x7(result))
    for c in result["checks"]:
        print(f"  {'pass' if c['passed'] else 'FAIL'}  {c['criterion']}")
    ln = result["latency_normal_s"]
    print(f"  latency (normal phases) p50 {ln['p50']} s, p95 {ln['p95']} s; {result['seconds']} s")
    print(f"  report   {report}")
    return 0 if all(c["passed"] for c in result["checks"]) else 1


def fmt_float(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f}"


def cmd_x5(args: argparse.Namespace) -> int:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.training.neural import dp_hparams
    from finmesh.training.x5 import run_x5
    from finmesh.training.x5_report import render_x5

    paths = dataset_paths(args.dataset)
    hp = dp_hparams(paths.name)
    if hp.source == "A17 defaults" and args.dataset != FIXTURE_DATASET:
        print(
            "  no tuned DP settings for this regime; run `finmesh dp-tune` on the Small set first"
        )
        return 2
    seeds = tuple(int(s) for s in args.seeds.split(","))
    out_root = data_root() / "artifacts" / "week12"
    result = run_x5(
        paths,
        out_root,
        option=args.option,
        seeds=seeds,
        reps=args.reps,
        cap=args.cap,
        rounds=args.rounds,
        local_steps=args.local_steps,
        progress=lambda m: print(f"  {m}"),
        iid=not args.no_iid,
    )
    manifest = load_manifest(paths.manifest)
    stamp = Stamp(
        kind="x5",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split="val",
        params={
            "option": args.option,
            "seeds": list(seeds),
            "cap": args.cap,
            "rounds": args.rounds,
            "local_steps": args.local_steps,
            "hparams": hp.to_dict(),
            "run_id": result["run_id"],
            "iid": not args.no_iid,
        },
    )
    artifact = write_artifact(out_root / f"x5_{paths.name}.json", stamp, result)
    out_dir = out_root if args.dataset == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval"
    report = out_dir / f"x5_{paths.name}_A19.md"  # the A18 page (week 11) stays as it is
    report.write_text(render_x5(result))
    s = result["summary"]
    for eps, v in s["H2a"].items():
        b = s["H2b"][eps]
        line = (
            f"  eps {eps}: window {v['share_of_centralised']['estimate']:.2f} of centralised "
            f"(H2a {v['met_on_validation']}); window - account "
            f"{b['window_minus_account']['estimate']:+.4f} (H2b {b['met_on_validation']})"
        )
        if s.get("iid"):
            line += f"; IID - partitioned {s['iid'][eps]['iid_minus_partitioned']['estimate']:+.4f}"
        print(line)
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  report   {report}")
    return 0


def cmd_sealed_log(args: argparse.Namespace) -> int:
    from finmesh.eval.sealed import read_access_log

    entries = read_access_log(dataset_paths(args.dataset))
    if not entries:
        print("  the sealed test has never been opened")
    for e in entries:
        print(f"  {e['time']}  config {e['config_hash'][:12]}  seed {e['seed']}  {e['purpose']}")
    return 0


# --------------------------------------------------------------------------- week 18: test
TEST_BANNER = (
    "> **Sealed test (week 18).** Every model trained on the training partition; every "
    "calibration, threshold, fusion and attribution parameter fitted on validation and "
    "frozen; test scored label-free, then opened once per seed through the logged seal "
    "(`finmesh sealed-log`). Wording below that says *validation* in a column or check "
    "name refers to the frozen rule; every number is on **test**.\n\n"
)


def as_test_page(text: str) -> str:
    """A validation renderer's page, relabelled for the test run."""
    for a, b in (
        ("on validation", "on test"),
        ("On validation", "On test"),
        (" validation ·", " test ·"),
        ("validation windows", "test windows"),
        ("| Validation |", "| Test |"),
        ("Met on validation", "Met on test"),
        ("met on validation", "met on test"),
        ("Judged on test; validation shown here.", "Decided here, on test."),
        ("Judged on test.", "Decided here, on test."),
        ("pattern-labelled validation schemes", "pattern-labelled test schemes"),
        (
            "cross-fitted on the two time halves of validation",
            "fitted on all detected validation schemes and applied to the test schemes",
        ),
        ("detected validation schemes sampled", "detected test schemes sampled"),
    ):
        text = text.replace(a, b)
    lines = text.split("\n", 1)
    return lines[0] + "\n\n" + TEST_BANNER + (lines[1].lstrip("\n") if len(lines) > 1 else "")


def _test_out(paths: DatasetPaths) -> tuple[Path, Path]:
    art = data_root() / "artifacts" / "week18"
    out = art if paths.name == FIXTURE_DATASET else REPO_ROOT / "docs" / "eval" / "test"
    out.mkdir(parents=True, exist_ok=True)
    return art, out


def _stamp(paths: DatasetPaths, kind: str, params: dict[str, Any], split: str = "test") -> Any:
    from finmesh.data.manifest import load_manifest
    from finmesh.eval.provenance import Stamp

    manifest = load_manifest(paths.manifest)
    return Stamp(
        kind=kind,
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        split=split,
        params=params,
    )


def _ints(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in text.split(",") if x.strip())


def cmd_test_preflight(args: argparse.Namespace) -> int:
    from finmesh.eval.test_plan import preflight

    report = preflight(dataset_paths(args.dataset), args.option, args.only)
    for line in report["lines"]:
        print(f"  {line}")
    return 0 if report["ok"] else 1


def _a25_out(paths_name: str) -> tuple[Path, Path]:
    art = data_root() / "artifacts" / "a25"
    out = art if paths_name.startswith("FIXTURE") else REPO_ROOT / "docs" / "eval" / "a25"
    art.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    return art, out


def _ci3(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    if d.get("low") is None:
        return f"{d['estimate']:.3f}"
    return f"{d['estimate']:.3f} [{d['low']:.3f}, {d['high']:.3f}]"


def cmd_flag_frontier(args: argparse.Namespace) -> int:
    """A25 P3: protected S1 flags on validation (utility seeds 0-2, attacks seed 0)."""
    from finmesh.eval.provenance import write_artifact
    from finmesh.training.flags import run_flag_frontier

    paths = dataset_paths(args.dataset)
    r = run_flag_frontier(
        paths, args.option, _ints(args.seeds), args.reps, progress=lambda m: print(f"  {m}")
    )
    art, out = _a25_out(paths.name)
    stamp = _stamp(
        paths, "flag-frontier", {"option": args.option, "seeds": r["seeds"]}, split="val"
    )
    write_artifact(art / f"flag_frontier_{paths.name}.json", stamp, r)
    lines = [
        f"# Protected S1 flags on validation (A25 P3) · {paths.name}",
        "",
        f"Seeds {r['seeds']} for linked detection; attacks on seed 0. Share = (candidate − S0) "
        "/ (plain S1 − S0) in linked detection. Within margin = upper 95% bound of (attack − "
        "prior) TPR at 1% FPR ≤ 0.05 on every assessable A2/A3 target.",
        "",
        "| Candidate | Linked | Share of S1's gain | Within margin | Per target |",
        "| --- | --- | --- | --- | --- |",
    ]
    for n, v in r["candidates"].items():
        per = ", ".join(f"{t}: {'yes' if w else ('no' if w is False else '—')}"
                        for t, w in v["within_by_target"].items())  # fmt: skip
        lines.append(
            f"| {n} | {_ci3(v['linked'])} | {_ci3(v['share_of_S1_gain'])} | "
            f"{'yes' if v['within_margin'] else 'no'} | {per} |"
        )
        print(f"  {n:<20} share {_ci3(v['share_of_S1_gain'])}  within {v['within_margin']}")
    (out / f"flag_frontier_{paths.name}.md").write_text("\n".join(lines) + "\n")
    print(f"  report   {out / f'flag_frontier_{paths.name}.md'}")
    return 0


def cmd_budget_replay(args: argparse.Namespace) -> int:
    """A25 P4: adaptive token budget replayed on the saved X1 test runs (no new opening)."""
    from finmesh.eval.provenance import write_artifact
    from finmesh.training.budget_replay import render, run_budget_replay

    paths = dataset_paths(args.dataset)
    r = run_budget_replay(
        paths,
        args.option,
        _ints(args.seeds) if args.seeds else None,
        recompute_validation=not args.no_validation,
        cap_factor=args.cap_factor,
        progress=lambda m: print(f"  {m}"),
    )
    art, out = _a25_out(paths.name)
    tag = paths.name + (f"_cap{args.cap_factor:g}x" if args.cap_factor else "")
    stamp = _stamp(
        paths,
        "budget-replay",
        {"option": args.option, "cap": r["cap"]},
        split="test (saved X1 runs: token counts and audit rows; no new opening)",
    )
    write_artifact(art / f"budget_replay_{tag}.json", stamp, r)
    (out / f"budget_replay_{tag}.md").write_text(render(r) + "\n")
    print(f"  report   {out / f'budget_replay_{tag}.md'}")
    return 0


def cmd_benchmark_dataset(args: argparse.Namespace) -> int:
    """A25 P6: the benchmark dataset <source>-FULL (links to the source's raw files)."""
    from finmesh.data.benchmark_split import link_benchmark

    r = link_benchmark(data_root() / "raw", args.source)
    print(f"  {r['dataset']}: {r['how']} of {r['source']}'s raw files")
    print(f"  next: uv run finmesh week1 --dataset {r['dataset']}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """A25 P6: our detector on AMLworld's published split (transaction-level F1)."""
    from finmesh.eval.provenance import write_artifact
    from finmesh.training.benchmark import render, run_benchmark

    paths = dataset_paths(args.dataset)
    r = run_benchmark(
        paths,
        args.option,
        _ints(args.seeds),
        args.negative_rate,
        progress=lambda m: print(f"  {m}"),
    )
    art, out = _a25_out(paths.name)
    stamp = _stamp(
        paths,
        "benchmark",
        {"option": args.option, "seeds": r["seeds"]},
        split="AMLworld benchmark split (train/val/test by day 60/20/20)",
    )
    write_artifact(art / f"benchmark_{r['source']}.json", stamp, r)
    report = out / f"benchmark_{r['source']}.md"
    report.write_text(render(r) + "\n")
    for m in ("A", "B"):
        x = r["models"][m]
        print(f"  model {m}: test F1 {x['test_f1_mean']:.2f} ± {x['test_f1_sd']:.2f}  "
              f"val F1 {x['val_f1_mean']:.2f}")  # fmt: skip
    print(f"  report   {report}")
    return 0


def cmd_plus_validation(args: argparse.Namespace) -> int:
    """A25 P6 adequacy: the stronger-detector track on validation, next to the current one."""
    from finmesh.eval.provenance import write_artifact
    from finmesh.sysinfo import AnonPeak
    from finmesh.training.sealed_runs import PLUS_CONFIGS
    from finmesh.training.x1 import _recovery, _Stack, combine, run_seed

    paths = dataset_paths(args.dataset)
    detectors = ("tx", "gbdt") if args.compare else ("tx",)
    out_rows: dict[str, Any] = {}
    for det in detectors:
        per_seed = []
        with AnonPeak() as anon:
            for seed in _ints(args.seeds):
                r = run_seed(
                    paths,
                    args.option,
                    seed,
                    args.reps,
                    args.window_reps,
                    anon,
                    sweeps=False,
                    audit=False,
                    only=PLUS_CONFIGS,
                    detector=det,
                )
                per_seed.append(r)
                print(f"  {det} seed {seed}: {r['seconds']['total']:.0f} s, "
                      f"peak token use {r['token_peak']:,} per bank and epoch")  # fmt: skip
        summary = combine(per_seed, args.reps)
        stack = _Stack(per_seed)
        out_rows[det] = {
            "linked": {c: summary[c]["linked"] for c in sorted(PLUS_CONFIGS) if c in summary},
            "gain_S2": summary["S2/stacker"].get("linked_gain", {}).get("difference"),
            "recovery": _recovery(stack, "S2/stacker", args.reps, "oracle-relational"),
            "peak_anon_mb": anon.mb,
            "token_peak": max(r["token_peak"] for r in per_seed),
            "candidates": [r["candidates"] for r in per_seed],
        }
    art, out = _a25_out(paths.name)
    stamp = _stamp(paths, "plus-validation", {"option": args.option, "seeds": args.seeds},
                   split="val")  # fmt: skip
    write_artifact(art / f"plus_validation_{paths.name}.json", stamp, out_rows)
    label = {"tx": "+ (transaction detector)", "gbdt": "current (account-window LightGBM)"}
    lines = [
        f"# Stronger-detector track on validation (A25 P6 adequacy) · {paths.name}",
        "",
        f"Seeds {args.seeds}. Linked scheme detection; gain = S2 − S0 (paired, scheme "
        "bootstrap); recovery = (S2 − S0) / (relational oracle − S0), as H1b. Token "
        "requests: the current detector is metered at the frozen A16 budget; the + track "
        "is served in full and its peak is shown against that budget.",
        "",
        "| Detector | S0 | S2 | Oracle | Relational oracle | S2 − S0 | Recovery | Candidates "
        "(mean) | Peak tokens per bank-epoch |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for det, v in out_rows.items():
        lk = v["linked"]
        lines.append(
            f"| {label[det]} | {_ci3(lk.get('S0'))} | {_ci3(lk.get('S2/stacker'))} | "
            f"{_ci3(lk.get('oracle'))} | {_ci3(lk.get('oracle-relational'))} | "
            f"{_ci3(v['gain_S2'])} | {_ci3(v['recovery'])} | "
            f"{sum(v['candidates']) / len(v['candidates']):,.0f} | {v['token_peak']:,} |"
        )
    report = out / f"plus_validation_{paths.name}.md"
    report.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-len(out_rows) :]))
    print(f"  report   {report}")
    return 0


def cmd_benchmark_table(args: argparse.Namespace) -> int:
    """A25 P6: one table over every benchmark run so far."""
    from finmesh.training.benchmark import render_table

    art = data_root() / "artifacts" / "a25"
    results = []
    for f in sorted(art.glob("benchmark_*.json")):
        doc = json.loads(f.read_text())
        results.append(doc.get("result", doc))
    if not results:
        print("  no benchmark runs yet; run `finmesh benchmark --dataset <source>-FULL`")
        return 1
    out = REPO_ROOT / "docs" / "eval" / "a25" / "benchmark_table.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_table(results))
    print(out.read_text())
    return 0


def cmd_flag_select(args: argparse.Namespace) -> int:
    """A25 P3: the frozen selection rule over the Medium validation frontiers."""
    from finmesh.eval.provenance import read_artifact
    from finmesh.training.flags import select_flag

    names = [d.strip() for d in args.datasets.split(",") if d.strip()]
    art, out = _a25_out(names[0])
    frontiers = []
    for n in names:
        path = art / f"flag_frontier_{n}.json"
        if not path.exists():
            print(f"  {path} missing; run `finmesh flag-frontier --dataset {n}` first")
            return 1
        frontiers.append(read_artifact(path)[1])
    sel = select_flag(frontiers)
    (art / "flag_selection.json").write_text(json.dumps(sel, indent=1))
    lines = [
        "# Protected S1 flag: selection by the frozen A25 P3 rule",
        "",
        f"Datasets: {', '.join(names)} (validation). Rule: among candidates within the H1c "
        "margin on every assessable target of every dataset, the largest mean share of plain "
        "S1's gain; ties to the smaller ε, then ungated; none if none qualifies.",
        "",
        f"**Chosen: {sel['chosen'] or 'none'}**"
        + (f" ({sel['reason']})" if not sel["chosen"] else ""),
        "",
        "| Candidate | Within margin on all | Mean share of S1's gain |",
        "| --- | --- | --- |",
    ]
    for n, v in sel["table"].items():
        lines.append(
            f"| {n} | {'yes' if v['within_margin_all'] else 'no'} | "
            f"{v['mean_share_of_S1_gain']:.3f} |"
        )
    (out / "flag_selection.md").write_text("\n".join(lines) + "\n")
    print(f"  chosen: {sel['chosen'] or 'none'}")
    print(f"  report   {out / 'flag_selection.md'}")
    return 0


def cmd_size_budget(args: argparse.Namespace) -> int:
    """A25 P1: the A16 token budget of a new dataset, from its validation traffic only."""
    from finmesh.matching.tokens import BUDGETS_PATH
    from finmesh.training.sealed_runs import token_traffic

    paths = dataset_paths(args.dataset)
    rows = token_traffic(paths, args.option, partitions=("val",), calibrations=("end of training",))
    peak = rows[0]["peak_tokens"]
    doc = json.loads(BUDGETS_PATH.read_text())
    doc.setdefault("measured_peak", {})[paths.name] = peak
    doc["budgets"][paths.name] = 2 * peak
    BUDGETS_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    where = rows[0]["peak_member_epoch"]
    print(f"  {paths.name}: validation peak {peak:,} tokens (bank/epoch {where})")
    print(f"  budget {2 * peak:,} written to {BUDGETS_PATH.name}")
    return 0


def cmd_narrative_export(args: argparse.Namespace) -> int:
    """A25 P5: write the narrative cases to one file for a remote (GPU) model run."""
    from finmesh.attribution.narrative_cases import export_cases

    paths = dataset_paths(args.dataset)
    bundle = export_cases(
        paths, args.option, args.n, args.protocol, "test" if args.test else "val", args.allow_repeat
    )
    if "error" in bundle:
        print(f"  {bundle['error']}")
        return 1
    out = Path(args.out)
    out.write_text(json.dumps(bundle, default=str))
    print(f"  {len(bundle['cases'])} cases ({bundle['split']}, {bundle['protocol']}) -> {out}")
    print(
        "  run them on the GPU notebook with `finmesh narrative-cases`, then bring back the result"
    )
    return 0


def cmd_narrative_cases(args: argparse.Namespace) -> int:
    """A25 P5: narrate an exported case file with a local Ollama model (no dataset needed)."""
    from finmesh.attribution.narrative import MAX_TOKENS, TIMEOUT_S, ollama_call
    from finmesh.attribution.narrative_cases import run_cases

    bundle = json.loads(Path(args.cases).read_text())
    proto = bundle["protocol"]
    call = ollama_call(args.url, args.model, TIMEOUT_S[proto], max_tokens=MAX_TOKENS[proto])
    out = Path(args.out)
    ckpt = out.with_suffix(".partial.json")
    result = run_cases(bundle, call, args.model, ckpt, progress=lambda m: print(f"  {m}"))
    if "error" in result:
        print(f"  {result['error']}")
        return 1
    out.write_text(json.dumps(result, default=str))
    s = result["summary"]
    print(f"  H3b grounding {s['H3b']['grounding']['estimate']}; strict "
          f"{s['strict_grounding']['estimate']}; result -> {out}")  # fmt: skip
    return 0


def cmd_narrative_render(args: argparse.Namespace) -> int:
    """A25 P5: the pages of a narrative result file (and N4, select-then-template)."""
    from finmesh.attribution.narrative_cases import select_then_template
    from finmesh.attribution.narrative_report import render_narrative, write_cases, write_review_ab
    from finmesh.training.x6 import load_catalogue

    result = json.loads(Path(args.result).read_text())
    if args.select:
        result = select_then_template(result, load_catalogue())
    art, out = _a25_out(result["dataset"])
    tag = args.model_tag or result["model"].replace(":", "-").replace("/", "-")
    tag += "_N4" if args.select else ""
    name = f"narrative_{result['dataset']}_{result['split']}_{tag}"
    (art / f"{name}.json").write_text(json.dumps(result, default=str))
    page = render_narrative(result)
    (out / f"{name}.md").write_text(as_test_page(page) if result["split"] == "test" else page)
    write_cases(result, out / f"{name}_cases.jsonl")
    if args.review:
        write_review_ab(
            result, out / f"{name}_review.csv", out / f"{name}_review_KEY_do_not_open.csv"
        )
    s = result["summary"]
    h3b, strict = s["H3b"]["grounding"]["estimate"], s["strict_grounding"]["estimate"]
    print(f"  {name}: H3b {h3b}; strict {strict}; scope ok (first) {s.get('first_scope_ok')}")
    print(f"  report   {out / (name + '.md')}")
    return 0


def cmd_large_window(args: argparse.Namespace) -> int:
    """A25 P1: cut the dense-period window of a Large set into a dataset of its own."""
    from finmesh.data.window import cut_window

    r = cut_window(data_root() / "raw", args.source, args.days)
    print(f"  {r['dataset']}: days {r['window'][0]} to {r['window'][1]} "
          f"(dense period {r['dense_period'][0]} to {r['dense_period'][1]})")  # fmt: skip
    print(f"  transactions {r['transactions']:,}; pattern blocks kept "
          f"{r['pattern_blocks']['kept']:,} of {r['pattern_blocks']['source']:,}")  # fmt: skip
    print(f"  next: uv run finmesh week1 --dataset {r['dataset']}")
    return 0


def cmd_test_traffic(args: argparse.Namespace) -> int:
    from finmesh.training.sealed_runs import token_traffic

    paths = dataset_paths(args.dataset)
    rows = token_traffic(paths, args.option)
    out = data_root() / "artifacts" / "week18" / f"traffic_{paths.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    print(f"  {'partition':<9} {'calibration':<22} {'candidates':>10} {'alerts':>7} "
          f"{'mean p':>8} {'peak tokens':>11} {'member/epoch':>12} {'budget':>7}")  # fmt: skip
    for r in rows:
        print(
            f"  {r['partition'] + ' ' + r['windows']:<9} {r['calibration']:<22} "
            f"{r['candidates']:>10,} {r['alerts']:>7,} {r['mean_prob']:>8.4f} "
            f"{r['peak_tokens']:>11,} {r['peak_member_epoch']:>12} {r['budget']:>7,}"
        )
    print(f"  details  {out}")
    return 0


def cmd_test_x1(args: argparse.Namespace) -> int:
    from finmesh.eval.provenance import write_artifact
    from finmesh.training.sealed_runs import run_x1_test
    from finmesh.training.x1_report import (
        frontier_figure,
        ladder_figure,
        render_audit,
        render_x1,
        render_x3,
        x3_figure,
    )
    from finmesh.training.x6 import ATTRIBUTOR, LEVELS, load_catalogue
    from finmesh.training.x6_report import render_x6

    paths = dataset_paths(args.dataset)
    params = {
        "option": args.option,
        "headline_seeds": list(_ints(args.headline_seeds)),
        "seeds": list(_ints(args.seeds)),
        "reps": args.reps,
        "window_reps": args.window_reps,
        "sweeps": not args.no_sweeps,
        "audit": not args.no_audit,
        "x6": not args.no_x6,
    }
    result = run_x1_test(
        paths,
        option=args.option,
        headline_seeds=_ints(args.headline_seeds),
        other_seeds=_ints(args.seeds),
        reps=args.reps,
        window_reps=args.window_reps,
        sweeps=not args.no_sweeps,
        audit=not args.no_audit,
        x6=not args.no_x6,
        allow_repeat=args.allow_repeat,
        progress=lambda m: print(f"  {m}"),
        flags=tuple(args.flag or ()),
        feature_set="no_artefacts" if args.noart else "all",
        detector="tx" if args.plus else "gbdt",
    )
    art, out = _test_out(paths)
    name = option_tag(paths.name, args.option) + ("_noart" if args.noart else "")
    name += "_plus" if args.plus else ""
    artifact = write_artifact(
        art / f"x1_test_{name}.json", _stamp(paths, "x1-test", params), result
    )
    ladder = ladder_figure(result, out / f"ladder_{name}.png")
    (out / f"x1_{name}.md").write_text(as_test_page(render_x1(result, ladder.name)))
    if result.get("sweeps"):
        fig = x3_figure(result, out / f"x3_{name}.png")
        (out / f"x3_{name}.md").write_text(
            as_test_page(render_x3(result, fig.name if fig else None))
        )
    if result.get("audit"):
        fig = frontier_figure(result, out / f"frontier_{name}.png")
        page = render_audit(result, fig.name if fig else None)
        (out / f"audit_{name}.md").write_text(as_test_page(page))
    if result.get("x6"):
        x6 = result["x6"]
        page = render_x6(
            {
                "dataset": paths.name,
                "option": args.option,
                "seeds": x6["seeds"],
                "levels": dict(LEVELS),
                "attributor": ATTRIBUTOR,
                "catalogue_version": load_catalogue()["version"],
                "summary": x6["summary"],
                "per_seed": x6["per_seed"],
                "seconds": result["seconds"],
                "peak_anon_mb": result["peak_anon_mb"],
            }
        )
        (out / f"x6_{name}.md").write_text(as_test_page(page))
    s = result["summary"]
    for key in ("S0", "S2/stacker", "oracle", "oracle-relational"):
        v = s.get(key)
        if v:
            g = v.get("linked_gain", {})
            p = g.get("p_holm", g.get("p"))
            extra = "" if p is None else f"  p {'(Holm) ' if 'p_holm' in g else ''}{p:.4f}"
            print(f"  {key:<18} linked {v['linked']['estimate']:.3f}{extra}")
    h = s.get("H1b", {}).get("oracle-relational", {}).get("S2/stacker") or {}
    if h.get("estimate") is not None:
        print(f"  H1b: S2 recovers {h['estimate']:.2f} [{h['low']:.2f}, {h['high']:.2f}]")
    if result.get("x6"):
        print(f"  H3a met on test: {result['x6']['summary']['H3a']['met']}")
    use = result.get("token_use") or {}
    if use.get("peak"):
        print(
            f"  token use: peak {use['peak']['used']:,} vs frozen budget "
            f"{use['frozen_budget']:,}; {use['share_beyond_budget']:.1%} beyond it (served)"
        )
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    print(f"  reports  {out}")
    return 0


def cmd_test_baselines(args: argparse.Namespace) -> int:
    from finmesh.eval.provenance import write_artifact
    from finmesh.training.report import render_baselines
    from finmesh.training.sealed_runs import run_baselines_test

    paths = dataset_paths(args.dataset)
    result = run_baselines_test(
        paths, option=args.option, reps=args.reps, allow_repeat=args.allow_repeat
    )
    art, out = _test_out(paths)
    name = option_tag(paths.name, args.option)
    params = {"option": args.option, "seed": 0, "reps": args.reps}
    artifact = write_artifact(
        art / f"baselines_test_{name}.json", _stamp(paths, "baselines-test", params), result
    )
    (out / f"baselines_{name}.md").write_text(as_test_page(render_baselines(result)))
    c = result["comparisons"]
    for pair in ("oracle - S0-BG", "oracle-noart - S0-BG-noart", "S0-BG - S0-B"):
        d = c[pair]["linked"]["difference"]
        print(f"  {pair:<28} linked {d['estimate']:+.3f} [{d['low']:+.3f}, {d['high']:+.3f}]")
    w = c["S0-BG - S0-B"]["window"]["auprc_difference"]
    print(f"  PT4b AUPRC S0-BG - S0-B {w['estimate']:+.4f} [{w['low']:+.4f}, {w['high']:+.4f}]")
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    return 0


def _x5_artifact(paths: DatasetPaths) -> dict[str, Any] | None:
    from finmesh.eval.provenance import read_artifact

    path = data_root() / "artifacts" / "week12" / f"x5_{paths.name}.json"
    if not path.exists():
        print(f"  no week-12 X5 run for {paths.name} ({path}); the test scores its saved models")
        return None
    return read_artifact(path)[1]


def cmd_test_x5(args: argparse.Namespace) -> int:
    from finmesh.eval.provenance import write_artifact
    from finmesh.eval.sealed import EvalStore
    from finmesh.training.sealed_runs import opener_for
    from finmesh.training.x5 import run_x5_test
    from finmesh.training.x5_report import render_x5

    paths = dataset_paths(args.dataset)
    x5 = _x5_artifact(paths)
    if x5 is None:
        return 2
    opener = opener_for(EvalStore(paths, args.option), args.allow_repeat)
    result = run_x5_test(
        paths,
        x5,
        opener,
        option=args.option,
        reps=args.reps,
        progress=lambda m: print(f"  {m}"),
        allow_repeat=args.allow_repeat,
    )
    art, out = _test_out(paths)
    params = {"option": args.option, "x5_run": x5["run_id"], "reps": args.reps}
    artifact = write_artifact(
        art / f"x5_test_{paths.name}.json", _stamp(paths, "x5-test", params), result
    )
    (out / f"x5_{paths.name}.md").write_text(as_test_page(render_x5(result)))
    s = result["summary"]
    for eps, h in s["H2a"].items():
        print(
            f"  eps {eps}: H2a share {h['share_of_centralised']['estimate']:.2f}, "
            f"minus local {h['minus_local']['estimate']:+.4f}; "
            f"H2b window - account {s['H2b'][eps]['window_minus_account']['estimate']:+.4f}"
        )
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    return 0


def cmd_test_ensemble(args: argparse.Namespace) -> int:
    from finmesh.eval.provenance import write_artifact
    from finmesh.eval.sealed import EvalStore
    from finmesh.training.ensemble import run_ensemble_test
    from finmesh.training.ensemble_report import render_ensemble
    from finmesh.training.sealed_runs import opener_for

    paths = dataset_paths(args.dataset)
    x5 = _x5_artifact(paths)
    if x5 is None:
        return 2
    opener = opener_for(EvalStore(paths, args.option), args.allow_repeat)
    result = run_ensemble_test(
        paths,
        x5,
        opener,
        option=args.option,
        reps=args.reps,
        progress=lambda m: print(f"  {m}"),
        allow_repeat=args.allow_repeat,
    )
    art, out = _test_out(paths)
    params = {"option": args.option, "x5_run": x5["run_id"], "reps": args.reps}
    artifact = write_artifact(
        art / f"ensemble_test_{paths.name}.json", _stamp(paths, "ensemble-test", params), result
    )
    (out / f"ensemble_{paths.name}.md").write_text(as_test_page(render_ensemble(result)))
    for k, g in result["summary"]["gain_over_local"].items():
        print(f"  + {k}: {g['estimate']:+.4f} [{g['low']:+.4f}, {g['high']:+.4f}]")
    print(f"  {result['seconds']:.0f} s, peak memory {result['peak_anon_mb']} MB")
    print(f"  artifact {artifact}")
    return 0


def cmd_test_report(args: argparse.Namespace) -> int:
    from finmesh.eval.test_report import write_results

    art = data_root() / "artifacts" / "week18"
    target = art if args.fixture else REPO_ROOT / "docs" / "eval" / "test"
    page = write_results(art, target / "RESULTS.md", fixture=args.fixture)
    print(f"  report   {page}")
    return 0


def cmd_a25_report(args: argparse.Namespace) -> int:
    """A25: the Large confirmation's rules decided on its sealed tests, one page."""
    from finmesh.eval.a25_report import LARGE, write_a25_results

    root = data_root() / "artifacts"
    page = write_a25_results(
        root / "week18", root / "a25", REPO_ROOT / "docs" / "eval" / "a25" / "RESULTS_LARGE.md",
        tuple(args.datasets.split(",")) if args.datasets else LARGE,
    )  # fmt: skip
    print(page.read_text())
    print(f"  report   {page}")
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

    fd = sub.add_parser("federation", help="membership for a federation option, e.g. A64 (week 13)")
    add_dataset(fd)
    fd.add_argument("--option", required=True, help="A8, A64, B8, B8c50 (A21 coverage), ...")
    fd.add_argument("--force", action="store_true", help="rebuild an existing membership file")
    fd.set_defaults(func=cmd_federation)

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

    fe = sub.add_parser("features", help="features for every account-window (week 4)")
    fe.add_argument("--dataset", required=True)
    fe.add_argument("--option", default="B8")
    fe.add_argument(
        "--view",
        default="member",
        choices=("member", "pooled"),
        help="member: what each bank sees; pooled: the oracle's full graph (needs member first)",
    )
    fe.add_argument(
        "--degree-cap",
        type=int,
        default=0,
        help="member view with at most D counterparties per account (week 11; needs member)",
    )
    fe.set_defaults(func=cmd_features)

    fr = sub.add_parser("feature-report", help="single-feature signal on validation (week 4)")
    fr.add_argument("--dataset", required=True)
    fr.add_argument("--option", default="B8")
    fr.set_defaults(func=cmd_feature_report)

    dg = sub.add_parser("diagnose", help="positives, pattern visibility, feature drift (week 4)")
    dg.add_argument("--dataset", required=True)
    dg.add_argument("--option", default="B8")
    dg.set_defaults(func=cmd_diagnose)

    bl = sub.add_parser("baselines", help="S0, oracle and unsupervised baselines (week 5)")
    bl.add_argument("--dataset", required=True)
    bl.add_argument("--option", default="B8")
    bl.add_argument("--seed", type=int, default=0)
    bl.add_argument("--reps", type=int, default=1000, help="bootstrap replicates")
    bl.add_argument("--draws", type=int, default=20, help="random-alert draws for linked detection")
    bl.set_defaults(func=cmd_baselines)

    sub.add_parser("g1", help="Gate G1 evidence from the baseline artifacts (week 5)").set_defaults(
        func=cmd_g1
    )

    sub.add_parser("g2", help="Gate G2 evidence from the X1 artifacts (week 9)").set_defaults(
        func=cmd_g2
    )
    ds = sub.add_parser("demo-slice", help="thin demo slice: one alert end to end (week 9)")
    ds.add_argument("--dataset", required=True)
    ds.add_argument("--option", default="B8")
    ds.add_argument("--alerts", type=int, default=50, help="sessions to time")
    ds.add_argument("--seed", type=int, default=0)
    ds.set_defaults(func=cmd_demo_slice)

    dt = sub.add_parser(
        "dp-tune", help="DP clip norm and batch on the proxy federation, HI/LI-Small (week 11)"
    )
    dt.add_argument("--dataset", required=True)
    dt.add_argument("--option", default="B8")
    dt.add_argument("--rounds", type=int, default=50)
    dt.add_argument(
        "--local-steps", type=int, default=None, help="override the grid's local steps (CI only)"
    )
    dt.add_argument("--quick", action="store_true", help="two settings only (CI)")
    dt.add_argument(
        "--grid", default="A19", choices=("A18", "A19"), help="A19 = the week-12 retune"
    )
    dt.set_defaults(func=cmd_dp_tune)

    inf = sub.add_parser(
        "influence", help="indirect influence of an account, with and without the cap (week 11)"
    )
    inf.add_argument("--dataset", required=True)
    inf.add_argument("--option", default="B8")
    inf.add_argument("--cap", type=int, default=16)
    inf.add_argument("--sample", type=int, default=200, help="accounts removed")
    inf.set_defaults(func=cmd_influence)

    x5 = sub.add_parser(
        "x5", help="X5: privacy unit, degree cap and IID arm, tuned DP (weeks 11-12)"
    )
    x5.add_argument("--dataset", required=True)
    x5.add_argument("--option", default="B8")
    x5.add_argument("--seeds", default="0,1,2")
    x5.add_argument("--reps", type=int, default=200)
    x5.add_argument("--cap", type=int, default=16)
    x5.add_argument("--rounds", type=int, default=50)
    x5.add_argument("--local-steps", type=int, default=20)
    x5.add_argument("--no-iid", action="store_true", help="skip the IID arm (proposal cut order)")
    x5.set_defaults(func=cmd_x5)

    mia = sub.add_parser(
        "membership", help="A5 on the federated model: membership inference (week 12)"
    )
    mia.add_argument("--dataset", required=True)
    mia.add_argument("--option", default="B8")
    mia.add_argument("--cap", type=int, default=16)
    mia.add_argument("--reps", type=int, default=200)
    mia.add_argument("--rounds", type=int, default=50)
    mia.add_argument("--local-steps", type=int, default=20)
    mia.set_defaults(func=cmd_membership)

    en = sub.add_parser("ensemble", help="X4 part 2: stacked ensemble on X5's models (week 12)")
    en.add_argument("--dataset", required=True)
    en.add_argument("--option", default="B8")
    en.add_argument("--reps", type=int, default=200)
    en.set_defaults(func=cmd_ensemble)
    sub.add_parser("g3", help="Gate G3 evidence and rule outcome (week 12)").set_defaults(
        func=cmd_g3
    )

    x6 = sub.add_parser("x6", help="X6: pattern attribution by sharing level (week 13)")
    x6.add_argument("--dataset", required=True)
    x6.add_argument("--option", default="B8")
    x6.add_argument("--seeds", default="0,1,2")
    x6.add_argument("--reps", type=int, default=1000, help="scheme bootstrap replicates")
    x6.set_defaults(func=cmd_x6)

    nr = sub.add_parser("narrative", help="A21/H3b: constrained case narratives (week 14)")
    nr.add_argument("--dataset", required=True)
    nr.add_argument("--option", default="B8")
    nr.add_argument("--n", type=int, default=200, help="cases to narrate (stratified)")
    nr.add_argument("--model", default="llama3.2:3b")
    nr.add_argument("--url", default="http://localhost:11434", help="local Ollama only")
    nr.add_argument(
        "--timeout", type=float, default=None, help="seconds per call (A21: 120, A22: 600)"
    )
    nr.add_argument("--protocol", default="A23", choices=["A21", "A22", "A23"])
    nr.add_argument(
        "--test", action="store_true", help="week 18: A23 on test (after `finmesh test-x1`)"
    )
    nr.add_argument("--allow-repeat", action="store_true")
    nr.add_argument(
        "--pages-only",
        action="store_true",
        help="with --test: rewrite the pages from the saved result (no model, no opening)",
    )
    nr.set_defaults(func=cmd_narrative)

    db = sub.add_parser("demo-build", help="week 16: demo world from real validation data")
    db.add_argument("--dataset", required=True)
    db.add_argument("--option", default="B8")
    db.add_argument(
        "--alerts", type=int, default=200, help="alerts with cross-member counterparties"
    )
    db.add_argument("--seed", type=int, default=0)
    db.set_defaults(func=cmd_demo_build)

    dr = sub.add_parser("demo-run", help="week 16: the demo world through the services")
    dr.add_argument("--dataset", required=True)
    dr.add_argument("--limit", type=int, default=None, help="only the first N alerts")
    dr.set_defaults(func=cmd_demo_run)

    x7 = sub.add_parser("x7", help="week 17: X7 latency, faults, probes and resources")
    x7.add_argument("--dataset", help="a dataset with a demo world (finmesh demo-build)")
    x7.add_argument("--smoke", action="store_true", help="a small synthetic world instead")
    x7.add_argument("--node-timeout", type=float, default=2.0, help="client timeout, seconds")
    x7.set_defaults(func=cmd_x7)

    co = sub.add_parser("console", help="week 16: the analyst console and privacy ledger")
    co.add_argument("--dataset", required=True)
    co.add_argument("--port", type=int, default=8050)
    co.add_argument(
        "--host",
        default="127.0.0.1",
        help="bind address; keep 127.0.0.1 except inside a container (compose maps it to "
        "the host's 127.0.0.1 only)",
    )
    co.set_defaults(func=cmd_console)

    rv = sub.add_parser("narrative-review", help="A23: score the owner's blind A/B review")
    rv.add_argument("--dataset", required=True)
    rv.add_argument("--option", default="B8")
    rv.add_argument("--raters", default="allaudin,ravi", help="one sheet copy per rater")
    rv.add_argument(
        "--prepare", action="store_true", help="write each rater's blank copy of the sheet"
    )
    rv.set_defaults(func=cmd_narrative_review)

    cv = sub.add_parser("coverage", help="A21 coverage curve from the X1 artifacts (week 14)")
    cv.add_argument("--dataset", required=True)
    cv.set_defaults(func=cmd_coverage)

    x4 = sub.add_parser("x4", help="X4 part 1: neural scorer, FedAvg and DP-SGD (week 10)")
    x4.add_argument("--dataset", required=True)
    x4.add_argument("--option", default="B8")
    x4.add_argument("--seeds", default="0,1,2")
    x4.add_argument("--reps", type=int, default=200, help="bootstrap replicates")
    x4.add_argument("--rounds", type=int, default=50)
    x4.add_argument("--local-steps", type=int, default=20)
    x4.set_defaults(func=cmd_x4)

    sh = sub.add_parser("share", help="in-process sharing protocol run, S0/S1/S2 (week 6)")
    sh.add_argument("--dataset", required=True)
    sh.add_argument("--option", default="B8")
    sh.add_argument("--seed", type=int, default=0)
    sh.add_argument("--reps", type=int, default=1000, help="bootstrap replicates")
    sh.set_defaults(func=cmd_share)

    x1 = sub.add_parser(
        "x1", help="X1-X3 on validation: sharing ladder, S3/PD sweeps, audit A1-A3 (weeks 7-8)"
    )
    x1.add_argument("--dataset", required=True)
    x1.add_argument("--option", default="B8")
    x1.add_argument("--seeds", default="0,1,2", help="comma-separated seeds")
    x1.add_argument("--reps", type=int, default=1000, help="bootstrap replicates")
    x1.add_argument("--no-sweeps", action="store_true", help="skip the S3 and PD sweeps (X3)")
    x1.add_argument("--no-audit", action="store_true", help="skip the leakage audit (X2)")
    x1.set_defaults(func=cmd_x1)

    tp = sub.add_parser("test-preflight", help="week 18: check everything before opening the test")
    tp.add_argument("--dataset", required=True)
    tp.add_argument("--option", default="B8")
    tp.add_argument(
        "--only",
        default="x1,baselines,x5,ensemble,narrative",
        help="comma-separated runs to check",
    )
    tp.set_defaults(func=cmd_test_preflight)

    ff = sub.add_parser("flag-frontier", help="A25 P3: protected S1 flags on validation")
    ff.add_argument("--dataset", required=True)
    ff.add_argument("--option", default="B8")
    ff.add_argument("--seeds", default="0,1,2")
    ff.add_argument("--reps", type=int, default=1000)
    ff.set_defaults(func=cmd_flag_frontier)

    fs = sub.add_parser("flag-select", help="A25 P3: apply the frozen flag selection rule")
    fs.add_argument("--datasets", default="HI-Medium,LI-Medium")
    fs.set_defaults(func=cmd_flag_select)

    bd = sub.add_parser("benchmark-dataset", help="A25 P6: make <source>-FULL")
    bd.add_argument("--source", required=True)
    bd.set_defaults(func=cmd_benchmark_dataset)

    bm = sub.add_parser("benchmark", help="A25 P6: transaction F1 on the published split")
    bm.add_argument("--dataset", required=True, help="a <source>-FULL dataset")
    bm.add_argument("--option", default="B8")
    bm.add_argument("--seeds", default="0,1,2,3,4")
    bm.add_argument("--negative-rate", type=float, default=0.1)
    bm.set_defaults(func=cmd_benchmark)

    pv = sub.add_parser("plus-validation", help="A25 P6: the S0+/S2+/oracle+ track on validation")
    pv.add_argument("--dataset", required=True)
    pv.add_argument("--option", default="B8")
    pv.add_argument("--seeds", default="0,1,2")
    pv.add_argument("--reps", type=int, default=1000)
    pv.add_argument("--window-reps", type=int, default=200)
    pv.add_argument("--compare", action=argparse.BooleanOptionalAction, default=True,
                    help="also run the current detector on the same seeds")  # fmt: skip
    pv.set_defaults(func=cmd_plus_validation)

    ar = sub.add_parser("a25-report", help="A25: the Large confirmation's results page")
    ar.add_argument("--datasets", default="", help="default: HI-Large-W16,LI-Large-W16")
    ar.set_defaults(func=cmd_a25_report)

    bt = sub.add_parser("benchmark-table", help="A25 P6: table over the benchmark runs")
    bt.set_defaults(func=cmd_benchmark_table)

    br = sub.add_parser("budget-replay", help="A25 P4: adaptive token budget replay")
    br.add_argument("--dataset", required=True)
    br.add_argument("--option", default="B8")
    br.add_argument("--seeds", default="", help="default: every saved X1 test seed")
    br.add_argument(
        "--cap-factor", type=float, default=None, help="also cap budgets at this multiple of A16"
    )
    br.add_argument(
        "--no-validation", action="store_true", help="skip recomputing validation history"
    )
    br.set_defaults(func=cmd_budget_replay)

    sb = sub.add_parser("size-budget", help="A25 P1: A16 token budget from validation traffic")
    sb.add_argument("--dataset", required=True)
    sb.add_argument("--option", default="B8")
    sb.set_defaults(func=cmd_size_budget)

    ne = sub.add_parser("narrative-export", help="A25 P5: narrative cases to one file")
    ne.add_argument("--dataset", required=True)
    ne.add_argument("--option", default="B8")
    ne.add_argument("--n", type=int, default=200)
    ne.add_argument("--protocol", default="A25N", choices=["A23", "A25N"])
    ne.add_argument("--test", action="store_true", help="the sealed test (logs the opening)")
    ne.add_argument("--allow-repeat", action="store_true")
    ne.add_argument("--out", required=True)
    ne.set_defaults(func=cmd_narrative_export)

    nc = sub.add_parser("narrative-cases", help="A25 P5: narrate an exported case file")
    nc.add_argument("--cases", required=True)
    nc.add_argument("--model", required=True)
    nc.add_argument("--url", default="http://localhost:11434")
    nc.add_argument("--out", required=True)
    nc.set_defaults(func=cmd_narrative_cases)

    nn = sub.add_parser("narrative-render", help="A25 P5: pages of a narrative result file")
    nn.add_argument("--result", required=True)
    nn.add_argument("--select", action="store_true", help="N4: select-then-template")
    nn.add_argument("--model-tag", default=None)
    nn.add_argument("--review", action="store_true", help="also write a blind A/B sheet")
    nn.set_defaults(func=cmd_narrative_render)

    lw = sub.add_parser("large-window", help="A25 P1: dense-period window of HI/LI-Large")
    lw.add_argument("--source", required=True, choices=["HI-Large", "LI-Large", "FIXTURE-Small"])
    lw.add_argument("--days", type=int, default=16)
    lw.set_defaults(func=cmd_large_window)

    tt = sub.add_parser(
        "test-traffic", help="week 18: label-free token demand on validation and test"
    )
    tt.add_argument("--dataset", required=True)
    tt.add_argument("--option", default="B8")
    tt.set_defaults(func=cmd_test_traffic)

    tx = sub.add_parser("test-x1", help="week 18: X1-X3 (+ X6) on the sealed test")
    tx.add_argument("--dataset", required=True)
    tx.add_argument("--option", default="B8")
    tx.add_argument("--headline-seeds", default="0,1,2,3,4", help="S0, oracles, S2, PD")
    tx.add_argument("--seeds", default="0,1,2", help="every configuration")
    tx.add_argument("--reps", type=int, default=1000, help="scheme bootstrap replicates")
    tx.add_argument("--window-reps", type=int, default=1000, help="account bootstrap replicates")
    tx.add_argument("--no-sweeps", action="store_true", help="skip the S3 and PD sweeps")
    tx.add_argument("--no-audit", action="store_true", help="skip the leakage audit")
    tx.add_argument("--no-x6", action="store_true", help="skip X6 attribution")
    tx.add_argument(
        "--flag",
        action="append",
        help="A25 P3: the protected-flag configuration chosen on validation",
    )
    tx.add_argument(
        "--noart", action="store_true", help="A25 P1: the artefact-free track (its own opening)"
    )
    tx.add_argument(
        "--plus",
        action="store_true",
        help="A25 P6 adequacy: the stronger-detector track S0+, S2+, oracle+ (its own opening)",
    )
    tx.add_argument(
        "--allow-repeat",
        action="store_true",
        help="rerun a seed that crashed after opening (logged)",
    )
    tx.set_defaults(func=cmd_test_x1)

    tb = sub.add_parser("test-baselines", help="week 18: G1 baselines and ablation on test")
    tb.add_argument("--dataset", required=True)
    tb.add_argument("--option", default="B8")
    tb.add_argument("--reps", type=int, default=1000)
    tb.add_argument("--allow-repeat", action="store_true")
    tb.set_defaults(func=cmd_test_baselines)

    t5 = sub.add_parser("test-x5", help="week 18: X5 saved models (H2a, H2b) on test")
    t5.add_argument("--dataset", required=True)
    t5.add_argument("--option", default="B8")
    t5.add_argument("--reps", type=int, default=1000)
    t5.add_argument("--allow-repeat", action="store_true")
    t5.set_defaults(func=cmd_test_x5)

    te = sub.add_parser("test-ensemble", help="week 18: stacked ensemble on test")
    te.add_argument("--dataset", required=True)
    te.add_argument("--option", default="B8")
    te.add_argument("--reps", type=int, default=1000)
    te.add_argument("--allow-repeat", action="store_true")
    te.set_defaults(func=cmd_test_ensemble)

    tr = sub.add_parser("test-report", help="week 18: the hypothesis verdicts on test")
    tr.add_argument("--fixture", action="store_true", help="include FIXTURE-Small artifacts")
    tr.set_defaults(func=cmd_test_report)

    sl = sub.add_parser("sealed-log", help="show every opening of the sealed test")
    add_dataset(sl)
    sl.set_defaults(func=cmd_sealed_log)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
