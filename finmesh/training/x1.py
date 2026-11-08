"""Experiment X1 on validation: the sharing ladder (week 7; amendment A13).

Per seed, every member runs its S0 detector (local LightGBM, calibrated on
the held-out end of training) and builds evidence records for its
candidates: account-windows with calibrated probability at the evidence
floor, or alerted. Then for each sharing level:

1. **Protocol.** Every candidate asks about its counterparties at other
   members (``finmesh.sharing.simulate``); responders answer at the level.
2. **Triage (fusion).** Each member re-scores its candidates from what it
   received and what it was asked (``finmesh.fusion.triage``). The
   **primary rule is the stacker**: a per-member logistic regression on the
   evidence features, fitted on one half of the validation windows and
   applied to the other (two-fold, by time). Noisy-OR and k-of-n are fixed
   secondary rules. Each member cuts its queue at its own budget.
3. **Linking.** Final alerts at different members are linked when the
   accounts transacted within the lookback; at S1 and above, alert flags
   travel through tokens (week 6 showed the protocol links exactly these
   pairs). S0 links only within a member.

Also: the oracle (pooled data and graph, pooled linking), a plaintext
score-propagation baseline (no cryptography), and the random-alert baseline.
Per-scheme outcomes are averaged over seeds before the scheme bootstrap.
"""

from __future__ import annotations

import time
import warnings
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from finmesh.eval.budgets import apply_budget
from finmesh.eval.guard import KEY_COLUMNS, ScoreFrame
from finmesh.eval.harness import evaluate, random_scorer
from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore, PartitionData
from finmesh.eval.split_io import load_plan
from finmesh.eval.stats import holm, interval_from, paired_difference, scheme_rate_ci
from finmesh.features.build import FeatureStore
from finmesh.fusion.local import Linker, link_edges
from finmesh.fusion.triage import evidence_features, feature_names, k_of_n, noisy_or
from finmesh.matching.tokens import token_budget
from finmesh.models.autoencoder import Autoencoder
from finmesh.models.calibration import Isotonic
from finmesh.models.gbdt import GBDT
from finmesh.paths import DatasetPaths
from finmesh.sharing.evidence import bucket, build_records, load_evidence_schema
from finmesh.sharing.ldp import EPSILONS
from finmesh.sharing.simulate import TokenEnv, counterparty_requests, simulate
from finmesh.sysinfo import AnonPeak
from finmesh.training.attacks import a5_membership
from finmesh.training.audit import Auditor
from finmesh.training.baselines import (
    DELAY_WINDOWS,
    PRIMARY,
    _per_member,
    feature_sets,
    fit_local_models,
    score_keys,
    score_rows,
)
from finmesh.training.data import feature_slices, sample_rows, training_rows, training_windows
from finmesh.training.relational import FLOOR as RELATIONAL_FLOOR
from finmesh.training.relational import RELATIONAL_FEATURES, neighbour_features, propagate
from finmesh.training.sharing_run import _calibrators, store_membership

SHARING_LEVELS: tuple[str, ...] = ("S1", "S2", "S4")
PD_TAUS: tuple[int, ...] = (2, 3, 4)  # requester bucket: p >= 0.05, 0.2, 0.5
REL_FLOOR = RELATIONAL_FLOOR
FUSIONS: tuple[str, ...] = ("stacker", "noisy_or", "kofn")  # stacker is primary (A13)
PROPAGATION_WEIGHT = 0.5
AE_SAMPLE = 200_000
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2)


# A25 P3: protected S1 flags (randomised response, gating, both), fixed before any result.
FLAG_RR_EPSILONS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0)
FLAG_GATES: tuple[int, ...] = (2, 3)
FLAG_GATED_RR: tuple[tuple[int, float], ...] = ((2, 1.0), (2, 2.0))


def flag_runs() -> list[tuple[str, str, dict[str, Any]]]:
    runs: list[tuple[str, str, dict[str, Any]]] = [
        (f"S1F[eps={e:g}]", "S1", {"flag_eps": e}) for e in FLAG_RR_EPSILONS
    ]
    runs += [(f"S1F[gate={t}]", "S1", {"flag_tau": t}) for t in FLAG_GATES]
    runs += [
        (f"S1F[gate={t},eps={e:g}]", "S1", {"flag_tau": t, "flag_eps": e}) for t, e in FLAG_GATED_RR
    ]
    return runs


def level_runs(
    sweeps: bool = True, flags: bool | Collection[str] = False
) -> list[tuple[str, str, dict[str, Any]]]:
    """(configuration name, protocol level, parameters) for every protocol run of a seed.
    ``flags``: True adds every protected-flag candidate (A25 P3), a collection only those
    named (the chosen one, on the Large tests)."""
    runs: list[tuple[str, str, dict[str, Any]]] = [(lv, lv, {}) for lv in SHARING_LEVELS]
    if sweeps:
        runs += [(f"S3[eps={e:g}]", "S3", {"epsilon": e}) for e in EPSILONS]
        runs += [(f"PD[tau={t}]", "PD", {"tau": t}) for t in PD_TAUS]
    if flags is True:
        runs += flag_runs()
    elif flags:
        wanted = set(flags)
        runs += [r for r in flag_runs() if r[0] in wanted]
    return runs


def _halves(windows: np.ndarray, v0: int, v1: int) -> np.ndarray:
    """Fold 0 = first half of the validation windows, fold 1 = second half."""
    return (windows >= v0 + (v1 - v0 + 1) // 2).astype(np.int8)


Stacker = tuple[StandardScaler, LogisticRegression]


def _fit_stacker(x: np.ndarray, y: np.ndarray, seed: int) -> Stacker:
    scaler = StandardScaler().fit(x)
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=seed).fit(
        scaler.transform(x), y
    )
    return scaler, model


