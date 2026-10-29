"""DP hyperparameters chosen on a proxy federation (amendment A18).

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
from finmesh.models.neural import Encoder, init_params, scores
from finmesh.paths import DatasetPaths
from finmesh.reporting import fmt, table
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import feature_sets
from finmesh.training.data import training_rows, training_windows
from finmesh.training.neural import DpHparams, client_data, steps_for, train_private

GRID_CLIP: tuple[float, ...] = (0.01, 0.03, 0.1, 0.3, 1.0)
GRID_BATCH: tuple[int, ...] = (512, 2048, 8192)
TUNE_LR = 1e-3
TUNE_EPSILON = 3.0
TUNE_SEED = 0
PROXY_DATASETS: tuple[str, ...] = ("HI-Small", "LI-Small")


def run_tuning(
    paths: DatasetPaths,
    out_root: Path,
    option: str = "B8",
    rounds: int = 50,
    local_steps: int | None = None,
    grid: list[tuple[float, int]] | None = None,
    progress: Callable[[str], None] | None = None,
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
    settings = grid if grid is not None else list(itertools.product(GRID_CLIP, GRID_BATCH))
    with AnonPeak() as anon:
        for clip, batch in settings:
            t0 = time.perf_counter()
            steps = steps_for(batch) if local_steps is None else local_steps
            hp = DpHparams(clip, batch, TUNE_LR, f"dp-tune {paths.name}", steps)
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
                    "local_steps": steps,
                    "holdout_auprc": ap,
                    "clipped_share": clipped,
                    "noise_multiplier": noise,
                    "seconds": round(time.perf_counter() - t0, 1),
                }
            )
            if progress:
                progress(
                    f"clip {clip:g} batch {batch}: hold-out AUPRC {ap:.4f}, {clipped:.0%} clipped"
                )
    ok = [r for r in rows if not np.isnan(r["holdout_auprc"])]
    best = max(ok, key=lambda r: (r["holdout_auprc"], -r["clip"])) if ok else None
    return {
        "dataset": paths.name,
        "run_id": run_id,
        "epsilon": TUNE_EPSILON,
        "lr": TUNE_LR,
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
    return "\n".join(
        [
            f"# DP hyperparameters on the proxy federation · {r['dataset']}",
            "",
            "Amendment A18: FedAvg with DP-SGD at ε = "
            f"{r['epsilon']:g} (window unit, seed 0, lr {r['lr']:g}, {r['rounds']} rounds; local "
            "steps per round = 20 × 512 / batch, so every setting sees the same number of "
            "examples) for every clip norm and expected batch in the grid, scored by AUPRC on "
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
                    ("local_steps", "Local steps per round"),
                    ("holdout_auprc", "Hold-out AUPRC"),
                    ("clipped_share", "Share clipped"),
                    ("noise_multiplier", "Noise multiplier"),
                    ("seconds", "Seconds"),
                ],
            ),
            "",
            (
                f"**Chosen:** clip {best['clip']:g}, expected batch {best['batch']}, "
                f"{best['local_steps']} local steps per round, hold-out "
                f"AUPRC {fmt(best['holdout_auprc'])}."
                if best
                else "No setting could be scored (no positives in the hold-out)."
            ),
            "",
        ]
    )


__all__ = ["GRID_BATCH", "GRID_CLIP", "PROXY_DATASETS", "render_tuning", "run_tuning"]
