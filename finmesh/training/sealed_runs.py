"""Week 18: the frozen configurations on the sealed test partition.

Every runner here follows the same discipline (preregistration sections 3, 6, 7 and 8):

1. **Train** exactly as on validation: the training partition only, the same seeds.
2. **Fit on validation** every calibration, threshold, fusion and attribution parameter
   (isotonic calibration per member; the stackers, the noisy-OR flag precision, the
   attributor and the FPR thresholds on all of validation). These are frozen.
3. **Score the test partition label-free**: features only, never a test label. All
   scores are fixed, and their SHA-256 digest computed, before step 4.
4. **Open the seal once** per experiment, dataset and seed through
   :func:`finmesh.eval.sealed.open_sealed_test`, which logs the opening (with the scores'
   digest) before returning any label. A second opening of the same experiment and seed
   is refused unless ``allow_repeat`` is given, and is then logged as a repeat.
5. **Evaluate** with the validation harness and statistics.

Each seed's result is saved as soon as it exists (``data/test/<dataset>/``), so a crash
loses at most the seed in progress and a rerun continues from the next one. A crash
*after* an opening needs ``allow_repeat`` to rerun that seed; the log shows it.
"""

from __future__ import annotations

import hashlib
import pickle
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import polars as pl

from finmesh.eval.guard import KEY_COLUMNS
from finmesh.eval.sealed import (
    EvalStore,
    PartitionData,
    SealedTestError,
    aligned_labels,
    open_sealed_test,
    opened_before,
    read_access_log,
)
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak

HEADLINE_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)  # S0, oracle, S2, PD (section 7)
OTHER_SEEDS: tuple[int, ...] = (0, 1, 2)
# Headline configurations of X1. The relational oracle is the H1b ceiling (A14), so it
# runs with the oracle's seeds.
X1_HEADLINE: frozenset[str] = frozenset(
    {
        "S0",
        "oracle",
        "oracle-relational",
        "S2/stacker",
        "PD[tau=2]/stacker",
        "PD[tau=3]/stacker",
        "PD[tau=4]/stacker",
    }
)
TEST_WINDOW_REPS = 1000  # section 7: 1,000 account-bootstrap replicates at test


class Opener(Protocol):
    def __call__(
        self,
        config: dict[str, Any],
        seed: int,
        purpose: str,
        extra: dict[str, Any],
        variant: str = "primary",
    ) -> PartitionData: ...


def opener_for(store: EvalStore, allow_repeat: bool = False) -> Opener:
    """The seal's only door, with this run's repeat policy."""

    def open_(
        config: dict[str, Any],
        seed: int,
        purpose: str,
        extra: dict[str, Any],
        variant: str = "primary",
    ) -> PartitionData:
        return open_sealed_test(
            store, config, seed, purpose, allow_repeat=allow_repeat, variant=variant, extra=extra
        )

    return open_


def test_dir(paths: DatasetPaths, option: str) -> Path:
    tag = paths.name if option == "B8" else f"{paths.name}_{option}"
    return paths.root / "test" / tag


def scores_digest(keys: pl.DataFrame, scores: dict[str, np.ndarray]) -> str:
    """SHA-256 over the row keys and every configuration's scores, in name order."""
    h = hashlib.sha256()
    for c in KEY_COLUMNS:
        h.update(np.ascontiguousarray(keys[c].to_numpy()).tobytes())
    for name in sorted(scores):
        h.update(name.encode())
        h.update(np.ascontiguousarray(np.asarray(scores[name], dtype=np.float64)).tobytes())
    return h.hexdigest()


def _save(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)


def _load(path: Path) -> Any:
    with path.open("rb") as f:  # our own checkpoint, written by _save on this machine
        return pickle.load(f)


def openings(paths: DatasetPaths) -> list[dict[str, Any]]:
    return read_access_log(paths)