def stacker_scores(
    feats: pl.DataFrame,
    names: tuple[str, ...],
    label: np.ndarray,
    usable: np.ndarray,
    fold: np.ndarray,
    seed: int,
) -> np.ndarray:
    """Per member, two-fold by time: fit on one half, score the other."""
    out = feats["prob"].to_numpy().copy()
    x_all = feats.select(names).to_numpy().astype(np.float64)
    members = feats["member"].to_numpy()
    for m in np.unique(members):
        for k in (0, 1):
            fit = (members == m) & (fold == k) & usable
            apply = (members == m) & (fold != k)
            if not apply.any() or fit.sum() < 20 or len(np.unique(label[fit])) < 2:
                continue
            scaler, model = _fit_stacker(x_all[fit], label[fit], seed)
            out[apply] = model.predict_proba(scaler.transform(x_all[apply]))[:, 1]
    return out


def fit_stackers(
    feats: pl.DataFrame,
    names: tuple[str, ...],
    label: np.ndarray,
    usable: np.ndarray,
    seed: int,
) -> dict[int, Stacker]:
    """Per member, on every usable candidate (both validation halves): frozen for the test."""
    x_all = feats.select(names).to_numpy().astype(np.float64)
    members = feats["member"].to_numpy()
    out: dict[int, Stacker] = {}
    for m in np.unique(members):
        fit = (members == m) & usable
        if fit.sum() < 20 or len(np.unique(label[fit])) < 2:
            continue
        out[int(m)] = _fit_stacker(x_all[fit], label[fit], seed)
    return out


def apply_stackers(
    feats: pl.DataFrame, names: tuple[str, ...], stackers: dict[int, Stacker]
) -> np.ndarray:
    """Frozen stackers; a member without one keeps its own probability (as in cross-fitting)."""
    out = feats["prob"].to_numpy().copy()
    if feats.height == 0:
        return out
    x_all = feats.select(names).to_numpy().astype(np.float64)
    members = feats["member"].to_numpy()
    for m, (scaler, model) in stackers.items():
        idx = members == m
        if idx.any():
            out[idx] = model.predict_proba(scaler.transform(x_all[idx]))[:, 1]
    return out


def _flag_precision(
    alerted: np.ndarray,
    label: np.ndarray,
    usable: np.ndarray,
    members: np.ndarray,
    fold: np.ndarray,
) -> dict[tuple[int, int], float]:
    """Each member's own alert precision on each fold (the q of noisy-OR at S1)."""
    out = {}
    for m in np.unique(members):
        for k in (0, 1):
            sel = (members == m) & (fold == k) & usable & alerted
            out[(int(m), k)] = float(label[sel].mean()) if sel.any() else 0.0
    return out


@dataclass
class Fusion:
    """Every fusion parameter fitted on validation, frozen for the test (A24, as corrected
    on 3 Nov): stackers fitted on all validation candidates and each member's flag
    precision. Probabilities keep the validated calibration from the end of training, so
    the stackers see at test the inputs they were fitted on."""

    flag_q: dict[int, float] = field(default_factory=dict)
    stackers: dict[str, dict[int, Stacker]] = field(default_factory=dict)


UNMETERED = 2**62  # test: the token service serves every legitimate request (A24 correction)


@dataclass
class _Trained:
    """What one seed trains on the training partition; shared by validation and test."""

    plan: Any
    store: EvalStore
    feats: FeatureStore
    pooled_f: FeatureStore
    windows: Any
    cols: tuple[str, ...]
    members: list[int]
    apm: pl.DataFrame
    lookback: int
    fn: Callable[[pl.DataFrame], np.ndarray]
    s0_cal: dict[int, Isotonic]  # on the held-out end of training (the validation run's)
    oracle: Any  # GBDT, or the oracle+ table scorer (A25 adequacy track)
    oracle_cal: dict[int, Isotonic]
    encoders: dict[int, Autoencoder]
    a5: dict[str, Any] | None
    detector: str = "gbdt"  # "tx": the A25 stronger-detector track
    feature_set: str = "all"  # "no_artefacts": the A25 artefact-free track


@dataclass
class _Phase:
    """One partition scored by every configuration (scores fixed before any evaluation)."""

    partition: str
    v0: int
    v1: int
    keys: pl.DataFrame
    prob: np.ndarray
    oracle_score: np.ndarray
    oracle_prob: np.ndarray
    alerted: np.ndarray
    rows: np.ndarray
    full_scores: dict[str, np.ndarray]
    row_scores: dict[str, tuple[str, np.ndarray, np.ndarray]]
    protocol: dict[str, Any]
    label: np.ndarray | None  # validation only: the test's come after its opening
    usable: np.ndarray | None
    fitted: Fusion | None = None
    auditor: Auditor | None = None
    tokens: Any = None
    records: dict[int, pl.DataFrame] | None = None
    candidates: pl.DataFrame | None = None

    @property
    def bases(self) -> dict[str, np.ndarray]:
        return {"prob": self.prob, "oracle_prob": self.oracle_prob}

    def names(self, only: frozenset[str] | None) -> list[str]:
        names = [*self.full_scores, *self.row_scores]
        return names if only is None else [n for n in names if n in only]

    def score_of(self, name: str) -> np.ndarray:
        if name in self.full_scores:
            return self.full_scores[name]
        base, at, values = self.row_scores[name]
        out = self.bases[base].copy()
        out[at] = values
        return out


