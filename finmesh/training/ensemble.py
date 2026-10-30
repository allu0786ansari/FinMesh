"""Experiment X4, second part (week 12; amendment A19): the stacked ensemble.

Does the federated DP scorer add anything once a bank already has its own
detectors? Per seed, on validation:

* **Base scores:** the member's local GBDT (S0, member view), its local
  autoencoder (reconstruction error, member view, label-free sample), and the
  neural scorers saved by the X5 run of the same seed: FedAvg + DP-SGD in the
  deployed setup (account unit, capped features) at each ε, and the
  non-private FedAvg and centralised MLPs as references.
* **Stacker:** the A13 stacker (per member, standardised logistic regression,
  C = 1), cross-fitted on the two time halves of validation, so no row is
  scored by a stacker fitted on it, on logit(GBDT), log(autoencoder error) and
  logit(neural).
* **Configurations:** ``stack[gbdt]`` (the GBDT, recalibrated per member);
  ``stack[local]`` (GBDT + autoencoder: what a bank has alone);
  ``stack[local+X]`` for each neural scorer X.

Pooled validation AUPRC averaged over seeds with a paired Poisson bootstrap
over accounts. Primary comparison: ``stack[local+dp ε]`` − ``stack[local]``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore
from finmesh.eval.stats import interval_from
from finmesh.features.build import FeatureStore
from finmesh.models.autoencoder import Autoencoder
from finmesh.models.gbdt import matrix
from finmesh.models.neural import Encoder, scores
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import _per_member, feature_sets, fit_local_models
from finmesh.training.data import sample_rows, slices, training_windows
from finmesh.training.x1 import AE_SAMPLE, _halves, stacker_scores
from finmesh.training.x4 import SCORE_CHUNK
from finmesh.training.x5 import X5_EPSILONS, dp_name, load_models

EPS_CLIP = 1e-6


def neural_inputs(cap: int) -> dict[str, tuple[str, str]]:
    """Ensemble input name -> (saved X5 model, feature view it scores)."""
    view = f"cap{cap}"
    out = {f"dp{eps:g}": (dp_name("account", view, eps), view) for eps in X5_EPSILONS}
    out["fedavg"] = ("fedavg", "member")
    out["centralised"] = ("centralised", "member")
    return out


def configurations(cap: int) -> dict[str, tuple[str, ...]]:
    cfg: dict[str, tuple[str, ...]] = {
        "stack[gbdt]": ("gbdt",),
        "stack[local]": ("gbdt", "ae"),
    }
    for name in neural_inputs(cap):
        cfg[f"stack[local+{name}]"] = ("gbdt", "ae", name)
    return cfg


def _logit(p: np.ndarray) -> np.ndarray:
    q = np.clip(p, EPS_CLIP, 1 - EPS_CLIP)
    return np.asarray(np.log(q / (1 - q)))


def _ae_error(models: dict[int, Autoencoder], feat: pl.DataFrame) -> np.ndarray:
    out = np.zeros(feat.height)
    members = feat["member"].to_numpy()
    for m, ae in models.items():
        idx = members == m
        if idx.any():
            err, _ = ae.deviations(feat.filter(pl.Series(idx)))
            out[idx] = err.mean(axis=1)
    return out


def run_seed(
    paths: DatasetPaths,
    option: str,
    seed: int,
    models_file: Path,
    cap: int,
    reps: int,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    t_start = time.perf_counter()
    store = EvalStore(paths, option)
    views = {"member": FeatureStore(paths, option, "member")}
    views[f"cap{cap}"] = FeatureStore(paths, option, f"cap{cap}")
    cols = feature_sets()["all"]
    enc = Encoder(cols)
    members = sorted(store.accounts_per_member()["member"].to_list())
    windows = training_windows(store, views["member"])
    seconds: dict[str, float] = {}

    def tick(name: str, t0: float) -> None:
        seconds[name] = round(time.perf_counter() - t0, 1)
        if progress:
            progress(f"seed {seed} {name}: {seconds[name]:.0f} s")

    t0 = time.perf_counter()
    gbdt = _per_member(fit_local_models(store, views["member"], cols, windows, seed, members))
    tick("gbdt", t0)
    t0 = time.perf_counter()
    sample = sample_rows(views["member"], cols, windows, AE_SAMPLE, seed)
    encoders = {
        m: Autoencoder(cols, seed).fit(sample.filter(pl.col("member") == m))
        for m in members
        if sample.filter(pl.col("member") == m).height > 100
    }
    del sample
    tick("autoencoder", t0)

    saved = load_models(models_file)
    inputs = {k: v for k, v in neural_inputs(cap).items() if v[0] in saved}
    t0 = time.perf_counter()
    base: dict[str, list[np.ndarray]] = {"gbdt": [], "ae": [], **{k: [] for k in inputs}}
    keys: list[tuple[np.ndarray, ...]] = []
    member_slices = slices(store, views["member"], "val")
    capped_slices = slices(store, views[f"cap{cap}"], "val")
    for (lab, feat), (_, feat_cap) in zip(member_slices, capped_slices, strict=True):
        keys.append(
            (
                lab["label"].to_numpy().astype(np.int8),
                ~lab["masked"].to_numpy(),
                lab["account"].to_numpy(),
                lab["member"].to_numpy(),
                lab["window"].to_numpy(),
            )
        )
        base["gbdt"].append(np.asarray(gbdt(feat), dtype=np.float64))
        base["ae"].append(_ae_error(encoders, feat))
        raw_x = {"member": matrix(feat, cols), f"cap{cap}": matrix(feat_cap, cols)}
        part = {k: np.zeros(feat.height) for k in inputs}
        for start in range(0, feat.height, SCORE_CHUNK):  # bounded memory: encode in chunks
            sl = slice(start, start + SCORE_CHUNK)
            for view, x in raw_x.items():
                e = enc(x[sl])
                for k, (model, v) in inputs.items():
                    if v == view:
                        part[k][sl] = scores(saved[model], e)
                del e
        for k in inputs:
            base[k].append(part[k])
        del raw_x, part
    y, usable, accounts, member, window = (np.concatenate(c) for c in zip(*keys, strict=True))
    raw = {k: np.concatenate(v) for k, v in base.items()}
    del base
    tick("score", t0)

    t0 = time.perf_counter()
    features = {k: _logit(v) for k, v in raw.items() if k != "ae"}
    features["ae"] = np.log(raw["ae"] + 1e-9)
    v0, v1 = (int(x) for x in store.meta["partition_windows"]["val"])
    fold = _halves(window, v0, v1)
    stacked: dict[str, np.ndarray] = {}
    for name, inp in configurations(cap).items():
        if not all(i in features for i in inp):
            continue
        frame = pl.DataFrame(
            {"member": member, "prob": raw["gbdt"], **{i: features[i] for i in inp}}
        )
        stacked[name] = stacker_scores(frame, inp, y, usable, fold, seed)
    for k in inputs:  # each neural scorer on its own, for reference
        stacked[k] = raw[k]
    stacked["gbdt"] = raw["gbdt"]
    tick("stack", t0)

    metrics: dict[str, Any] = {}
    draws: dict[str, list[float]] = {}
    for name, sc in stacked.items():
        ranked = RankedScores(y[usable], sc[usable])
        ap, auc = ranked.stats()
        d, _ = ranked.bootstrap(accounts[usable], reps, 0)  # same weights for every name
        metrics[name] = {"auprc": ap, "auroc": auc}
        draws[name] = d.tolist()
    seconds["total"] = round(time.perf_counter() - t_start, 1)
    return {
        "seed": seed,
        "metrics": metrics,
        "draws": draws,
        "seconds": seconds,
        "autoencoders": {str(m): ae.info for m, ae in encoders.items()},
    }


def combine(per_seed: list[dict[str, Any]], cap: int) -> dict[str, Any]:
    names = list(per_seed[0]["metrics"])
    draws = {n: np.mean([np.asarray(s["draws"][n]) for s in per_seed], axis=0) for n in names}
    point = {n: float(np.mean([s["metrics"][n]["auprc"] for s in per_seed])) for n in names}
    out: dict[str, Any] = {
        n: {
            "auprc": interval_from(draws[n], point[n]).to_dict(),
            "auroc_mean": float(np.mean([s["metrics"][n]["auroc"] for s in per_seed])),
        }
        for n in names
    }

    def diff(a: str, b: str) -> dict[str, Any]:
        return interval_from(draws[a] - draws[b], point[a] - point[b]).to_dict()

    gains: dict[str, Any] = {}
    for k in neural_inputs(cap):
        name = f"stack[local+{k}]"
        if name in names:
            g = diff(name, "stack[local]")
            gains[k] = {**g, "ci_above_zero": bool((g.get("low") or 0) > 0)}
    out["gain_over_local"] = gains
    out["autoencoder_over_gbdt"] = diff("stack[local]", "stack[gbdt]")
    out["stacking_over_raw_gbdt"] = diff("stack[gbdt]", "gbdt")
    qualifying = [
        float(k[2:]) for k, v in gains.items() if k.startswith("dp") and v["ci_above_zero"]
    ]
    out["smallest_qualifying_epsilon"] = min(qualifying) if qualifying else None
    return out


def run_ensemble(
    paths: DatasetPaths,
    x5: dict[str, Any],
    option: str = "B8",
    reps: int = 200,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """``x5`` = the X5 result (week 12) whose saved models are stacked."""
    cap = int(x5["cap"])
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        per_seed = []
        for s in x5["per_seed"]:
            if not s.get("models_file"):
                raise RuntimeError("this X5 run saved no models; rerun `finmesh x5` (week 12)")
            per_seed.append(
                run_seed(paths, option, int(s["seed"]), Path(s["models_file"]), cap, reps, progress)
            )
    return {
        "dataset": paths.name,
        "x5_run": x5["run_id"],
        "seeds": [s["seed"] for s in per_seed],
        "cap": cap,
        "hparams": x5["hparams"],
        "summary": combine(per_seed, cap),
        "per_seed": [{k: v for k, v in s.items() if k != "draws"} for s in per_seed],
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
    }


__all__ = ["combine", "configurations", "neural_inputs", "run_ensemble"]