def token_shortfall(used: dict[tuple[int, int], int], budget: int) -> dict[str, Any]:
    """What the frozen A16 budget would have refused of the legitimate test traffic."""
    rows = sorted(
        ({"bank": int(b), "epoch": int(e), "used": int(u)} for (b, e), u in used.items()),
        key=lambda r: -r["used"],
    )
    total = sum(r["used"] for r in rows)
    over = sum(max(0, r["used"] - budget) for r in rows)
    return {
        "frozen_budget": budget,
        "peak": rows[0] if rows else None,
        "bank_epochs_over": sum(r["used"] > budget for r in rows),
        "bank_epochs": len(rows),
        "share_beyond_budget": (over / total) if total else 0.0,
        "per_bank_epoch": rows,
    }


def refuse_if_opened(
    paths: DatasetPaths, config: dict[str, Any], seed: int, allow_repeat: bool
) -> None:
    """Refuse before any work when this configuration and seed already saw the test."""
    first = opened_before(paths, config, seed)
    if first is not None and not allow_repeat:
        raise SealedTestError(
            f"{config['experiment']} seed {seed} on {paths.name} already opened the test on "
            f"{first['time']} and its saved result is missing. Rerun with --allow-repeat only "
            "if that run crashed before reporting (the repeat is logged)."
        )


# --------------------------------------------------------------------------- traffic
def token_traffic(paths: DatasetPaths, option: str = "B8", seed: int = 0) -> list[dict[str, Any]]:
    """Label-free on test: candidates and OPRF token demand per bank and epoch, for
    validation and test under each calibration (end of training, as on validation; or
    fitted on validation). Reads validation labels only (for the second calibration)."""
    from finmesh.eval.split_io import load_plan
    from finmesh.features.build import FeatureStore
    from finmesh.fusion.local import link_edges
    from finmesh.matching.tokens import EPOCH_WINDOWS, token_budget
    from finmesh.sharing.evidence import load_evidence_schema
    from finmesh.sharing.simulate import counterparty_requests
    from finmesh.training.baselines import (
        _per_member,
        feature_sets,
        fit_local_models,
        score_keys,
        score_rows,
    )
    from finmesh.training.data import training_windows
    from finmesh.training.sharing_run import _calibrators, store_membership
    from finmesh.training.x1 import _alerts, _calibrate

    plan = load_plan(paths)
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    windows = training_windows(store, feats)
    cols = feature_sets()["all"]
    members = sorted(store.accounts_per_member()["member"].to_list())
    apm = store.accounts_per_member()
    lookback = int(feats.meta["neighbourhood"]["lookback_windows"])
    schema = load_evidence_schema()
    budget = token_budget(paths.name)
    fn = _per_member(fit_local_models(store, feats, cols, windows, seed, members))
    cal_train = _calibrators(score_rows(store, feats, "train", fn, windows.stop_from))
    val = score_rows(store, feats, "val", fn)
    cals = {"end of training": cal_train, "fitted on validation": _calibrators(val)}
    frames = {"val": val.select(*KEY_COLUMNS, "score"), "test": score_keys(feats, "test", fn)}
    del val
    membership = store_membership(paths, option)
    rows: list[dict[str, Any]] = []
    for part, frame in frames.items():
        v0, v1 = (int(x) for x in store.meta["partition_windows"][part])
        keys = frame.select(*KEY_COLUMNS)
        member = frame["member"].to_numpy()
        for cal_name, cal in cals.items():
            t0 = time.perf_counter()
            prob = _calibrate(frame["score"].to_numpy(), member, cal)
            alerted = _alerts(keys, prob, apm, plan.window_hours)
            keep = (prob >= schema.floor) | alerted
            cand = keys.filter(pl.Series(keep)).with_columns(pl.lit(0).alias("prob_bucket"))
            edges = link_edges(
                paths.transactions, plan, v0, v1, lookback, membership,
                touching=cand.select("account"),
            )  # fmt: skip
            req = counterparty_requests(cand, edges, lookback).select("member", "window", "cp")
            lo = pl.max_horizontal(pl.lit(v0), pl.col("window") - lookback + 1)
            demand = (
                req.with_columns(
                    pl.int_ranges(lo // EPOCH_WINDOWS, pl.col("window") // EPOCH_WINDOWS + 1).alias(
                        "epoch"
                    )
                )
                .explode("epoch", empty_as_null=False)
                .group_by("member", "epoch")
                .agg(pl.col("cp").n_unique().alias("tokens"))
                .sort("tokens", descending=True)
            )
            top = demand.row(0, named=True) if demand.height else {}
            rows.append(
                {
                    "partition": part,
                    "windows": f"{v0}-{v1}",
                    "calibration": cal_name,
                    "candidates": int(keep.sum()),
                    "alerts": int(alerted.sum()),
                    "mean_prob": float(prob.mean()),
                    "peak_tokens": int(top.get("tokens", 0)),
                    "peak_member_epoch": f"{top.get('member')}/{top.get('epoch')}",
                    "budget": budget,
                    "per_member_epoch": demand.to_dicts(),
                    "seconds": round(time.perf_counter() - t0, 1),
                }
            )
    return rows