def _train(
    paths: DatasetPaths,
    option: str,
    seed: int,
    audit: bool,
    lap: Callable[[str], None],
    feature_set: str = "all",
    detector: str = "gbdt",
) -> tuple[_Trained, dict[str, float]]:
    seconds: dict[str, float] = {}
    plan = load_plan(paths)
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    pooled_f = FeatureStore(paths, option, "pooled")
    windows = training_windows(store, feats)
    cols = feature_sets()[feature_set]  # A25 P1: "no_artefacts" for the artefact-free track
    members = sorted(store.accounts_per_member()["member"].to_list())
    t0 = time.perf_counter()
    oracle: Any
    fn: Callable[[pl.DataFrame], np.ndarray]
    if detector == "tx":  # A25 P6 adequacy track: S0+ and oracle+ (finmesh.training.txdetector)
        from finmesh.training.sharing_run import store_membership
        from finmesh.training.txdetector import TableScorer, TxDetector

        ranges = {p: (int(w[0]), int(w[1])) for p, w in store.meta["partition_windows"].items()}
        tail = {"train": int(windows.stop_from)}
        membership = store_membership(paths, option)
        local = TxDetector(paths, plan, feats, cols, membership, False, seed).fit(windows)
        fn = TableScorer(local, ranges, tail)
    elif detector == "gbdt":
        models = fit_local_models(store, feats, cols, windows, seed, members)
        fn = _per_member(models)
    else:
        raise ValueError(f"unknown detector {detector!r}")
    s0_cal = _calibrators(score_rows(store, feats, "train", fn, windows.stop_from))
    seconds["s0"] = round(time.perf_counter() - t0, 1)
    lap("s0")
    t0 = time.perf_counter()
    if detector == "tx":
        pooled = TxDetector(paths, plan, pooled_f, cols, membership, True, seed).fit(windows)
        oracle = TableScorer(pooled, ranges, tail)
    else:
        fit, stop = training_rows(store, pooled_f, cols, windows, seed)
        oracle = GBDT(cols, seed).fit(fit.x, fit.y, fit.w, stop.x, stop.y, stop.w)
        del fit, stop
    oracle_cal = _calibrators(score_rows(store, pooled_f, "train", oracle.score, windows.stop_from))
    seconds["oracle"] = round(time.perf_counter() - t0, 1)
    lap("oracle")
    t0 = time.perf_counter()
    schema = load_evidence_schema()
    sample = sample_rows(feats, cols, windows, AE_SAMPLE, seed)
    encoders = {
        m: Autoencoder(cols, seed).fit(sample.filter(pl.col("member") == m))
        for m in members
        if sample.filter(pl.col("member") == m).height > 100
    }
    a5 = None
    if audit:  # A5: what S4 discloses about the autoencoders' training rows
        pool = sample_rows(feats, cols, windows, AE_SAMPLE, seed + 7919)
        a5 = a5_membership(encoders, sample, pool, schema.magnitude_edges, schema.top, seed)
        del pool
    del sample
    seconds["autoencoders"] = round(time.perf_counter() - t0, 1)
    lap("autoencoders")
    trained = _Trained(
        plan,
        store,
        feats,
        pooled_f,
        windows,
        cols,
        members,
        store.accounts_per_member(),
        int(feats.meta["neighbourhood"]["lookback_windows"]),
        fn,
        s0_cal,
        oracle,
        oracle_cal,
        encoders,
        a5,
        detector,
        feature_set,
    )
    return trained, seconds


def _calibrate(score: np.ndarray, members: np.ndarray, cal: dict[int, Isotonic]) -> np.ndarray:
    out = np.zeros(len(score))
    for m, c in cal.items():
        idx = members == m
        out[idx] = c(score[idx])
    return out


