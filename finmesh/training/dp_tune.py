"""DP hyperparameters chosen on a proxy federation (amendments A18, A19).

Week 10 showed DP-SGD with the a-priori clip norm (1) and batch (512) far
below the non-private network: only about 3% of units reached the clip norm,
so the noise, which scales with it, swamped a gradient carried by a few
positives per batch. The fix is the usual one (clip near the typical
gradient norm, larger batches), but choosing it on a bank's own data would
spend privacy the accountant does not see.

So the grid below is run on the **Small** federation of the same regime
(HI-Small for HI-Medium, LI-Small for LI-Medium): separate AMLworld data,
treated as public proxy data. Each setting trains FedAvg with DP-SGD at
ε = 3 (window unit, seed 0) and is scored by AUPRC on that federation's own
training hold-out (the last 20% of training windows). The best setting is
written to ``finmesh/schemas/dp_hparams.json`` and used unchanged for every DP
run on the Medium set of the regime. Validation is never touched.

Two grids exist. **A18** (week 11): clip × batch at a fixed *example* budget
(20 × 512 / batch local steps). It picked its own corner (clip 1, batch 512):
accuracy still rose at the largest clip, and batch 8,192 got only 50 updates.
**A19** (week 12, the one retune): clip ∈ {1, 3, 10} × batch ∈ {512, 2048} ×
lr ∈ {1e-3, 3e-3, 1e-2}, every setting with the same 1,000 updates, so batch
is compared at equal training length. A non-private FedAvg on the same
hold-out puts the numbers in context.
"""

from __future__ import annotations

import itertools
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore
from finmesh.features.build import FeatureStore
from finmesh.federation.fedavg import fedavg
from finmesh.models.neural import Encoder, init_params, scores
from finmesh.paths import DatasetPaths
from finmesh.reporting import fmt, table
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import feature_sets
from finmesh.training.data import training_rows, training_windows
from finmesh.training.neural import DpHparams, client_data, steps_for, train_private

GRID_CLIP: tuple[float, ...] = (0.01, 0.03, 0.1, 0.3, 1.0)  # A18
GRID_BATCH: tuple[int, ...] = (512, 2048, 8192)  # A18
TUNE_LR = 1e-3  # A18
A19_CLIP: tuple[float, ...] = (1.0, 3.0, 10.0)
A19_BATCH: tuple[int, ...] = (512, 2048)
A19_LR: tuple[float, ...] = (1e-3, 3e-3, 1e-2)
A19_LOCAL_STEPS = 20
GRIDS: tuple[str, ...] = ("A18", "A19")
TUNE_EPSILON = 3.0
TUNE_SEED = 0
PROXY_DATASETS: tuple[str, ...] = ("HI-Small", "LI-Small")
Setting = tuple[float, int, float, int]  # clip, expected batch, lr, local steps per round


def grid_settings(name: str) -> list[Setting]:
    if name == "A18":
        return [(c, b, TUNE_LR, steps_for(b)) for c, b in itertools.product(GRID_CLIP, GRID_BATCH)]
    if name == "A19":
        return [
            (c, b, lr, A19_LOCAL_STEPS)
            for c, b, lr in itertools.product(A19_CLIP, A19_BATCH, A19_LR)
        ]
    raise ValueError(f"unknown grid {name!r}; known: {', '.join(GRIDS)}")