# --------------------------------------------------------------------------- baselines
def run_baselines_test(
    paths: DatasetPaths,
    option: str = "B8",
    seed: int = 0,
    reps: int = 1000,
    window_reps: int = TEST_WINDOW_REPS,
    linked_draws: int = 20,
    allow_repeat: bool = False,
) -> dict[str, Any]:
    """The G1 baselines on test (section 8 secondary analyses): FPR operating points with
    validation thresholds, the touch label, the artefact ablation, the decomposition and
    PT4b. Seed 0, as at G1; the headline S0 and oracle seeds are X1's."""
    from finmesh.training.baselines import run_baselines

    store = EvalStore(paths, option)
    config = {"experiment": "baselines", "dataset": paths.name, "option": option}
    refuse_if_opened(paths, config, seed, allow_repeat)
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        result = run_baselines(
            paths,
            option=option,
            seed=seed,
            reps=reps,
            window_reps=window_reps,
            linked_draws=linked_draws,
            opener=opener_for(store, allow_repeat),
        )
    result["seconds"] = round(time.perf_counter() - t0, 1)
    result["peak_anon_mb"] = anon.mb
    return result


# --------------------------------------------------------------------------- X1 (+ X6)
def x1_config(paths: DatasetPaths, option: str, x6: bool) -> dict[str, Any]:
    return {"experiment": "X1+X6" if x6 else "X1", "dataset": paths.name, "option": option}


