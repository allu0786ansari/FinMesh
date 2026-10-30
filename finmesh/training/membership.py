"""Attack A5 on the federated model (week 12; amendment A19).

Can a peer bank tell whether an account at another bank was in that bank's
training data, from the global model it receives?

* **Members and non-members.** Each member's training accounts (the GBDT's
  training rows, seed 0, reduced to account-unit bags of at most 8 windows)
  are split 50/50 by a fixed hash into IN and OUT. The target models train on
  IN only, so OUT accounts are drawn from exactly the same population.
* **Target models** (deployed setup: account unit, degree-capped features):
  FedAvg + DP-SGD at ε ∈ {1, 3, 10} with the frozen DP settings, and
  non-private FedAvg as the positive control.
* **Attacker** (worst case, as in DP auditing): a peer bank that holds the
  final global model and the candidate account's rows and labels.
  * LOSS: score = −(mean weighted loss of the account's bag under the model).
  * REF: score = loss under the attacker's own non-private local MLP (trained
    on its own accounts only) − loss under the global model, which removes
    how hard the account is in general. Each candidate at member m is
    attacked by the next member, m + 1 (mod members).
* **Metrics:** AUC and TPR at 1% and 0.1% FPR (threshold set on OUT), with a
  Poisson bootstrap over accounts; all accounts and laundering accounts (a
  positive row in the bag).
* **Audit check:** for an (ε, δ)-DP model at the account unit, any attack has
  TPR ≤ e^ε · FPR + δ. A lower 95% bound of the TPR at 1% FPR above
  e^ε × 0.01 + δ would mean the implementation leaks more than it claims (G3
  blocks). The Clopper–Pearson empirical ε lower bound is reported alongside.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from scipy.stats import beta

from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore
from finmesh.features.build import FeatureStore
from finmesh.features.variants import DEFAULT_DEGREE_CAP
from finmesh.federation.dpsgd import Adam, local_training
from finmesh.federation.fedavg import LOCAL_STEPS, ROUNDS, fedavg
from finmesh.models.neural import Encoder, init_params, logits
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import feature_sets
from finmesh.training.data import Rows, training_rows, training_windows
from finmesh.training.neural import (
    BAG_CAP,
    POS_WEIGHT,
    _bag_keep,
    client_data,
    dp_hparams,
    train_private,
)
from finmesh.training.x4 import ledger_append

MIA_EPSILONS: tuple[float, ...] = (1.0, 3.0, 10.0)
FPRS: tuple[float, ...] = (0.01, 0.001)
IN_SALT = 0x5A41
MIA_SEED = 0
NONPRIVATE = "fedavg[account,capped]"


def model_name(eps: float | None) -> str:
    return NONPRIVATE if eps is None else f"dp[account,capped,eps={eps:g}]"


def bag_rows(fit: Rows) -> Rows:
    """The rows the account unit trains on: at most BAG_CAP windows per account and member."""
    assert fit.account is not None and fit.window is not None
    keep = np.zeros(len(fit.y), dtype=bool)
    for m in np.unique(fit.member):
        idx = np.nonzero(fit.member == m)[0]
        keep[idx] = _bag_keep(fit.account[idx], fit.window[idx], BAG_CAP)
    return _subset(fit, keep)


def _subset(rows: Rows, mask: np.ndarray) -> Rows:
    return dataclasses.replace(
        rows,
        x=rows.x[mask],
        y=rows.y[mask],
        w=rows.w[mask],
        member=rows.member[mask],
        account=None if rows.account is None else rows.account[mask],
        window=None if rows.window is None else rows.window[mask],
    )


def in_mask(account: np.ndarray, member: np.ndarray) -> np.ndarray:
    """IN (True) or OUT for each row's account, 50/50 by a fixed hash of (account, member)."""
    h = pl.DataFrame({"a": account, "m": member}).select(pl.struct("a", "m").hash(seed=IN_SALT))
    return np.asarray(h.to_series().to_numpy() % 2 == 0)