def _phase(
    paths: DatasetPaths,
    option: str,
    seed: int,
    t: _Trained,
    partition: str,
    seconds: dict[str, float],
    lap: Callable[[str], None],
    sweeps: bool = True,
    audit: bool = False,
    only: frozenset[str] | None = None,
    fusion: Fusion | None = None,
    fit_fusion: bool = False,
    flags: bool | Collection[str] = False,
) -> _Phase:
    """Score ``partition`` with every configuration.

    Validation (``fusion`` None): calibration from the end of training, stackers
    cross-fitted on the validation halves, exactly the frozen validation run; with
    ``fit_fusion`` the stackers are also fitted on all validation candidates and returned
    with a validation-fitted calibration, for the test. Test (``fusion`` given): reads
    features only, never a label, and applies ``fusion``.
    """
    plan, store, feats, apm, lookback = t.plan, t.store, t.feats, t.apm, t.lookback
    v0, v1 = (int(x) for x in store.meta["partition_windows"][partition])
    is_test = fusion is not None
    p = (lambda n: f"{partition}:{n}") if (is_test or fit_fusion) else (lambda n: n)

    # S0: calibrated probability and primary-budget alerts.
    t0 = time.perf_counter()
    if is_test:
        scored = score_keys(feats, partition, t.fn)
        label = usable = None
    else:
        scored = score_rows(store, feats, partition, t.fn)
        label = scored["label"].to_numpy().astype(np.int8)
        usable = ~scored["masked"].to_numpy()
    member_arr = scored["member"].to_numpy()
    # The validated calibration (end of training) on both partitions: A13 candidates and
    # record buckets, and the stackers' inputs, mean the same thing at test.
    prob = _calibrate(scored["score"].to_numpy(), member_arr, t.s0_cal)
    keys = scored.select(*KEY_COLUMNS)
    alerted = _alerts(keys, prob, apm, plan.window_hours)
    fitted: Fusion | None = None
    if fit_fusion:
        fitted = Fusion()
    del scored
    seconds[p("s0_score")] = round(time.perf_counter() - t0, 1)

    # Oracle: pooled rows and graph.
    t0 = time.perf_counter()
    if is_test:
        oracle_score = score_keys(t.pooled_f, partition, t.oracle.score)["score"].to_numpy()
    else:
        oracle_score = score_rows(store, t.pooled_f, partition, t.oracle.score)["score"].to_numpy()
    oracle_prob = _calibrate(oracle_score, member_arr, t.oracle_cal)
    oracle_alerted = _alerts(keys, oracle_score, apm, plan.window_hours)
    seconds[p("oracle_score")] = round(time.perf_counter() - t0, 1)
    lap(p("oracle"))

    # Relational oracle (A14): pooled scores re-ranked from every counterparty's.
    t0 = time.perf_counter()
    rel_rows = np.nonzero((oracle_prob >= REL_FLOOR) | oracle_alerted)[0]
    rel_edges = link_edges(
        paths.transactions, plan, v0, v1, lookback, touching=keys[rel_rows].select("account")
    )
    rel = neighbour_features(keys, oracle_prob, oracle_alerted, rel_rows, rel_edges, lookback)
    del rel_edges
    row_scores: dict[str, tuple[str, np.ndarray, np.ndarray]] = {
        "oracle-relational": (
            "oracle_prob",
            rel_rows,
            _fuse(
                "oracle-relational",
                rel,
                RELATIONAL_FEATURES,
                label,
                usable,
                rel_rows,
                v0,
                v1,
                seed,
                fusion,
                fitted,
            ),
        ),
        "oracle+propagation": ("oracle_prob", rel_rows, propagate(rel, PROPAGATION_WEIGHT)),
    }
    del rel
    seconds[p("relational")] = round(time.perf_counter() - t0, 1)
    lap(p("relational"))

    # Records and candidates (with S4 embeddings).
    t0 = time.perf_counter()
    schema = load_evidence_schema()
    keep = (prob >= schema.floor) | alerted
    counter_cols = [c[1] for c in schema.counters]
    chosen_parts, offset = [], 0
    for feat in feature_slices(feats, partition):
        n = feat.height
        sel = keep[offset : offset + n]
        chosen_parts.append(
            feat.filter(pl.Series(sel)).with_columns(pl.Series("row", np.nonzero(sel)[0] + offset))
        )
        offset += n
    chosen = pl.concat(chosen_parts)
    records: dict[int, pl.DataFrame] = {}
    cand_rows: list[np.ndarray] = []
    for m in t.members:
        part = chosen.filter(pl.col("member") == m)
        if part.height == 0 or m not in t.encoders:
            continue
        idx, direction, err = t.encoders[m].top(part, schema.top)
        r = part["row"].to_numpy()
        records[m] = build_records(
            part.select("member", "account", "window", *counter_cols),
            prob[r],
            alerted[r],
            idx,
            direction,
            err,
            t.encoders[m].embedding(part),
        )
        cand_rows.append(r)
    rows = np.sort(np.concatenate(cand_rows)) if cand_rows else np.zeros(0, dtype=np.int64)
    del chosen
    candidates = keys[rows].with_columns(
        pl.Series("prob", prob[rows]),
        pl.Series("prob_bucket", bucket(prob[rows], schema.prob_edges)),
    )
    edges = link_edges(
        paths.transactions,
        plan,
        v0,
        v1,
        lookback,
        store_membership(paths, option),
        touching=candidates.select("account"),
    )
    seconds[p("records")] = round(time.perf_counter() - t0, 1)
    lap(p("records"))

    # Scores per configuration. Fusion and propagation change candidate rows only, so
    # they are kept for those rows and expanded one at a time (memory at scale).
    protocol: dict[str, Any] = {}
    cand_label = label[rows] if label is not None else None
    cand_usable = usable[rows] if usable is not None else None
    cand_members = candidates["member"].to_numpy()
    fold = _halves(candidates["window"].to_numpy(), v0, v1)
    if is_test:
        assert fusion is not None
        q_all = np.array([fusion.flag_q.get(int(m), 0.0) for m in cand_members])
    else:
        assert cand_label is not None and cand_usable is not None
        flag_q = _flag_precision(alerted[rows], cand_label, cand_usable, cand_members, fold)
        if fitted is not None:
            whole = _flag_precision(
                alerted[rows], cand_label, cand_usable, cand_members, np.zeros_like(fold)
            )
            fitted.flag_q = {m: q for (m, _), q in whole.items()}
    # One token service per seed and partition (levels reuse the OPRF work). Validation:
    # the dataset's sized budget (A16), which never bound there. Test: every legitimate
    # request is served, and the frozen budget's shortfall is reported (A24 correction).
    # The A25 side tracks (stronger detector, artefact-free features) have their own
    # candidate traffic, which the A16 budget (sized on the main detector's) was not sized
    # for: served in full on validation too, with the frozen budget's shortfall reported,
    # as at test (A24a; A25a for the artefact-free track).
    metered = not is_test and t.detector == "gbdt" and t.feature_set == "all"
    tokens = TokenEnv.new(token_budget(paths.name) if metered else UNMETERED)
    auditor = Auditor(paths, option, plan, keys, lookback, v0, v1, seed) if audit else None
    if auditor is not None:
        auditor.partition = partition
        auditor.protocol_budget = token_budget(paths.name)
        if not is_test:
            auditor.own = (candidates, cand_label, cand_usable)  # type: ignore[assignment]
        auditor.n_features = len(t.cols)
        auditor.a5 = t.a5
    for name, level, params in level_runs(sweeps, flags):
        if only is not None and not any(o.split("/")[0] == name for o in only):
            continue
        t0 = time.perf_counter()
        run = simulate(
            level,
            candidates.select(*KEY_COLUMNS, "prob_bucket"),
            records,
            edges,
            v0,
            lookback,
            n_features=len(t.cols),
            ldp_seed=seed,
            tokens=tokens,
            **params,
        )
        assert run.responses is not None and run.inbound is not None and run.asked is not None
        ev = evidence_features(level, candidates, run.responses, run.inbound, run.asked)
        if auditor is not None:
            auditor.observe(name, level, run, ev)
        variants = {
            "stacker": _fuse(
                name, ev, feature_names(level), label, usable, rows, v0, v1, seed, fusion, fitted
            )
        }
        if level in SHARING_LEVELS:
            if is_test:
                q = q_all
            else:
                q = np.array(
                    [flag_q[(int(m), int(1 - k))] for m, k in zip(ev["member"], fold, strict=True)]
                )  # precision on the *other* fold, as the stacker
            variants["noisy_or"] = _noisy_or_per_row(ev, level, q)
            variants["kofn"] = k_of_n(ev)
        for fusion_rule, sc in variants.items():
            row_scores[f"{name}/{fusion_rule}"] = ("prob", rows, np.asarray(sc, dtype=np.float64))
        protocol[name] = {k: v for k, v in run.stats.items() if k not in ("messages",)} | {
            "messages": sum(run.stats.get("messages", {}).values()),
            "seconds_total": round(time.perf_counter() - t0, 1),
        }
        lap(p(name))
        del run, ev

    # Plaintext score propagation (no cryptography): own + w * max counterparty prob.
    t0 = time.perf_counter()
    row_scores["propagation"] = (
        "prob",
        rows,
        _propagation(prob, keys, candidates, rows, edges, lookback)[rows],
    )
    seconds[p("propagation")] = round(time.perf_counter() - t0, 1)
    lap(p("propagation"))
    return _Phase(
        partition,
        v0,
        v1,
        keys,
        prob,
        oracle_score,
        oracle_prob,
        alerted,
        rows,
        {"S0": prob, "oracle": oracle_score},
        row_scores,
        protocol,
        label,
        usable,
        fitted,
        auditor,
        tokens,
        records,
        candidates,
    )


