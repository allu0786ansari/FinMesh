"""Experiment X4, first part (week 10; amendment A17): the neural scorer on validation.

Configurations, all on the same training rows as the GBDT (training
partition after the burn-in, the held-out end excluded, masked rows out,
every positive and 10% of negatives by a fixed hash):

* ``mlp-centralised``: every member's rows in one place, non-private (the
  reference of H2a);
* ``mlp-local``: one network per member on its own rows, non-private;
* ``mlp-fedavg``: FedAvg, non-private;
* ``mlp-fedavg-dp[eps=ε]``: FedAvg with DP-SGD at the **window unit**,
  ε ∈ {1, 3, 10}, δ = 1/(10 N) for a client with N training units;
* ``gbdt-local``: the local LightGBM of S0 (reference).

Every network: the encoding and architecture of ``finmesh.models.neural``,
Adam (lr 1e-3), batch 512 per client step (expected units under DP),
50 rounds × 20 local steps (1,000 steps per client; centralised: 1,000 steps
of 512 × members rows), loss weight 10 on positives and 1 on negatives,
clip norm 1. Nothing is tuned on validation.

Validation AUPRC is pooled over the federation's account-windows (each row
scored by the model its member would use), averaged over seeds, with a
Poisson bootstrap over accounts shared by every configuration (paired).
H2a: ``mlp-fedavg-dp`` at ε ≤ 10 reaches at least 0.70 of
``mlp-centralised`` and exceeds ``mlp-local``.
"""

from __future__ import annotations

import json
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
from finmesh.federation.accountant import Accountant
from finmesh.federation.dpsgd import BATCH, Adam, ClientData, local_training
from finmesh.federation.fedavg import LOCAL_STEPS, ROUNDS, fedavg
from finmesh.models.gbdt import matrix
from finmesh.models.neural import Encoder, init_params, scores
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import _per_member, feature_sets, fit_local_models
from finmesh.training.data import Rows, slices, training_rows, training_windows

MODEL_EPSILONS: tuple[float, ...] = (1.0, 3.0, 10.0)
POS_WEIGHT = 10.0
DELTA_FACTOR = 0.1  # δ = DELTA_FACTOR / N units
H2A_SHARE = 0.70
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2)
SCORE_CHUNK = 200_000


def _client_data(fit: Rows, member: int | None) -> ClientData:
    sel = np.ones(len(fit.y), dtype=bool) if member is None else fit.member == member
    y = fit.y[sel].astype(np.float64)
    return ClientData(
        x=fit.x[sel],
        y=y,
        w=np.where(y == 1, POS_WEIGHT, 1.0),
        unit=np.arange(int(sel.sum())),  # window unit
    )


def _const(params: list[np.ndarray]) -> Callable[[int], list[np.ndarray]]:
    """The same global model for every member."""

    def get(_member: int) -> list[np.ndarray]:
        return params

    return get