def run_x1_test_seed(
    paths: DatasetPaths,
    option: str,
    seed: int,
    opener: Opener,
    reps: int,
    window_reps: int,
    meter: AnonPeak | None = None,
    sweeps: bool = True,
    audit: bool = False,
    only: frozenset[str] | None = None,
    x6: bool = False,
    keep_tables: bool = False,
    random_reference: bool = False,
) -> dict[str, Any]:
    """One seed of X1 (and X6 on the same scores) on test. See the module docstring."""
    from finmesh.training.x1 import _evaluate, _phase, _random_reference, _train
    from finmesh.training.x6 import (
        LEVELS,
        attribute,
        attribute_frozen,
        level_entry,
        level_tables,
        load_catalogue,
    )

    t_start = time.perf_counter()
    memory: dict[str, float | None] = {}

    def lap(phase: str) -> None:
        if meter is not None:
            memory[phase] = meter.lap()

    t, seconds = _train(paths, option, seed, audit, lap)
    # Validation: the frozen run, plus everything fitted on all of it for the test.
    val = _phase(paths, option, seed, t, "val", seconds, lap, sweeps, False, only, fit_fusion=True)
    fusion = val.fitted
    assert fusion is not None
    levels6 = tuple(LEVELS) if x6 else ()
    catalogue = load_catalogue() if x6 else {}
    val_tables: dict[str, Any] = {}
    narrative_val: dict[str, Any] = {}
    if x6:
        t0 = time.perf_counter()
        val_scores = {LEVELS[lv]: val.score_of(LEVELS[lv]) for lv in levels6}
        val_tables = level_tables(
            paths, option, seed, val.keys, val_scores, t.store.partition("val"), levels6
        )
        if keep_tables:  # the narrative's tau and frequency baseline come from validation
            for lv in ("S0", "S2"):
                proba: dict[str, Any] = {}
                attribute(val_tables[lv][0], lv, seed, catalogue, proba)
                narrative_val[lv] = {"table": val_tables[lv][0], **proba}
        seconds["val:x6_tables"] = round(time.perf_counter() - t0, 1)
    val_protocol = val.protocol
    del val
    lap("val:done")

    # Test: label-free scores, fixed before the opening.
    test = _phase(paths, option, seed, t, "test", seconds, lap, sweeps, audit, only, fusion=fusion)
    names = test.names(only)
    from finmesh.matching.tokens import token_budget

    tokens_used = token_shortfall(dict(test.tokens.service.used), token_budget(paths.name))
    scores = {n: test.score_of(n) for n in names}
    digest = scores_digest(test.keys, scores)
    config = x1_config(paths, option, x6)
    part = opener(
        config,
        seed,
        "week 18: X1 sharing ladder" + (" and X6 attribution" if x6 else ""),
        {"scores_sha256": digest, "configurations": names, "x6_levels": list(levels6)},
    )
    label, usable = aligned_labels(part, test.keys)

    audit_result = None
    if test.auditor is not None:
        t0 = time.perf_counter()
        assert test.candidates is not None
        test.auditor.own = (test.candidates, label[test.rows], usable[test.rows])
        audit_result = test.auditor.finish(test.tokens, test.records)
        audit_result["seconds"] = round(time.perf_counter() - t0, 1)
        test.auditor = None
        lap("test:audit")

    t0 = time.perf_counter()
    results, outcomes, auprc = _evaluate(
        paths, t, test, part, label, usable, names, reps, window_reps, seed
    )
    seconds["test:evaluate"] = round(time.perf_counter() - t0, 1)
    lap("test:evaluate")

    x6_out: dict[str, Any] | None = None
    narrative: dict[str, Any] | None = None
    if x6:
        t0 = time.perf_counter()
        test_scores = {LEVELS[lv]: scores[LEVELS[lv]] for lv in levels6}
        tables = level_tables(paths, option, seed, test.keys, test_scores, part, levels6)
        x6_out = {"seed": seed, "levels": {}}
        narrative_test: dict[str, Any] = {}
        for lv in levels6:
            table, n_inc, n_feat = tables[lv]
            proba = {}
            preds = attribute_frozen(val_tables[lv][0], table, lv, seed, catalogue, proba)
            x6_out["levels"][lv] = level_entry(table, preds, n_inc, n_feat)
            if keep_tables and lv in ("S0", "S2"):
                narrative_test[lv] = {"table": table, **proba}
        if keep_tables:
            narrative = {"val": narrative_val, "test": narrative_test, "seed": seed}
        seconds["test:x6"] = round(time.perf_counter() - t0, 1)

    random_ref = (
        _random_reference(paths, option, reps, window_reps, part) if random_reference else None
    )
    seconds["total"] = round(time.perf_counter() - t_start, 1)
    return {
        "seed": seed,
        "results": results,
        "outcomes": outcomes,
        "protocol": test.protocol,
        "protocol_val": val_protocol,
        "candidates": len(test.rows),
        "alerts": int(test.alerted.sum()),
        "seconds": seconds,
        "memory_mb": memory,
        "audit": audit_result,
        "auprc": auprc,
        "scores_sha256": digest,
        "token_use": tokens_used,
        "x6": x6_out,
        "narrative": narrative,
        "random": random_ref,
    }