def _fuse(
    name: str,
    ev: pl.DataFrame,
    names: tuple[str, ...],
    label: np.ndarray | None,
    usable: np.ndarray | None,
    rows: np.ndarray,
    v0: int,
    v1: int,
    seed: int,
    fusion: Fusion | None,
    fitted: Fusion | None,
) -> np.ndarray:
    """The primary stacker: cross-fitted on validation halves, or validation's at test."""
    if fusion is not None:
        return apply_stackers(ev, names, fusion.stackers.get(name, {}))
    assert label is not None and usable is not None
    lab, use = label[rows], usable[rows]
    if fitted is not None:
        fitted.stackers[name] = fit_stackers(ev, names, lab, use, seed)
    return stacker_scores(ev, names, lab, use, _halves(ev["window"].to_numpy(), v0, v1), seed)


def _evaluate(
    paths: DatasetPaths,
    t: _Trained,
    ph: _Phase,
    part: PartitionData,
    label: np.ndarray,
    usable: np.ndarray,
    names: list[str],
    reps: int,
    window_reps: int,
    seed: int,
) -> tuple[dict[str, Any], dict[str, pl.DataFrame], dict[str, float]]:
    """Every configuration through the harness on ``part`` (linked detection and AUPRC)."""
    plan, apm, lookback = t.plan, t.apm, t.lookback
    # Linking edges must cover every configuration's final alerts (the oracle's can
    # fall outside S0's candidates), so they are cut to the union of all alerts.
    alert_accounts = pl.concat(
        [
            ph.keys.filter(pl.Series(_alerts(ph.keys, ph.score_of(n), apm, plan.window_hours)))
            for n in names
        ]
    ).select(pl.col("account").unique())
    full_edges = link_edges(
        paths.transactions, plan, ph.v0, ph.v1, lookback, touching=alert_accounts
    )
    linkers = {
        "local": Linker(full_edges, lookback, False),
        "pooled": Linker(full_edges, lookback, True),
    }
    results: dict[str, Any] = {}
    outcomes: dict[str, pl.DataFrame] = {}
    auprc: dict[str, float] = {}
    for name in names:
        s = ph.score_of(name)
        auprc[name] = RankedScores(label[usable], s[usable]).stats()[0]
        out: dict[str, pl.DataFrame] = {}
        rep = evaluate(
            part,
            ScoreFrame(ph.keys.with_columns(pl.Series("score", s))),
            accounts_per_member=apm,
            window_hours=plan.window_hours,
            thresholds={},
            budgets=(PRIMARY,),
            delay_windows=DELAY_WINDOWS,
            reps=reps,
            window_reps=window_reps,
            seed=seed,
            linker=linkers["local" if name == "S0" else "pooled"],
            linked_draws=0,
            outcomes=out,
        )
        results[name] = rep
        outcomes[name] = out[PRIMARY.name]
    return results, outcomes, auprc