def choose(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Best hold-out AUPRC; ties to the cheaper setting (smaller batch, then clip, then lr)."""
    ok = [r for r in rows if not np.isnan(r["holdout_auprc"])]
    if not ok:
        return None
    return max(ok, key=lambda r: (r["holdout_auprc"], -r["batch"], -r["clip"], -r["lr"]))


def run_tuning(
    paths: DatasetPaths,
    out_root: Path,
    option: str = "B8",
    rounds: int = 50,
    local_steps: int | None = None,
    grid: list[Setting] | None = None,
    progress: Callable[[str], None] | None = None,
    grid_name: str = "A19",
) -> dict[str, Any]:
    t_start = time.perf_counter()
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    windows = training_windows(store, feats)
    cols = feature_sets()["all"]
    members = sorted(store.accounts_per_member()["member"].to_list())
    enc = Encoder(cols)
    fit, hold = training_rows(store, feats, cols, windows, TUNE_SEED)
    clients = {m: client_data(fit, m) for m in members if (fit.member == m).any()}
    x_hold = enc(hold.x)
    init = init_params(enc.width, TUNE_SEED)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rows = []
    settings = grid if grid is not None else grid_settings(grid_name)
    reference: dict[str, Any] = {}
    with AnonPeak() as anon:
        t0 = time.perf_counter()  # non-private FedAvg on the same rows: context only
        ref_steps = A19_LOCAL_STEPS if local_steps is None else local_steps
        ref_params, _ = fedavg(clients, enc, init, TUNE_SEED, rounds, ref_steps)
        ref_s = scores(ref_params, x_hold)
        reference = {
            "holdout_auprc": RankedScores(hold.y, ref_s).stats()[0]
            if hold.y.sum()
            else float("nan"),
            "local_steps": ref_steps,
            "seconds": round(time.perf_counter() - t0, 1),
        }
        for clip, batch, lr, own_steps in settings:
            t0 = time.perf_counter()
            steps = own_steps if local_steps is None else local_steps
            hp = DpHparams(clip, batch, lr, f"dp-tune {paths.name} ({grid_name})", steps)
            params, report = train_private(
                clients,
                enc,
                init,
                TUNE_SEED,
                TUNE_EPSILON,
                hp,
                out_root / "accountants" / paths.name / run_id / f"c{clip:g}_b{batch}",
                rounds,
                steps,
            )
            s = scores(params, x_hold)
            ap = RankedScores(hold.y, s).stats()[0] if hold.y.sum() else float("nan")
            clipped = float(np.mean(list(report["clipped_share"].values())))
            noise = float(np.mean([c["noise"] for c in report["clients"].values()]))
            rows.append(
                {
                    "clip": clip,
                    "batch": batch,
                    "lr": lr,
                    "local_steps": steps,
                    "holdout_auprc": ap,
                    "clipped_share": clipped,
                    "noise_multiplier": noise,
                    "seconds": round(time.perf_counter() - t0, 1),
                }
            )
            if progress:
                progress(
                    f"clip {clip:g} batch {batch} lr {lr:g}: hold-out AUPRC {ap:.4f}, "
                    f"{clipped:.0%} clipped"
                )
    best = choose(rows)
    edge = None
    if best is not None and grid is None and grid_name == "A19":
        edge = {
            "clip": best["clip"] == max(A19_CLIP),
            "batch": best["batch"] == max(A19_BATCH),
            "lr": best["lr"] in (min(A19_LR), max(A19_LR)),
        }
    return {
        "dataset": paths.name,
        "grid_name": grid_name,
        "run_id": run_id,
        "epsilon": TUNE_EPSILON,
        "non_private": reference,
        "on_edge": edge,
        "rounds": rounds,
        "local_steps": local_steps,
        "holdout_rows": len(hold.y),
        "holdout_positives": int(hold.y.sum()),
        "grid": rows,
        "best": best,
        "seconds": round(time.perf_counter() - t_start, 1),
        "peak_anon_mb": anon.mb,
    }


def render_tuning(r: dict[str, Any]) -> str:
    best = r["best"]
    name = r.get("grid_name", "A18")
    budget = (
        "local steps per round = 20 × 512 / batch, so every setting sees the same number of "
        "examples"
        if name == "A18"
        else "20 local steps per round for every setting, so every setting takes the same "
        "1,000 updates and a larger batch costs more compute"
    )
    ref = r.get("non_private") or {}
    edge = r.get("on_edge") or {}
    edges = [k for k, v in edge.items() if v]
    return "\n".join(
        [
            f"# DP hyperparameters on the proxy federation · {r['dataset']} · {name}",
            "",
            f"Amendment {name}: FedAvg with DP-SGD at ε = "
            f"{r['epsilon']:g} (window unit, seed 0, {r['rounds']} rounds; {budget}) for every "
            "setting in the grid, scored by AUPRC on "
            "this federation's training hold-out "
            f"({r['holdout_rows']:,} rows, {r['holdout_positives']:,} positives). The best "
            "setting is written to `finmesh/schemas/dp_hparams.json` and used unchanged on the "
            "Medium set of the same regime; no Medium data is used here. "
            f"Total {r['seconds']:,.0f} s, peak memory {r['peak_anon_mb']:,.0f} MB.",
            "",
            table(
                r["grid"],
                [
                    ("clip", "Clip norm"),
                    ("batch", "Expected batch"),
                    ("lr", "Learning rate"),
                    ("local_steps", "Local steps per round"),
                    ("holdout_auprc", "Hold-out AUPRC"),
                    ("clipped_share", "Share clipped"),
                    ("noise_multiplier", "Noise multiplier"),
                    ("seconds", "Seconds"),
                ],
            ),
            "",
            (
                f"**Chosen:** clip {best['clip']:g}, expected batch {best['batch']}, learning "
                f"rate {best.get('lr', 1e-3):g}, {best['local_steps']} local steps per round, "
                f"hold-out AUPRC {fmt(best['holdout_auprc'])}."
                if best
                else "No setting could be scored (no positives in the hold-out)."
            ),
            "",
            (
                f"Non-private FedAvg on the same hold-out: AUPRC {fmt(ref.get('holdout_auprc'))}"
                + (
                    "; the chosen DP setting reaches "
                    f"{fmt(best['holdout_auprc'] / ref['holdout_auprc'])} of it."
                    if best and ref.get("holdout_auprc")
                    else "."
                )
                if ref
                else ""
            ),
            "",
            (
                f"The choice lies on the grid's edge in: {', '.join(edges)}. A19 allows one "
                "retune only, so the edge is reported, not extended."
                if edges
                else ""
            ),
            "",
        ]
    )


__all__ = [
    "GRIDS",
    "GRID_BATCH",
    "GRID_CLIP",
    "PROXY_DATASETS",
    "choose",
    "grid_settings",
    "render_tuning",
    "run_tuning",
]