def run_seed(
    paths: DatasetPaths,
    option: str,
    seed: int,
    run_dir: Path,
    reps: int,
    epsilons: tuple[float, ...] = MODEL_EPSILONS,
    rounds: int = ROUNDS,
    local_steps: int = LOCAL_STEPS,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    t_start = time.perf_counter()
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    windows = training_windows(store, feats)
    cols = feature_sets()["all"]
    members = sorted(store.accounts_per_member()["member"].to_list())
    enc = Encoder(cols)
    fit, _ = training_rows(store, feats, cols, windows, seed)
    clients = {m: _client_data(fit, m) for m in members if (fit.member == m).any()}
    init = init_params(enc.width, seed)
    steps = rounds * local_steps
    seconds: dict[str, float] = {}
    models: dict[str, Callable[[int], Any]] = {}
    privacy: dict[str, Any] = {}

    def timed(name: str, t0: float) -> None:
        seconds[name] = round(time.perf_counter() - t0, 1)
        if progress:
            progress(f"seed {seed} {name}: {seconds[name]:.0f} s")

    t0 = time.perf_counter()
    central = _client_data(fit, None)
    p_central, _ = local_training(
        init,
        central,
        enc,
        steps,
        np.random.default_rng([seed, 99]),
        Adam(),
        None,
        batch=BATCH * len(clients),
    )
    models["mlp-centralised"] = _const(p_central)
    del central
    timed("mlp-centralised", t0)

    t0 = time.perf_counter()
    local = {
        m: local_training(init, d, enc, steps, np.random.default_rng([seed, 7, m]))[0]
        for m, d in clients.items()
    }
    models["mlp-local"] = lambda m: local.get(m, init)
    timed("mlp-local", t0)

    t0 = time.perf_counter()
    p_fed, _ = fedavg(clients, enc, init, seed, rounds, local_steps)
    models["mlp-fedavg"] = _const(p_fed)
    timed("mlp-fedavg", t0)

    for eps in epsilons:
        t0 = time.perf_counter()
        name = f"mlp-fedavg-dp[eps={eps:g}]"
        dp: dict[int, dict[str, Any]] = {}
        for m, d in clients.items():
            n = d.units
            rate = min(1.0, BATCH / n)
            acc = Accountant.plan(
                run_dir / f"seed{seed}" / f"eps{eps:g}" / f"client{m}.json",
                client=m,
                target_epsilon=eps,
                delta=DELTA_FACTOR / n,
                rate=rate,
                steps=steps,
            )
            dp[m] = {"rate": rate, "noise": acc.state.noise, "accountant": acc}
        p_dp, info = fedavg(clients, enc, init, seed, rounds, local_steps, dp)
        models[name] = _const(p_dp)
        privacy[name] = {
            "unit": "window",
            "clients": {str(m): dp[m]["accountant"].report() for m in dp},
            "clipped_share": {str(k): v for k, v in info["clipped_share"].items()},
        }
        timed(name, t0)

    # Score validation once per configuration; the GBDT reference alongside.
    t0 = time.perf_counter()
    gbdt = _per_member(fit_local_models(store, feats, cols, windows, seed, members))
    del fit
    # One pass over the validation slices: encode each chunk once, score every model on it.
    names = ["gbdt-local", *models]
    parts: dict[str, list[np.ndarray]] = {cfg: [] for cfg in names}
    keys_parts: list[tuple[np.ndarray, ...]] = []
    for lab, feat in slices(store, feats, "val"):
        keys_parts.append(
            (
                lab["label"].to_numpy().astype(np.int8),
                ~lab["masked"].to_numpy(),
                lab["account"].to_numpy(),
                lab["member"].to_numpy(),
            )
        )
        parts["gbdt-local"].append(np.asarray(gbdt(feat), dtype=np.float64))
        x = matrix(feat, cols)
        mem = feat["member"].to_numpy()
        out = {cfg: np.zeros(len(x)) for cfg in models}
        for m in np.unique(mem):
            idx = np.nonzero(mem == m)[0]
            for start in range(0, len(idx), SCORE_CHUNK):
                part = idx[start : start + SCORE_CHUNK]
                e = enc(x[part])
                for cfg, params_of in models.items():
                    out[cfg][part] = scores(params_of(int(m)), e)
        for cfg in models:
            parts[cfg].append(out[cfg])
    y, usable, accounts, member = (np.concatenate(c) for c in zip(*keys_parts, strict=True))
    result_scores = {cfg: np.concatenate(parts[cfg]) for cfg in names}
    del parts
    timed("score", t0)

    metrics: dict[str, Any] = {}
    draws: dict[str, np.ndarray] = {}
    for name, s in result_scores.items():
        ranked = RankedScores(y[usable], s[usable])
        ap, auc = ranked.stats()
        ap_draws, _ = ranked.bootstrap(accounts[usable], reps, 0)  # same weights everywhere
        draws[name] = ap_draws
        per_member = {}
        for m in np.unique(member):
            sel = usable & (member == m)
            if y[sel].sum() > 0:
                per_member[str(int(m))] = RankedScores(y[sel], s[sel]).stats()[0]
        metrics[name] = {
            "auprc": ap,
            "auroc": auc,
            "auprc_member_mean": float(np.mean(list(per_member.values()))),
            "auprc_member": per_member,
        }
    seconds["total"] = round(time.perf_counter() - t_start, 1)
    return {
        "seed": seed,
        "metrics": metrics,
        "draws": {k: v.tolist() for k, v in draws.items()},
        "privacy": privacy,
        "seconds": seconds,
        "clients": {str(m): int(d.units) for m, d in clients.items()},
        "prevalence": float(y[usable].mean()),
    }


def combine(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    names = list(per_seed[0]["metrics"])
    draws = {n: np.mean([np.asarray(s["draws"][n]) for s in per_seed], axis=0) for n in names}
    out: dict[str, Any] = {}
    for n in names:
        point = float(np.mean([s["metrics"][n]["auprc"] for s in per_seed]))
        out[n] = {
            "auprc": interval_from(draws[n], point).to_dict(),
            "auroc_mean": float(np.mean([s["metrics"][n]["auroc"] for s in per_seed])),
            "auprc_member_mean": float(
                np.mean([s["metrics"][n]["auprc_member_mean"] for s in per_seed])
            ),
        }
    central = "mlp-centralised"
    h2a = {}
    for n in names:
        if not n.startswith("mlp-fedavg-dp"):
            continue
        ratio_point = out[n]["auprc"]["estimate"] / out[central]["auprc"]["estimate"]
        ratio = interval_from(draws[n] / draws[central], ratio_point).to_dict()
        diff_point = out[n]["auprc"]["estimate"] - out["mlp-local"]["auprc"]["estimate"]
        diff = interval_from(draws[n] - draws["mlp-local"], diff_point).to_dict()
        h2a[n] = {
            "share_of_centralised": ratio,
            "minus_local": diff,
            "met_on_validation": bool(ratio_point >= H2A_SHARE and diff_point > 0),
        }
    out["H2a"] = h2a
    return out


def ledger_append(path: Path, dataset: str, run_id: str, per_seed: list[dict[str, Any]]) -> None:
    """The privacy ledger: every private training ever run on this dataset, never rewritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for s in per_seed:
            for name, p in s["privacy"].items():
                for client, rep in p["clients"].items():
                    f.write(
                        json.dumps(
                            {
                                "dataset": dataset,
                                "run": run_id,
                                "seed": s["seed"],
                                "configuration": name,
                                "unit": p["unit"],
                                "client": int(client),
                                "epsilon_target": rep["target_epsilon"],
                                "epsilon_spent": rep["epsilon_spent"],
                                "delta": rep["delta"],
                                "noise_multiplier": rep["noise"],
                                "sampling_rate": rep["rate"],
                                "steps": rep["steps_done"],
                            }
                        )
                        + "\n"
                    )


def run_x4(
    paths: DatasetPaths,
    out_root: Path,
    option: str = "B8",
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    reps: int = 200,
    rounds: int = ROUNDS,
    local_steps: int = LOCAL_STEPS,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / "accountants" / paths.name / run_id
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        per_seed = [
            run_seed(
                paths,
                option,
                s,
                run_dir,
                reps,
                rounds=rounds,
                local_steps=local_steps,
                progress=progress,
            )
            for s in seeds
        ]
    ledger_append(out_root / f"privacy_ledger_{paths.name}.jsonl", paths.name, run_id, per_seed)
    summary = combine(per_seed)
    return {
        "dataset": paths.name,
        "run_id": run_id,
        "seeds": list(seeds),
        "rounds": rounds,
        "local_steps": local_steps,
        "batch": BATCH,
        "pos_weight": POS_WEIGHT,
        "epsilons": list(MODEL_EPSILONS),
        "summary": summary,
        "per_seed": [{k: v for k, v in s.items() if k != "draws"} for s in per_seed],
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
    }


__all__ = ["MODEL_EPSILONS", "combine", "run_x4"]