def run_seed(
    paths: DatasetPaths,
    option: str,
    seed: int,
    reps: int,
    window_reps: int,
    meter: AnonPeak | None = None,
    sweeps: bool = True,
    audit: bool = False,
    only: frozenset[str] | None = None,
    return_scores: bool = False,
    evaluate_configs: bool = True,
    flags: bool | Collection[str] = False,
    detector: str = "gbdt",
) -> dict[str, Any]:
    """Every configuration for one seed on validation: scores and per-scheme outcomes.

    ``only`` keeps just the named configurations (protocol runs and evaluation);
    ``return_scores`` adds their final validation scores and the row keys, for
    analyses built on the frozen levels (X6); ``evaluate_configs`` False skips
    the scheme evaluation. The defaults are the frozen X1 behaviour.
    """
    t_start = time.perf_counter()
    memory: dict[str, float | None] = {}

    def lap(phase: str) -> None:
        if meter is not None:
            memory[phase] = meter.lap()

    t, seconds = _train(paths, option, seed, audit, lap, detector=detector)
    ph = _phase(paths, option, seed, t, "val", seconds, lap, sweeps, audit, only, flags=flags)
    audit_result = None
    if ph.auditor is not None:
        t0 = time.perf_counter()
        audit_result = ph.auditor.finish(ph.tokens, ph.records)
        audit_result["seconds"] = round(time.perf_counter() - t0, 1)
        ph.auditor = None
        lap("audit")
    names = ph.names(only)
    extra: dict[str, Any] = {}
    if return_scores:
        extra = {"keys": ph.keys, "scores": {n: ph.score_of(n) for n in names}}
    if not evaluate_configs:
        seconds["total"] = round(time.perf_counter() - t_start, 1)
        return {"seed": seed, "seconds": seconds, "memory_mb": memory, **extra}

    t0 = time.perf_counter()
    assert ph.label is not None and ph.usable is not None
    results, outcomes, auprc = _evaluate(
        paths, t, ph, t.store.partition("val"), ph.label, ph.usable, names, reps, window_reps, seed
    )
    seconds["evaluate"] = round(time.perf_counter() - t0, 1)
    lap("evaluate")
    seconds["total"] = round(time.perf_counter() - t_start, 1)
    return {
        "seed": seed,
        "results": results,
        "outcomes": outcomes,
        "protocol": ph.protocol,
        "candidates": len(ph.rows),
        "alerts": int(ph.alerted.sum()),
        "seconds": seconds,
        "memory_mb": memory,
        "audit": audit_result,
        "auprc": auprc,
        "token_peak": max(ph.tokens.service.used.values(), default=0),
        **extra,
    }


def _noisy_or_per_row(ev: pl.DataFrame, level: str, q: np.ndarray) -> np.ndarray:
    """Noisy-OR with a per-row flag precision (the member's, from the other fold)."""
    return noisy_or(ev, level, q)


def _alerts(keys: pl.DataFrame, score: np.ndarray, apm: pl.DataFrame, hours: int) -> np.ndarray:
    return (
        apply_budget(
            keys.with_columns(pl.Series("score", score)),
            PRIMARY,
            accounts_per_member=apm,
            window_hours=hours,
        )
        .join(keys.with_row_index("row"), on=list(KEY_COLUMNS))
        .sort("row")["alert"]
        .to_numpy()
    )


def _propagation(
    prob: np.ndarray,
    keys: pl.DataFrame,
    candidates: pl.DataFrame,
    rows: np.ndarray,
    edges: pl.DataFrame,
    lookback: int,
) -> np.ndarray:
    """Plaintext: each candidate adds w x its strongest cross-member counterparty's probability."""
    groups = counterparty_requests(
        candidates.select(*KEY_COLUMNS, "prob_bucket"), edges, lookback
    ).explode("account", empty_as_null=False)
    probs = keys.select(
        pl.col("account").alias("cp"), pl.col("window").alias("cp_window")
    ).with_columns(pl.Series("cp_prob", prob))
    best = (
        groups.join(probs, on="cp")
        .filter(
            (pl.col("cp_window") <= pl.col("window"))
            & (pl.col("cp_window") > pl.col("window") - lookback)
        )
        .group_by("member", "account", "window")
        .agg(pl.col("cp_prob").max().alias("cp_max"))
    )
    cand = (
        candidates.select(*KEY_COLUMNS)
        .with_columns(pl.Series("row", rows))
        .join(best, on=list(KEY_COLUMNS), how="left")
    )
    out = prob.copy()
    r = cand["row"].to_numpy()
    out[r] = prob[r] + PROPAGATION_WEIGHT * cand["cp_max"].fill_null(0.0).to_numpy()
    return out


class _Stack:
    """Per-scheme outcomes per configuration, one column per seed that ran it.

    At test the headline configurations run seeds 0-4 and the others 0-2 (section 7), so
    every comparison averages each side over the seeds both sides ran. With one seed set
    (validation) this is the plain seed average.
    """

    def __init__(self, seeds: list[dict[str, Any]]) -> None:
        self.names: list[str] = []
        for s in seeds:
            self.names += [n for n in s["outcomes"] if n not in self.names]
        order = seeds[0]["outcomes"]["S0"]["scheme_id"]
        self.seeds = {n: [i for i, s in enumerate(seeds) if n in s["outcomes"]] for n in self.names}
        self.data: dict[str, dict[str, np.ndarray]] = {}
        for name in self.names:
            per = {}
            for metric in ("linked", "detected", "linked_cross_member"):
                cols = []
                for i in self.seeds[name]:
                    o = seeds[i]["outcomes"][name]
                    assert o["scheme_id"].equals(order)
                    cols.append(o[metric].to_numpy().astype(float))
                per[metric] = np.column_stack(cols)
            self.data[name] = per

    def __contains__(self, name: str) -> bool:
        return name in self.data

    def common(self, *names: str) -> list[int]:
        return sorted(set.intersection(*(set(self.seeds[n]) for n in names)))

    def mean(self, name: str, metric: str = "linked", among: list[int] | None = None) -> np.ndarray:
        """Per-scheme mean over the seeds in ``among`` (default: every seed that ran it)."""
        cols = self.seeds[name] if among is None else among
        pick = [self.seeds[name].index(i) for i in cols]
        return np.asarray(self.data[name][metric][:, pick].mean(axis=1))