def run_x1_test(
    paths: DatasetPaths,
    option: str = "B8",
    headline_seeds: tuple[int, ...] = HEADLINE_SEEDS,
    other_seeds: tuple[int, ...] = OTHER_SEEDS,
    reps: int = 1000,
    window_reps: int = TEST_WINDOW_REPS,
    sweeps: bool = True,
    audit: bool = True,
    x6: bool = True,
    allow_repeat: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """X1 (and X6) on test: every configuration on ``other_seeds``, the headline ones on
    ``headline_seeds`` too. The audit, the random reference and the narrative's tables
    come from the first seed."""
    from finmesh.training import x6 as x6mod
    from finmesh.training.x1 import combine

    if x6 and not sweeps:
        raise ValueError("X6 needs S3 at eps = 2 from the sweeps; drop --no-sweeps or add --no-x6")
    store = EvalStore(paths, option)
    opener = opener_for(store, allow_repeat)
    out_dir = test_dir(paths, option)
    seeds = sorted(set(headline_seeds) | set(other_seeds))
    first = seeds[0]
    t0 = time.perf_counter()
    per_seed: list[dict[str, Any]] = []
    with AnonPeak() as anon:
        for seed in seeds:
            ckpt = out_dir / f"x1_seed{seed}.pkl"
            if ckpt.exists():
                per_seed.append(_load(ckpt))
                if progress:
                    progress(f"seed {seed}: kept from {ckpt.name}")
                continue
            full = seed in other_seeds
            refuse_if_opened(paths, x1_config(paths, option, x6 and full), seed, allow_repeat)
            r = run_x1_test_seed(
                paths,
                option,
                seed,
                opener,
                reps,
                window_reps,
                anon,
                sweeps=sweeps,
                audit=audit and seed == first,
                only=None if full else X1_HEADLINE,
                x6=x6 and full,
                keep_tables=x6 and seed == first,
                random_reference=seed == first,
            )
            if r["narrative"] is not None:
                _save(out_dir / "narrative_inputs.pkl", r["narrative"])
                r["narrative"] = None
            _save(ckpt, r)
            per_seed.append(r)
            if progress:
                progress(f"seed {seed}: {r['seconds']['total']:.0f} s")
        summary = combine(per_seed, reps, holm_family=True)
        x6_seeds = [r["x6"] for r in per_seed if r.get("x6")]
        x6_summary = x6mod.combine(x6_seeds, reps) if x6_seeds else None
    base = next(r for r in per_seed if r["seed"] == first)
    return {
        "dataset": paths.name,
        "option": option,
        "split": "test",
        "seeds": seeds,
        "headline_seeds": list(headline_seeds),
        "other_seeds": list(other_seeds),
        "headline_configurations": sorted(X1_HEADLINE),
        "primary_budget": "per_1000_per_day",
        "delay_windows": 12,
        "primary_fusion": "stacker",
        "h1b_ceiling": "oracle-relational",
        "sweeps": sweeps,
        "audit": base["audit"],
        "epsilons": [0.5, 1.0, 2.0, 4.0, 8.0] if sweeps else [],
        "taus": [2, 3, 4] if sweeps else [],
        "summary": summary,
        "random": base["random"],
        "token_use": base.get("token_use"),
        "x6": (
            {"seeds": [s["seed"] for s in x6_seeds], "summary": x6_summary, "per_seed": x6_seeds}
            if x6_summary
            else None
        ),
        "per_seed": [
            {
                "seed": r["seed"],
                "seconds": r["seconds"],
                "memory_mb": r["memory_mb"],
                "protocol": r["protocol"],
                "candidates": r["candidates"],
                "alerts": r["alerts"],
                "auprc": r["auprc"],
                "scores_sha256": r["scores_sha256"],
                "token_use": {
                    k: v for k, v in (r.get("token_use") or {}).items() if k != "per_bank_epoch"
                },
                "linked": {n: float(o["linked"].mean()) for n, o in r["outcomes"].items()},
            }
            for r in per_seed
        ],
        "openings": [e for e in openings(paths) if e["config_hash"]],
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
    }


__all__ = [
    "HEADLINE_SEEDS",
    "OTHER_SEEDS",
    "X1_HEADLINE",
    "opener_for",
    "run_baselines_test",
    "run_x1_test",
    "run_x1_test_seed",
    "scores_digest",
    "test_dir",
]
