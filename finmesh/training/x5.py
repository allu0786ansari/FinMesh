"""Experiment X5 (week 11; amendment A18): privacy unit and degree cap, with tuned DP.

Per seed, on the training rows of section 6 and the DP settings frozen by
``finmesh dp-tune`` on the proxy federation (``finmesh/schemas/dp_hparams.json``):

* non-private references on the member-view features: centralised, local-only
  and FedAvg MLPs (A17 settings), and the centralised MLP on the degree-capped
  features (the cap's own utility cost);
* FedAvg + DP-SGD for each privacy unit (window; account = a bag of at most 8
  windows) × features (member view; degree-capped) × ε ∈ {1, 3, 10}.

Validation AUPRC pooled over the federation's account-windows, averaged over
seeds 0–2, with a Poisson bootstrap over accounts shared by every
configuration (so every comparison is paired).

* **H2a** (tuned): window unit, member view, ε ≤ 10, at least 0.70 of the
  centralised MLP and above the local-only MLP.
* **H2b**: at the same ε, the account unit loses measurably more AUPRC than
  the window unit (member view): the paired difference window − account has
  a 95% CI above 0.
* **Cap cost**: account unit, capped − uncapped, at each ε.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore
from finmesh.eval.stats import interval_from
from finmesh.features.build import FeatureStore
from finmesh.features.variants import DEFAULT_DEGREE_CAP
from finmesh.federation.dpsgd import BATCH, Adam, local_training
from finmesh.federation.fedavg import LOCAL_STEPS, ROUNDS, fedavg
from finmesh.models.gbdt import matrix
from finmesh.models.neural import Encoder, init_params, scores
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import feature_sets
from finmesh.training.data import slices, training_rows, training_windows
from finmesh.training.neural import UNITS, client_data, dp_hparams, train_private
from finmesh.training.x4 import H2A_SHARE, SCORE_CHUNK, ledger_append

X5_EPSILONS: tuple[float, ...] = (1.0, 3.0, 10.0)
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2)
Model = Callable[[int], list[np.ndarray]]


def dp_name(unit: str, view: str, eps: float) -> str:
    return f"dp[{unit},{view},eps={eps:g}]"


def _const(params: list[np.ndarray]) -> Model:
    def get(_member: int) -> list[np.ndarray]:
        return params

    return get


def _per_member_model(params: dict[int, list[np.ndarray]], fallback: list[np.ndarray]) -> Model:
    def get(member: int) -> list[np.ndarray]:
        return params.get(member, fallback)

    return get


def _score_view(
    store: EvalStore,
    feats: FeatureStore,
    cols: tuple[str, ...],
    enc: Encoder,
    models: dict[str, Model],
) -> tuple[dict[str, np.ndarray], tuple[np.ndarray, ...]]:
    parts: dict[str, list[np.ndarray]] = {n: [] for n in models}
    keys: list[tuple[np.ndarray, ...]] = []
    for lab, feat in slices(store, feats, "val"):
        keys.append(
            (
                lab["label"].to_numpy().astype(np.int8),
                ~lab["masked"].to_numpy(),
                lab["account"].to_numpy(),
                lab["member"].to_numpy(),
            )
        )
        x = matrix(feat, cols)
        mem = feat["member"].to_numpy()
        out = {n: np.zeros(len(x)) for n in models}
        for m in np.unique(mem):
            idx = np.nonzero(mem == m)[0]
            for start in range(0, len(idx), SCORE_CHUNK):
                part = idx[start : start + SCORE_CHUNK]
                e = enc(x[part])
                for n, get in models.items():
                    out[n][part] = scores(get(int(m)), e)
        for n in models:
            parts[n].append(out[n])
    joined = tuple(np.concatenate(c) for c in zip(*keys, strict=True))
    return {n: np.concatenate(v) for n, v in parts.items()}, joined


def run_seed(
    paths: DatasetPaths,
    option: str,
    seed: int,
    run_dir: Path,
    reps: int,
    cap: int,
    rounds: int,
    local_steps: int,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    t_start = time.perf_counter()
    store = EvalStore(paths, option)
    cols = feature_sets()["all"]
    enc = Encoder(cols)
    members = sorted(store.accounts_per_member()["member"].to_list())
    hp = dp_hparams(paths.name)
    views = {
        "member": FeatureStore(paths, option, "member"),
        f"cap{cap}": FeatureStore(paths, option, f"cap{cap}"),
    }
    windows = training_windows(store, views["member"])
    init = init_params(enc.width, seed)
    steps = rounds * local_steps
    seconds: dict[str, float] = {}
    privacy: dict[str, Any] = {}
    all_scores: dict[str, np.ndarray] = {}
    keys: tuple[np.ndarray, ...] | None = None

    def tick(name: str, t0: float) -> None:
        seconds[name] = round(time.perf_counter() - t0, 1)
        if progress:
            progress(f"seed {seed} {name}: {seconds[name]:.0f} s")

    for view, feats in views.items():
        fit, _ = training_rows(store, feats, cols, windows, seed)
        models: dict[str, Model] = {}
        window_clients = {
            m: client_data(fit, m, "window") for m in members if (fit.member == m).any()
        }
        t0 = time.perf_counter()
        central, _ = local_training(
            init,
            client_data(fit, None, "window"),
            enc,
            steps,
            np.random.default_rng([seed, 99]),
            Adam(),
            None,
            batch=BATCH * len(window_clients),
        )
        models["centralised" if view == "member" else f"centralised[{view}]"] = _const(central)
        tick(f"centralised[{view}]", t0)
        if view == "member":
            t0 = time.perf_counter()
            local = {
                m: local_training(init, d, enc, steps, np.random.default_rng([seed, 7, m]))[0]
                for m, d in window_clients.items()
            }
            models["local"] = _per_member_model(local, init)
            tick("local", t0)
            t0 = time.perf_counter()
            models["fedavg"] = _const(
                fedavg(window_clients, enc, init, seed, rounds, local_steps)[0]
            )
            tick("fedavg", t0)
        for unit in UNITS:
            clients = (
                window_clients
                if unit == "window"
                else {m: client_data(fit, m, "account") for m in window_clients}
            )
            for eps in X5_EPSILONS:
                t0 = time.perf_counter()
                name = dp_name(unit, view, eps)
                params, report = train_private(
                    clients,
                    enc,
                    init,
                    seed,
                    eps,
                    hp,
                    run_dir
                    / f"seed{seed}"
                    / name.replace("[", "_").replace("]", "").replace(",", "_"),
                    rounds,
                    None if hp.source != "A17 defaults" else local_steps,
                    unit,
                )
                models[name] = _const(params)
                privacy[name] = report
                tick(name, t0)
        del fit, window_clients
        t0 = time.perf_counter()
        s, k = _score_view(store, feats, cols, enc, models)
        all_scores.update(s)
        keys = keys if keys is not None else k
        tick(f"score[{view}]", t0)
    assert keys is not None
    y, usable, accounts, _ = keys
    metrics: dict[str, Any] = {}
    draws: dict[str, list[float]] = {}
    for name, sc in all_scores.items():
        ranked = RankedScores(y[usable], sc[usable])
        ap, auc = ranked.stats()
        d, _ = ranked.bootstrap(accounts[usable], reps, 0)
        metrics[name] = {"auprc": ap, "auroc": auc}
        draws[name] = d.tolist()
    seconds["total"] = round(time.perf_counter() - t_start, 1)
    return {
        "seed": seed,
        "metrics": metrics,
        "draws": draws,
        "privacy": privacy,
        "seconds": seconds,
        "clients": {name: rep["units"] for name, rep in privacy.items() if name.endswith("eps=1]")},
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

    def ratio(a: str, b: str) -> dict[str, Any]:
        return interval_from(draws[a] / draws[b], point[a] / point[b]).to_dict()

    view_cap = f"cap{cap}"
    h2a, h2b, cap_cost = {}, {}, {}
    for eps in X5_EPSILONS:
        w = dp_name("window", "member", eps)
        a = dp_name("account", "member", eps)
        share = ratio(w, "centralised")
        minus_local = diff(w, "local")
        h2a[f"{eps:g}"] = {
            "share_of_centralised": share,
            "minus_local": minus_local,
            "met_on_validation": bool(
                share["estimate"] >= H2A_SHARE and minus_local["estimate"] > 0
            ),
        }
        loss = diff(w, a)
        h2b[f"{eps:g}"] = {
            "window_minus_account": loss,
            "account_share_of_window": ratio(a, w),
            "met_on_validation": bool((loss["low"] or 0) > 0),
        }
        cap_cost[f"{eps:g}"] = {
            "account_capped_minus_uncapped": diff(dp_name("account", view_cap, eps), a),
            "window_capped_minus_uncapped": diff(dp_name("window", view_cap, eps), w),
        }
    out["H2a"] = h2a
    out["H2b"] = h2b
    out["cap_cost"] = cap_cost
    out["cap_cost_nonprivate"] = diff(f"centralised[{view_cap}]", "centralised")
    return out


def run_x5(
    paths: DatasetPaths,
    out_root: Path,
    option: str = "B8",
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    reps: int = 200,
    cap: int = DEFAULT_DEGREE_CAP,
    rounds: int = ROUNDS,
    local_steps: int = LOCAL_STEPS,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / "accountants" / paths.name / run_id
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        per_seed = [
            run_seed(paths, option, s, run_dir, reps, cap, rounds, local_steps, progress)
            for s in seeds
        ]
    ledger_append(out_root / f"privacy_ledger_{paths.name}.jsonl", paths.name, run_id, per_seed)
    return {
        "dataset": paths.name,
        "run_id": run_id,
        "seeds": list(seeds),
        "cap": cap,
        "rounds": rounds,
        "local_steps": local_steps,
        "hparams": dp_hparams(paths.name).to_dict(),
        "epsilons": list(X5_EPSILONS),
        "summary": combine(per_seed, cap),
        "per_seed": [{k: v for k, v in s.items() if k != "draws"} for s in per_seed],
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
    }


__all__ = ["X5_EPSILONS", "combine", "dp_name", "run_x5"]