def combine(seeds: list[dict[str, Any]], reps: int, holm_family: bool = False) -> dict[str, Any]:
    """Seed-averaged per-scheme outcomes, intervals and paired gains over S0.

    ``holm_family`` (the test run, section 7) adds Holm-adjusted p-values across every
    sharing configuration's stacker compared with S0, for linked and any-alert detection.
    """
    stack = _Stack(seeds)
    names = stack.names
    summary: dict[str, Any] = {}
    for name in names:
        summary[name] = {
            m: scheme_rate_ci(stack.data[name][m], reps).to_dict()
            for m in ("linked", "detected", "linked_cross_member")
        }
        summary[name]["auprc_mean"] = float(
            np.mean([seeds[i]["auprc"][name] for i in stack.seeds[name]])
        )
        summary[name]["seeds"] = [int(seeds[i].get("seed", i)) for i in stack.seeds[name]]
        if name != "S0":
            among = stack.common(name, "S0")
            diff, p = paired_difference(
                stack.mean(name, "linked", among), stack.mean("S0", "linked", among), reps
            )
            summary[name]["linked_gain"] = {"difference": diff.to_dict(), "p": p}
            if holm_family:
                diff, p = paired_difference(
                    stack.mean(name, "detected", among), stack.mean("S0", "detected", among), reps
                )
                summary[name]["detected_gain"] = {"difference": diff.to_dict(), "p": p}
    levels = [n for n in names if n.endswith("/stacker")]
    if holm_family and levels:
        for metric in ("linked_gain", "detected_gain"):
            adjusted = holm([summary[lv][metric]["p"] for lv in levels])
            for lv, adj in zip(levels, adjusted, strict=True):
                summary[lv][metric]["p_holm"] = adj
        summary["holm_family"] = levels
    # H1b: share of the ceiling's gain over S0. A14 makes the relational oracle the
    # ceiling; the preregistered oracle is kept alongside.
    summary["H1b"] = {
        ceiling: {lv: _recovery(stack, lv, reps, ceiling) for lv in levels}
        for ceiling in ("oracle-relational", "oracle")
        if ceiling in stack
    }
    # Sensitivity: the stronger of the two pooled relational configurations (week 9).
    pooled = [c for c in ("oracle-relational", "oracle+propagation") if c in stack]
    if len(pooled) == 2:
        among = stack.common(*pooled)
        best = max(pooled, key=lambda c: float(stack.mean(c, "linked", among).mean()))
        summary["H1b_strongest_pooled"] = best
        summary["H1b"]["strongest-pooled"] = {lv: _recovery(stack, lv, reps, best) for lv in levels}
    # H1d: progressive disclosure against S2 (gain share and disclosure volume).
    if "S2/stacker" in stack and any(lv.startswith("PD[") for lv in levels):
        summary["H1d"] = {}
        if "S1/stacker" in stack:
            # S1 discloses no record; if it alone reaches 80% of S2's gain, H1d is uninformative.
            summary["H1d"]["S1"] = {
                "gain_share_of_S2": _recovery(stack, "S1/stacker", reps, "S2/stacker")
            }
        for lv in levels:
            if not lv.startswith("PD["):
                continue
            pd_name = lv.split("/")[0]
            among = stack.common(lv, "S2/stacker")
            s2_acc = [seeds[i]["protocol"]["S2"]["accounts_disclosed"] for i in among]
            pd_acc = [seeds[i]["protocol"][pd_name]["accounts_disclosed"] for i in among]
            share = float(np.mean([a / b for a, b in zip(pd_acc, s2_acc, strict=True) if b]))
            gain = _recovery(stack, lv, reps, "S2/stacker")
            summary["H1d"][pd_name] = {
                "gain_share_of_S2": gain,
                "disclosure_share_of_S2": share,
                "accounts_disclosed_mean": float(np.mean(pd_acc)),
                "met_on_validation": bool(
                    gain["estimate"] is not None and gain["estimate"] >= 0.8 and share < 0.5
                ),
            }
    return summary


CASE_METRICS: tuple[str, ...] = ("completeness", "fragmentation", "time_to_link_h")


def _finite(v: np.ndarray, how: Callable[[np.ndarray], Any]) -> float | None:
    v = v[np.isfinite(v)]
    return float(how(v)) if len(v) else None