def row_loss(params: list[np.ndarray], enc: Encoder, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Weighted cross-entropy per row, the training loss (weight 10 on positives)."""
    out = np.empty(len(y))
    for start in range(0, len(y), 200_000):
        sl = slice(start, start + 200_000)
        z = np.clip(logits(params, enc(x[sl])), -40, 40)
        yy = y[sl].astype(np.float64)
        out[sl] = np.where(yy == 1, POS_WEIGHT, 1.0) * (np.logaddexp(0.0, z) - yy * z)
    return out


def _tpr_sorted(
    srt: np.ndarray, ww: np.ndarray, s_in: np.ndarray, w_in: np.ndarray, fpr: float
) -> tuple[float, float, float]:
    total = ww.sum()
    if total <= 0 or w_in.sum() <= 0:
        return float("nan"), float("nan"), float("nan")
    cum = np.cumsum(ww) / total
    k = int(np.searchsorted(cum, fpr, side="right"))  # rows whose cumulative share stays <= fpr
    thr = srt[k] if k < len(srt) else -np.inf
    # ties at the threshold count as not flagged, so the achieved FPR never exceeds fpr
    achieved = float(ww[srt > thr].sum()) / float(total)
    return float(w_in[s_in > thr].sum()) / float(w_in.sum()), achieved, float(thr)


def tpr_at(
    s_in: np.ndarray, w_in: np.ndarray, s_out: np.ndarray, w_out: np.ndarray, fpr: float
) -> tuple[float, float, float]:
    """(TPR, achieved FPR, threshold): flag scores strictly above a threshold set on OUT."""
    order = np.argsort(-s_out, kind="mergesort")
    return _tpr_sorted(s_out[order], w_out[order], s_in, w_in, fpr)


def empirical_epsilon(tp: int, n_in: int, fp: int, n_out: int, delta: float) -> float:
    """Clopper–Pearson 95% lower bound on ε implied by one threshold (0 if none)."""
    if n_in == 0 or n_out == 0:
        return float("nan")
    tpr_low = float(beta.ppf(0.025, tp, n_in - tp + 1)) if tp > 0 else 0.0
    fpr_high = float(beta.ppf(0.975, fp + 1, n_out - fp)) if fp < n_out else 1.0
    if tpr_low - delta <= 0 or fpr_high <= 0:
        return 0.0
    return max(0.0, float(np.log((tpr_low - delta) / fpr_high)))


def attack_metrics(
    score: np.ndarray, is_in: np.ndarray, reps: int, seed: int, delta: float
) -> dict[str, Any]:
    s_in, s_out = score[is_in], score[~is_in]
    out: dict[str, Any] = {"n_in": len(s_in), "n_out": len(s_out)}
    if len(s_in) < 10 or len(s_out) < 10:
        return out
    ranked = RankedScores(is_in.astype(np.int8), score)
    out["auc"] = ranked.stats()[1]
    order = np.argsort(-s_out, kind="mergesort")
    srt = s_out[order]
    point = {
        fpr: _tpr_sorted(srt, np.ones(len(srt)), s_in, np.ones(len(s_in)), fpr) for fpr in FPRS
    }
    rng = np.random.default_rng(seed)
    auc_draws: list[float] = []
    tpr_draws: dict[float, list[float]] = {fpr: [] for fpr in FPRS}
    for _ in range(reps):  # Poisson weights per account, the same draw for every statistic
        w = rng.poisson(1.0, size=len(score)).astype(np.float64)
        auc_draws.append(ranked.stats(w)[1])
        w_in, w_out = w[is_in], w[~is_in][order]
        for fpr in FPRS:
            tpr_draws[fpr].append(_tpr_sorted(srt, w_out, s_in, w_in, fpr)[0])
    out["auc_ci"] = _ci(auc_draws, out["auc"])
    for fpr in FPRS:
        tpr, achieved, thr = point[fpr]
        tp, fp = int((s_in > thr).sum()), int((s_out > thr).sum())
        out[f"tpr@{fpr:g}"] = {
            **_ci(tpr_draws[fpr], tpr),
            "achieved_fpr": achieved,
            "dp_free_bound": fpr,  # a useless attack: TPR = FPR
            "epsilon_lower_bound": empirical_epsilon(tp, len(s_in), fp, len(s_out), delta),
        }
    return out


def _ci(draws: list[float], estimate: float) -> dict[str, float]:
    d = np.asarray([v for v in draws if not np.isnan(v)])
    if not len(d):
        return {"estimate": estimate, "low": float("nan"), "high": float("nan")}
    return {
        "estimate": float(estimate),
        "low": float(np.quantile(d, 0.025)),
        "high": float(np.quantile(d, 0.975)),
    }


def per_account(values: np.ndarray, account_index: np.ndarray, n: int) -> np.ndarray:
    counts = np.bincount(account_index, minlength=n)
    return np.bincount(account_index, weights=values, minlength=n) / np.maximum(counts, 1)


def run_membership(
    paths: DatasetPaths,
    out_root: Path,
    option: str = "B8",
    cap: int = DEFAULT_DEGREE_CAP,
    reps: int = 200,
    rounds: int = ROUNDS,
    local_steps: int = LOCAL_STEPS,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    t_start = time.perf_counter()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / "accountants" / paths.name / f"mia_{run_id}"
    seed = MIA_SEED
    store = EvalStore(paths, option)
    view = f"cap{cap}"
    feats = FeatureStore(paths, option, view)
    cols = feature_sets()["all"]
    enc = Encoder(cols)
    members = sorted(store.accounts_per_member()["member"].to_list())
    hp = dp_hparams(paths.name)
    own_steps = None if hp.source != "A17 defaults" else local_steps
    seconds: dict[str, float] = {}

    def tick(name: str, t0: float) -> None:
        seconds[name] = round(time.perf_counter() - t0, 1)
        if progress:
            progress(f"{name}: {seconds[name]:.0f} s")

    with AnonPeak() as anon:
        t0 = time.perf_counter()
        fit, _ = training_rows(store, feats, cols, training_windows(store, feats), seed)
        bags = bag_rows(fit)
        del fit
        assert bags.account is not None
        inside = in_mask(bags.account, bags.member)
        rows_in = _subset(bags, inside)
        present = [m for m in members if (rows_in.member == m).any()]
        clients = {m: client_data(rows_in, m, "account") for m in present}
        init = init_params(enc.width, seed)
        tick("data", t0)

        models: dict[str, list[np.ndarray]] = {}
        privacy: dict[str, Any] = {}
        t0 = time.perf_counter()
        models[model_name(None)] = fedavg(clients, enc, init, seed, rounds, local_steps)[0]
        tick(model_name(None), t0)
        for eps in MIA_EPSILONS:
            t0 = time.perf_counter()
            name = model_name(eps)
            models[name], privacy[name] = train_private(
                clients,
                enc,
                init,
                seed,
                eps,
                hp,
                run_dir / f"eps{eps:g}",
                rounds,
                own_steps,
                "account",
            )
            tick(name, t0)
        del clients, rows_in

        # The attacker's reference: its own non-private local MLP on its own accounts (IN + OUT).
        t0 = time.perf_counter()
        steps = rounds * local_steps
        refs = {
            m: local_training(
                init,
                client_data(bags, m, "account"),
                enc,
                steps,
                np.random.default_rng([seed, 31, m]),
                Adam(),
            )[0]
            for m in present
        }
        attacker = {m: present[(i + 1) % len(present)] for i, m in enumerate(present)}
        tick("references", t0)

        # Score every candidate account (its bag) under each model and its attacker's reference.
        t0 = time.perf_counter()
        keys = np.stack([bags.account.astype(np.uint64), bags.member.astype(np.uint64)], axis=1)
        uniq, acc_idx = np.unique(keys, axis=0, return_inverse=True)
        acc_idx = np.ravel(acc_idx)
        n_acc = len(uniq)
        acc_member = uniq[:, 1].astype(np.int64)
        acc_in = np.zeros(n_acc, dtype=bool)
        acc_in[acc_idx] = inside
        acc_pos = np.bincount(acc_idx, weights=bags.y.astype(np.float64), minlength=n_acc) > 0
        ref_loss = np.empty(len(bags.y))
        for m in present:
            sel = bags.member == m
            ref_loss[sel] = row_loss(refs[attacker[m]], enc, bags.x[sel], bags.y[sel])
        ref_acc = per_account(ref_loss, acc_idx, n_acc)
        target_acc = {
            name: per_account(row_loss(p, enc, bags.x, bags.y), acc_idx, n_acc)
            for name, p in models.items()
        }
        keep = np.isin(acc_member, present)
        tick("scoring", t0)

        t0 = time.perf_counter()
        results: dict[str, Any] = {}
        for name, loss in target_acc.items():
            delta = (
                max(c["delta"] for c in privacy[name]["clients"].values())
                if name in privacy
                else 0.0
            )
            target_eps = None if name not in privacy else float(name.split("eps=")[1].rstrip("]"))
            attacks = {"LOSS": -loss, "REF": ref_acc - loss}
            res: dict[str, Any] = {"epsilon": target_eps, "delta": delta, "attacks": {}}
            for attack, score in attacks.items():
                res["attacks"][attack] = {
                    group: attack_metrics(score[keep & sel], acc_in[keep & sel], reps, 0, delta)
                    for group, sel in (("all", np.ones(n_acc, bool)), ("laundering", acc_pos))
                }
            if target_eps is not None:
                bound = float(np.exp(target_eps) * 0.01 + delta)
                lows = [
                    res["attacks"][a]["all"].get("tpr@0.01", {}).get("low", float("nan"))
                    for a in attacks
                ]
                res["dp_bound_at_1pct"] = bound
                res["audit_violation"] = bool(any(lo > bound for lo in lows if not np.isnan(lo)))
            results[name] = res
        tick("metrics", t0)

    ledger_append(
        out_root / f"privacy_ledger_{paths.name}.jsonl",
        paths.name,
        f"mia_{run_id}",
        [{"seed": seed, "privacy": privacy}],
    )
    return {
        "dataset": paths.name,
        "run_id": run_id,
        "seed": seed,
        "cap": cap,
        "hparams": hp.to_dict(),
        "rounds": rounds,
        "local_steps": local_steps,
        "accounts": {
            "in": int((acc_in & keep).sum()),
            "out": int((~acc_in & keep).sum()),
            "laundering_in": int((acc_in & acc_pos & keep).sum()),
            "laundering_out": int((~acc_in & acc_pos & keep).sum()),
        },
        "results": results,
        "privacy": privacy,
        "audit_violation": any(r.get("audit_violation", False) for r in results.values()),
        "seconds": {**seconds, "total": round(time.perf_counter() - t_start, 1)},
        "peak_anon_mb": anon.mb,
    }


__all__ = [
    "FPRS",
    "MIA_EPSILONS",
    "attack_metrics",
    "bag_rows",
    "empirical_epsilon",
    "in_mask",
    "model_name",
    "run_membership",
    "tpr_at",
]
