"""Week 18 preflight: everything the sealed test needs, checked without opening it.

``finmesh test-preflight --dataset HI-Medium`` reports, for one dataset:

* the code: a clean working tree, and HEAD equal to the commit frozen in
  ``docs/protocol/test_plan.md`` once the owner has signed it;
* the inputs: labels, the test universe files (their presence only), the test
  partition's features in every view the runs read, the week-12 X5 artifact and its
  saved models, the narrative's model server;
* the seal: which experiments and seeds already opened the test, and which seeds have
  a saved result (a rerun continues after them);
* the machine: free disk.

Nothing here reads a test label.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from finmesh.eval.provenance import git_commit
from finmesh.eval.sealed import read_access_log
from finmesh.features.variants import DEFAULT_DEGREE_CAP
from finmesh.paths import REPO_ROOT, DatasetPaths, data_root

PLAN = REPO_ROOT / "docs" / "protocol" / "test_plan.md"
A25_PLAN = REPO_ROOT / "docs" / "protocol" / "improvement_plan_A25.md"  # the Large openings


def plan_for(paths: DatasetPaths) -> Path:
    """The signed plan that governs a dataset's test openings."""
    return A25_PLAN if "Large" in paths.name else PLAN


RUNS: tuple[str, ...] = ("x1", "baselines", "x5", "ensemble", "narrative")


def frozen_commit(plan: Path = PLAN) -> str | None:
    """The commit the owner signed last (``**Frozen commit:** <sha>``, or a later
    ``**<amendment> re-signed frozen commit:** <sha>`` field)."""
    if not plan.exists():
        return None
    found = re.findall(
        r"\*\*[^*\n]*frozen commit[^*\n]*:\*\*\s*`?([0-9a-f]{7,40})`?",
        plan.read_text(),
        flags=re.IGNORECASE,
    )
    return found[-1] if found else None  # the latest signature (a re-signed amendment)


def _clean_tree() -> bool | None:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return not out.strip()


CODE_PATHS: tuple[str, ...] = ("finmesh", "scripts", "pyproject.toml", "uv.lock")


def code_changes_since(commit: str) -> list[str] | None:
    """Code files that differ between ``commit`` and the working tree (docs may change)."""
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", commit, "--", *CODE_PATHS],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [line for line in out.splitlines() if line.strip()]


def _ollama(url: str = "http://localhost:11434") -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=3) as r:
            return bool(r.status == 200)
    except OSError:
        return False


def preflight(
    paths: DatasetPaths, option: str = "B8", only: str = ",".join(RUNS)
) -> dict[str, Any]:
    from finmesh.eval.sealed import EvalStore
    from finmesh.features.build import FeatureStore
    from finmesh.training.sealed_runs import test_dir

    runs = [r.strip() for r in only.split(",") if r.strip()]
    lines: list[str] = []
    ok = True

    def check(passed: bool | None, text: str, required: bool = True) -> None:
        nonlocal ok
        mark = "ok  " if passed else ("WARN" if not required or passed is None else "FAIL")
        if required and passed is False:
            ok = False
        lines.append(f"[{mark}] {text}")

    head = git_commit()
    plan = plan_for(paths)
    frozen = frozen_commit(plan)
    check(_clean_tree(), "working tree clean (no uncommitted change to tracked files)")
    if frozen is None:
        check(None, f"HEAD {head[:12]}; no frozen commit signed in {plan.name} yet", False)
    else:
        changed = code_changes_since(frozen)
        detail = "unknown" if changed is None else (", ".join(changed[:5]) or "none")
        check(
            changed == [],
            f"code identical to the signed frozen commit {frozen[:12]} (changed: {detail})",
        )

    try:
        store = EvalStore(paths, option)
    except FileNotFoundError as exc:
        check(False, f"labels: {exc}")
        return {"ok": False, "lines": lines}
    test_dir_labels = store.layout.partition_dir("test")
    check(
        any(test_dir_labels.glob("universe_*.parquet")), "sealed test universe present (not read)"
    )
    views = ["member", "pooled"]
    if {"x5", "ensemble"} & set(runs):
        views.append(f"cap{DEFAULT_DEGREE_CAP}")
    for view in views:
        try:
            feats = FeatureStore(paths, option, view)
            n = len(list(feats.layout.partition_dir("test").glob("feat_*.parquet")))
            check(n > 0, f"test features, {view} view: {n} slices")
        except (FileNotFoundError, RuntimeError) as exc:
            check(False, f"test features, {view} view: {exc}")

    if {"x5", "ensemble"} & set(runs):
        x5_path = data_root() / "artifacts" / "week12" / f"x5_{paths.name}.json"
        if not x5_path.exists():
            check(False, f"week-12 X5 artifact {x5_path.name} (its saved models are scored)")
        else:
            x5 = json.loads(x5_path.read_text())
            x5 = x5.get("result", x5)
            files = [s.get("models_file") for s in x5.get("per_seed", [])]
            missing = [f for f in files if not f or not Path(f).exists()]
            check(
                not missing and bool(files),
                f"X5 run {x5.get('run_id')}: {len(files)} saved model files",
            )

    log = [e for e in read_access_log(paths) if e.get("dataset") == paths.name]
    check(True, f"access log: {len(log)} opening(s) so far on {paths.name}")
    for e in log:
        lines.append(f"       {e['time']} seed {e['seed']} {e['purpose']}")
    done = sorted(p.name for p in test_dir(paths, option).glob("x1_seed*.pkl"))
    if done:
        lines.append(f"       saved X1 seeds (a rerun continues after them): {', '.join(done)}")

    if "narrative" in runs and paths.name.endswith("Medium"):
        check(_ollama(), "Ollama answers on localhost:11434 (needed for the narrative)", False)
    free = shutil.disk_usage(data_root()).free / 2**30
    check(free > 10, f"free disk {free:.0f} GB (10 GB or more advised)", False)
    return {"ok": ok, "lines": lines}


__all__ = ["A25_PLAN", "PLAN", "RUNS", "frozen_commit", "plan_for", "preflight"]