def case_quality(
    seeds: list[dict[str, Any]], reps: int, pairs: tuple[tuple[str, str], ...] = ()
) -> dict[str, Any]:
    """A25 P2: case-quality metrics per configuration (seed-averaged per scheme), and paired
    differences with a scheme bootstrap. Completeness and fragmentation are over detected
    schemes, time to link over linked ones; workload = alerts raised per linked scheme."""
    names: list[str] = []
    for r in seeds:
        names += [n for n in r["outcomes"] if n not in names]
    per: dict[str, dict[str, np.ndarray]] = {}
    out: dict[str, Any] = {}
    for name in names:
        runs = [r for r in seeds if name in r["outcomes"]]
        frames = [r["outcomes"][name] for r in runs]
        if not all(m in frames[0].columns for m in CASE_METRICS):
            continue
        cols = {
            m: np.column_stack([f[m].cast(pl.Float64).fill_null(np.nan).to_numpy() for f in frames])
            for m in CASE_METRICS
        }
        with warnings.catch_warnings():  # a scheme with no value in any seed stays NaN
            warnings.simplefilter("ignore", RuntimeWarning)
            means = {m: np.nanmean(v, axis=1) for m, v in cols.items()}
        per[name] = means
        linked = [int(f["linked"].sum()) for f in frames]
        out[name] = {
            "completeness": _finite(means["completeness"], np.mean),
            "fragmentation": _finite(means["fragmentation"], np.mean),
            "time_to_link_h_median": _finite(means["time_to_link_h"], np.median),
            "workload_alerts_per_linked_scheme": float(
                np.mean([r["alerts"] / max(n, 1) for r, n in zip(runs, linked, strict=True)])
            ),
        }
    comparisons: dict[str, Any] = {}
    rng = np.random.default_rng(0)
    for a, b in pairs:
        if a not in per or b not in per:
            continue
        for m in CASE_METRICS:
            x, y = per[a][m], per[b][m]
            ok = np.isfinite(x) & np.isfinite(y)
            d = x[ok] - y[ok]
            if not len(d):
                continue
            draws = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(reps)])
            comparisons[f"{a} - {b}: {m}"] = {
                **interval_from(draws, float(d.mean())).to_dict(),
                "schemes": int(ok.sum()),
            }
    return {"configurations": out, "comparisons": comparisons}


def _recovery(
    stack: _Stack | dict[str, dict[str, np.ndarray]],
    level: str,
    reps: int,
    ceiling: str = "oracle",
) -> dict[str, Any]:
    """(level - S0) / (ceiling - S0) in linked detection, scheme bootstrap, over the seeds
    the level and the ceiling share (a plain dict: every seed column)."""
    if isinstance(stack, _Stack):
        among = stack.common(level, ceiling, "S0")
        s0 = stack.mean("S0", "linked", among)
        lv = stack.mean(level, "linked", among)
        orc = stack.mean(ceiling, "linked", among)
    else:
        s0, lv, orc = (stack[n]["linked"].mean(axis=1) for n in ("S0", level, ceiling))
    point = (lv.mean() - s0.mean()) / max(orc.mean() - s0.mean(), 1e-12)
    rng = np.random.default_rng(0)
    n = len(s0)
    draws = []
    for _ in range(reps):
        i = rng.integers(0, n, n)
        den = orc[i].mean() - s0[i].mean()
        if den > 0:
            draws.append((lv[i].mean() - s0[i].mean()) / den)
    if orc.mean() - s0.mean() <= 0 or not draws:
        # No oracle gain to recover (e.g. the fixture, where the budget yields no alerts).
        return {"estimate": None, "low": None, "high": None, "reps": 0}
    return interval_from(np.asarray(draws), float(point)).to_dict()


def run_x1(
    paths: DatasetPaths,
    option: str = "B8",
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    reps: int = 1000,
    window_reps: int = 200,
    progress: Callable[[str], None] | None = None,
    sweeps: bool = True,
    audit: bool = True,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        per_seed = []
        for seed in seeds:
            r = run_seed(
                paths,
                option,
                seed,
                reps,
                window_reps,
                anon,
                sweeps=sweeps,
                audit=audit and seed == seeds[0],
            )
            per_seed.append(r)
            if progress:
                progress(f"seed {seed}: {r['seconds']['total']:.0f} s")
        summary = combine(per_seed, reps)
        anon.lap()
        random_ref = _random_reference(paths, option, reps, window_reps)
        reference_mb = anon.lap()
    return {
        "dataset": paths.name,
        "option": option,
        "seeds": list(seeds),
        "primary_budget": PRIMARY.name,
        "delay_windows": DELAY_WINDOWS,
        "primary_fusion": "stacker",
        "h1b_ceiling": "oracle-relational",  # amendment A14
        "sweeps": sweeps,
        "audit": per_seed[0]["audit"],
        "epsilons": list(EPSILONS) if sweeps else [],
        "taus": list(PD_TAUS) if sweeps else [],
        "summary": summary,
        "random": random_ref,
        "per_seed": [
            {
                "seed": r["seed"],
                "seconds": r["seconds"],
                "memory_mb": r["memory_mb"],
                "protocol": r["protocol"],
                "candidates": r["candidates"],
                "alerts": r["alerts"],
                "auprc": r["auprc"],
                "linked": {n: float(o["linked"].mean()) for n, o in r["outcomes"].items()},
            }
            for r in per_seed
        ],
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
        "reference_mb": reference_mb,
    }


def _random_reference(
    paths: DatasetPaths,
    option: str,
    reps: int,
    window_reps: int,
    part: PartitionData | None = None,
) -> dict[str, Any]:
    """Random alerts at the same budget, linked with the pooled rule over every edge
    (validation, or the opened test partition ``part``)."""
    plan = load_plan(paths)
    store = EvalStore(paths, option)
    if part is None:
        part = store.partition("val")
    lookback = int(FeatureStore(paths, option, "member").meta["neighbourhood"]["lookback_windows"])
    v0, v1 = part.windows
    edges = link_edges(paths.transactions, plan, v0, v1, lookback)
    rep = evaluate(
        part,
        random_scorer(part.labels.keys(), 0),
        accounts_per_member=store.accounts_per_member(),
        window_hours=plan.window_hours,
        thresholds={},
        budgets=(PRIMARY,),
        delay_windows=DELAY_WINDOWS,
        reps=reps,
        window_reps=window_reps,
        seed=0,
        linker=Linker(edges, lookback, True),
        linked_draws=20,
    )
    b = rep["budgets"][0]
    return {
        "detected": b["random_alert_detected"],
        "linked": b["random_alert_linked"],
    }
