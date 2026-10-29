"""Leakage audit, attacks A1-A3 on validation (week 8; amendment A15).

An honest-but-curious peer bank (ADV-2) attacks what it legitimately receives.
Every attack is scored as TPR at 0.1% and 1% FPR (and AUC) against a
**prior-only** attack that sees only what the adversary knew before asking:
its own accounts in the request group, its own score bucket, the window, and
the two banks involved.

* **A1 token re-identification.** The adversary holds candidate account
  numbers: every account at another member that its own customers paid or
  were paid by, up to the end of validation. Targets are the tokens of every
  other member's evidence records (what any request or leaked log could
  carry). Under shared-key hashing it tokenises every candidate offline,
  unmetered. Under the OPRF it must query the token service within its
  per-epoch budget, on top of its legitimate use, and every query is logged.
* **A2 relationship inference.** For each counterparty it asked about: did
  that account transact, in the window its answer describes, with an account
  at a *third* member (neither the responder nor the adversary)?
* **A3 attribute inference.** Same targets: is the account's outgoing amount
  in the top decile of queried accounts? Its fan-in in the top decile? Is it
  a pass-through account (pass-through ratio >= 0.9)?

A2 and A3 use a **strong** adversary: a gradient-boosted classifier trained
on the true attributes of half the queried accounts (split by account) and
tested on the other half. Real adversaries know less; the audit bounds them.

H1c (A15): a level stays within the margin when the upper end of the 95% CI
of (attack - prior) TPR at 1% FPR is at most :data:`MARGIN` for every A2/A3
target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from finmesh.data.lowmem import hashed_key
from finmesh.data.splits import window_index_expr
from finmesh.eval.sealed import EvalStore
from finmesh.eval.stats import interval_from
from finmesh.features.build import FeatureStore
from finmesh.fusion.local import link_edges
from finmesh.matching.tokens import QUERY_BUDGET, HashTokenClient, TokenClient, identifier
from finmesh.paths import DatasetPaths
from finmesh.sharing.evidence import S4_FIELDS, WIRE_FIELDS
from finmesh.training.data import slices
from finmesh.training.sharing_run import store_membership

MARGIN = 0.05  # H1c: attack - prior TPR at 1% FPR, upper 95% bound (A15)
FPRS: tuple[float, ...] = (0.001, 0.01)
AUDIT_REPS = 200
MAX_TARGETS = 200_000  # sampled by counterparty account hash when the plan is larger
TOP_DECILE = 0.9
PASS_THROUGH = 0.9
SIZED_BUDGET_FACTOR = 2.0  # A1: budget sized to twice the largest legitimate use
TARGETS: tuple[str, ...] = ("A2_third_party", "A3_amount_top", "A3_fan_in_top", "A3_pass_through")
PRIOR_FEATURES: tuple[str, ...] = ("adversary", "responder", "n_own", "bucket", "n", "w_rel")
TRUTH_FEATURES: tuple[str, ...] = ("amt_out", "fan_in", "pass_through")


def tpr_at_fpr(y: np.ndarray, s: np.ndarray, fpr: float) -> float:
    """TPR at the score threshold whose FPR is at most ``fpr`` (strictly above it)."""
    neg, pos = s[y == 0], s[y == 1]
    if len(neg) == 0 or len(pos) == 0:
        return float("nan")
    thr = np.quantile(neg, 1 - fpr, method="higher")
    return float(np.mean(pos > thr))


def _auc(y: np.ndarray, s: np.ndarray) -> float:
    return float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else float("nan")


def _metrics(y: np.ndarray, s: np.ndarray) -> dict[str, float]:
    out = {"auc": _auc(y, s)}
    for f in FPRS:
        out[f"tpr_{f:g}"] = tpr_at_fpr(y, s, f)
    return out


def _bootstrap(
    y: np.ndarray,
    scores: dict[str, np.ndarray],
    clusters: np.ndarray,
    reps: int,
    seed: int = 0,
) -> dict[str, dict[str, np.ndarray]]:
    """Cluster-bootstrap draws of each metric for each score (same draws for all)."""
    _, inv = np.unique(clusters, return_inverse=True)
    n = int(np.max(inv)) + 1 if len(inv) else 0
    rows = np.arange(len(inv))
    rng = np.random.default_rng(seed)
    draws: dict[str, dict[str, list[float]]] = {k: {} for k in scores}
    for _ in range(reps):
        counts = np.bincount(rng.integers(0, n, n), minlength=n) if n else np.zeros(0, int)
        idx = np.repeat(rows, counts[inv])
        for name, s in scores.items():
            for metric, value in _metrics(y[idx], s[idx]).items():
                draws[name].setdefault(metric, []).append(value)
    return {k: {m: np.asarray(v) for m, v in d.items()} for k, d in draws.items()}


def _ci(point: float, draws: np.ndarray) -> dict[str, Any]:
    ok = draws[~np.isnan(draws)]
    if np.isnan(point) or len(ok) == 0:
        return {"estimate": None, "low": None, "high": None}
    return interval_from(ok, point).to_dict()


def _attack(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, seed: int) -> np.ndarray:
    if len(np.unique(y_train)) < 2:
        return np.zeros(len(x_test))
    model = HistGradientBoostingClassifier(max_iter=200, random_state=seed, early_stopping=False)
    model.fit(x_train, y_train)
    return np.asarray(model.predict_proba(x_test)[:, 1])


@dataclass
class Auditor:
    """Collects one seed's protocol runs and attacks each level as it finishes."""

    paths: DatasetPaths
    option: str
    plan: Any
    keys: pl.DataFrame  # validation keys (member, account, window)
    lookback: int
    v0: int
    v1: int
    seed: int = 0
    reps: int = AUDIT_REPS
    targets: pl.DataFrame | None = None
    test_scores: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)
    levels: dict[str, str] = field(default_factory=dict)

    # --- ground truth (harness only) -------------------------------------------------

    def _build_targets(self, asked: pl.DataFrame) -> pl.DataFrame:
        t = (
            asked.select(
                pl.col("member").alias("adversary"),
                "window",
                pl.col("cp_member").alias("responder"),
                "cp",
                pl.col("accounts").list.len().cast(pl.Int32).alias("n_own"),
                pl.col("bucket").cast(pl.Int32),
                "n",
            )
            .unique(subset=["adversary", "window", "responder", "cp"])
            .sort("adversary", "window", "responder", "cp")
        )
        if t.height > MAX_TARGETS:  # deterministic: whole accounts in or out
            frac = MAX_TARGETS / t.height
            t = t.filter((pl.col("cp").hash(seed=29) % 1_000_000) < int(frac * 1_000_000))
        # The window the answer describes: the counterparty's latest active window in range.
        active = self.keys.select(pl.col("account").alias("cp"), pl.col("window").alias("tw")).join(
            t.select("cp").unique(), on="cp", how="semi"
        )
        tw = (
            t.select("adversary", "window", "responder", "cp")
            .join(active, on="cp")
            .filter(
                (pl.col("tw") <= pl.col("window"))
                & (pl.col("tw") > pl.col("window") - self.lookback)
            )
            .group_by("adversary", "window", "responder", "cp")
            .agg(pl.col("tw").max())
        )
        t = t.join(tw, on=["adversary", "window", "responder", "cp"], how="inner")
        # Attribute truth from the responder's own feature rows.
        want = t.select(pl.col("cp").alias("account"), pl.col("tw").alias("window")).unique()
        feats = FeatureStore(self.paths, self.option, "member")
        store = EvalStore(self.paths, self.option)
        parts = [
            feat.select("account", "window", *TRUTH_FEATURES).join(
                want, on=["account", "window"], how="semi"
            )
            for _, feat in slices(store, feats, "val")
        ]
        truth = pl.concat(parts).rename({"account": "cp", "window": "tw"})
        t = t.join(truth, on=["cp", "tw"], how="left")
        # Third-member relationships in the described window.
        edges = link_edges(
            self.paths.transactions,
            self.plan,
            self.v0,
            self.v1,
            self.lookback,
            store_membership(self.paths, self.option),
            touching=t.select(pl.col("cp").alias("account")),
        )
        sides = pl.concat(
            [
                edges.select(
                    pl.col("src").alias("cp"), "window", pl.col("dst_member").alias("other")
                ),
                edges.select(
                    pl.col("dst").alias("cp"), "window", pl.col("src_member").alias("other")
                ),
            ]
        ).join(t.select("cp").unique(), on="cp", how="semi")
        third = (
            t.select("adversary", "responder", "cp", "tw")
            .unique()
            .join(sides.rename({"window": "tw"}), on=["cp", "tw"])
            .filter(
                pl.col("other").is_not_null()
                & (pl.col("other") != pl.col("responder"))
                & (pl.col("other") != pl.col("adversary"))
            )
            .select("adversary", "responder", "cp", "tw")
            .unique()
            .with_columns(pl.lit(True).alias("third"))
        )
        t = t.join(third, on=["adversary", "responder", "cp", "tw"], how="left")
        amt_q = float(t["amt_out"].drop_nulls().quantile(TOP_DECILE) or 0.0)
        fan_q = float(t["fan_in"].drop_nulls().quantile(TOP_DECILE) or 0.0)
        return t.with_columns(
            pl.col("third").fill_null(False).cast(pl.Int8).alias("A2_third_party"),
            (pl.col("amt_out").fill_null(0) > amt_q).cast(pl.Int8).alias("A3_amount_top"),
            (pl.col("fan_in").fill_null(0) > fan_q).cast(pl.Int8).alias("A3_fan_in_top"),
            (pl.col("pass_through").fill_null(0) >= PASS_THROUGH)
            .cast(pl.Int8)
            .alias("A3_pass_through"),
            (pl.col("window") - self.v0).alias("w_rel"),
            (pl.col("cp").hash(seed=17) % 2).cast(pl.Int8).alias("split"),
        ).drop("third")

    # --- attacks per level -----------------------------------------------------------

    def _view(self, level: str, responses: pl.DataFrame) -> pl.DataFrame:
        """What the adversary holds about each target after the level's answers."""
        n = len(S4_FIELDS) if level == "S4" else len(WIRE_FIELDS)
        r = responses.group_by("member", "window", "cp_member", "cp").agg(
            (pl.col("status") == "ok").any().cast(pl.Int8).alias("r_ok"),
            (pl.col("status") == "refused").any().cast(pl.Int8).alias("r_refused"),
            pl.col("alert").any().cast(pl.Int8).alias("r_alert"),
            pl.col("record").drop_nulls().first().alias("record"),
        )
        cols = [pl.col("record").list.get(i, null_on_oob=True).alias(f"r{i}") for i in range(n)]
        r = r.with_columns(*cols).drop("record")
        w_idx = WIRE_FIELDS.index("window")
        r = r.with_columns((pl.col("window") - pl.col(f"r{w_idx}")).alias(f"r{w_idx}"))
        return r.rename({"member": "adversary", "cp_member": "responder"})

    def observe(self, name: str, level: str, run: Any, _features: Any = None) -> None:
        if self.targets is None:
            self.targets = self._build_targets(run.asked)
        t = self.targets
        view = self._view(level, run.responses)
        joined = t.join(view, on=["adversary", "window", "responder", "cp"], how="left")
        level_cols = [c for c in view.columns if c.startswith("r")]
        x_prior = joined.select(PRIOR_FEATURES).fill_null(-1).to_numpy().astype(np.float64)
        x_level = np.column_stack(
            [x_prior, joined.select(level_cols).fill_null(-1).to_numpy().astype(np.float64)]
        )
        train = joined["split"].to_numpy() == 0
        self.levels[name] = level
        if "prior" not in self.test_scores:
            self.test_scores["prior"] = {}
            for target in TARGETS:
                y = joined[target].to_numpy()
                self.test_scores["prior"][target] = _attack(
                    x_prior[train], y[train], x_prior[~train], self.seed
                )
        self.test_scores[name] = {}
        for target in TARGETS:
            y = joined[target].to_numpy()
            self.test_scores[name][target] = _attack(
                x_level[train], y[train], x_level[~train], self.seed
            )

    # --- summary ---------------------------------------------------------------------

    def finish(
        self, tokens: Any = None, records: dict[int, pl.DataFrame] | None = None
    ) -> dict[str, Any]:
        out: dict[str, Any] = {"seed": self.seed, "margin": MARGIN, "levels": self.levels}
        if self.targets is not None and self.test_scores:
            test = self.targets.filter(pl.col("split") == 1)
            clusters = test["cp"].to_numpy()
            out["targets"] = {
                "n": self.targets.height,
                "test": test.height,
                "prevalence": {t: float(self.targets[t].mean()) for t in TARGETS},  # type: ignore[arg-type]
            }
            attacks: dict[str, Any] = {}
            for target in TARGETS:
                y = test[target].to_numpy()
                scores = {k: v[target] for k, v in self.test_scores.items()}
                draws = _bootstrap(y, scores, clusters, self.reps, self.seed)
                res: dict[str, Any] = {}
                for name, s in scores.items():
                    m = _metrics(y, s)
                    res[name] = {k: _ci(v, draws[name][k]) for k, v in m.items()}
                    if name != "prior":
                        diff = _metrics(y, s)["tpr_0.01"] - _metrics(y, scores["prior"])["tpr_0.01"]
                        d = draws[name]["tpr_0.01"] - draws["prior"]["tpr_0.01"]
                        res[name]["diff_tpr_0.01"] = _ci(diff, d)
                if "S4" in scores and "S2" in scores:
                    diff = (
                        _metrics(y, scores["S4"])["tpr_0.01"]
                        - _metrics(y, scores["S2"])["tpr_0.01"]
                    )
                    d = draws["S4"]["tpr_0.01"] - draws["S2"]["tpr_0.01"]
                    res["S4_minus_S2_tpr_0.01"] = _ci(diff, d)
                attacks[target] = res
            out["attacks"] = attacks
            out["H1c"] = _h1c(attacks, self.levels)
        if tokens is not None and records is not None:
            out["A1"] = a1_reidentification(
                self.paths, self.option, self.plan, self.v1, tokens, records
            )
        return out


def _within(attacks: dict[str, Any], target: str, name: str) -> bool | None:
    """Upper 95% bound of (attack - prior) TPR at 1% FPR at most the margin; None if undefined."""
    d = attacks[target].get(name, {}).get("diff_tpr_0.01", {})
    return None if d.get("high") is None else bool(d["high"] <= MARGIN)


def _eps(name: str) -> float:
    return float(name.split("=")[1].rstrip("]"))


def _h1c(attacks: dict[str, Any], levels: dict[str, str]) -> dict[str, Any]:
    per = {n: {t: _within(attacks, t, n) for t in TARGETS} for n in levels}

    def level_within(name: str) -> bool | None:
        vals = [v for v in per[name].values() if v is not None]
        return None if not vals else all(vals)

    claim = [n for n, lv in levels.items() if lv == "S1" or (lv == "S3" and _eps(n) <= 2)]
    verdicts = [level_within(n) for n in claim]
    out: dict[str, Any] = {
        "within_by_target": per,
        "within_margin": {n: level_within(n) for n in levels},
        "S1_and_S3_le2_within": (
            None if any(v is None for v in verdicts) or not verdicts else all(verdicts)
        ),
        "not_assessable": sorted({t for n in levels for t, v in per[n].items() if v is None}),
    }
    if "S4" in levels and "S2" in levels:
        out["S4_above_S2"] = {
            t: bool((attacks[t]["S4_minus_S2_tpr_0.01"].get("low") or 0) > 0) for t in TARGETS
        }
    s3 = sorted((_eps(n), n) for n, lv in levels.items() if lv == "S3")
    if s3:
        out["S3_tpr_by_epsilon"] = {
            t: [(e, (attacks[t][n]["tpr_0.01"] or {}).get("estimate")) for e, n in s3]
            for t in TARGETS
        }
    return out


# --- A1 --------------------------------------------------------------------------------


def _member_legs(paths: DatasetPaths, option: str, plan: Any, last: int) -> pl.LazyFrame:
    """Cross-member legs up to window ``last``: src, dst and both members."""
    m = store_membership(paths, option).lazy()
    return (
        pl.scan_parquet(paths.transactions)
        .select(
            hashed_key("src_key").alias("src"),
            hashed_key("dst_key").alias("dst"),
            window_index_expr(plan).alias("window"),
            "from_bank",
            "to_bank",
        )
        .filter(pl.col("window").is_between(0, last))
        .join(
            m.select(pl.col("bank").alias("from_bank"), pl.col("member").alias("sm")),
            on="from_bank",
            how="left",
        )
        .join(
            m.select(pl.col("bank").alias("to_bank"), pl.col("member").alias("dm")),
            on="to_bank",
            how="left",
        )
        .filter(
            pl.col("sm").is_not_null() & pl.col("dm").is_not_null() & (pl.col("sm") != pl.col("dm"))
        )
        .select("src", "dst", "sm", "dm")
    )


def _candidates(
    legs: pl.LazyFrame, adversary: int, targets: pl.DataFrame
) -> tuple[int, pl.DataFrame]:
    """One adversary's candidate list: its size, and the candidates that are target tokens.

    One pass per adversary keeps memory to one member's counterparties.
    """
    cands = (
        pl.concat(
            [
                legs.filter(pl.col("sm") == adversary).select(
                    pl.col("dst").alias("account"), pl.col("dm").alias("holder")
                ),
                legs.filter(pl.col("dm") == adversary).select(
                    pl.col("src").alias("account"), pl.col("sm").alias("holder")
                ),
            ]
        )
        .unique()
        .collect(engine="streaming")
    )
    hits = cands.join(targets, on=["account", "holder"], how="semi")
    return cands.height, hits


def a1_reidentification(
    paths: DatasetPaths,
    option: str,
    plan: Any,
    last: int,
    tokens: Any,
    records: dict[int, pl.DataFrame],
    sample: int = 200,
) -> dict[str, Any]:
    """Re-identification rate of other members' record tokens, hashing vs OPRF."""
    targets = pl.concat(
        [r.select(pl.col("member").alias("holder"), "account").unique() for r in records.values()]
    )
    legs = _member_legs(paths, option, plan, last)
    legit: dict[int, int] = {}
    for (bank, _epoch), used in tokens.service.used.items():
        legit[int(bank)] = max(legit.get(int(bank), 0), int(used))
    sized = int(SIZED_BUDGET_FACTOR * max(legit.values(), default=0))
    rows = []
    hit_frames = []
    for adv in sorted(targets["holder"].unique().to_list()):
        t_adv = targets.filter(pl.col("holder") != adv)
        n_c, hits = _candidates(legs, int(adv), t_adv)
        hit = hits.height
        hit_frames.append(hits.with_columns(pl.lit(int(adv), pl.Int32).alias("adversary")))
        n_t = t_adv.height
        row: dict[str, Any] = {
            "adversary": int(adv),
            "targets": n_t,
            "candidates": n_c,
            "hash": hit / n_t if n_t else 0.0,
            "legit_queries": legit.get(int(adv), 0),
        }
        for label, budget in (("oprf_deployed", QUERY_BUDGET), ("oprf_sized", sized)):
            spare = max(0, budget - legit.get(int(adv), 0))
            row[label] = (hit * min(1.0, spare / n_c) / n_t) if n_t and n_c else 0.0
            row[f"{label}_attack_queries"] = min(spare, n_c)
        rows.append(row)
    total_t = sum(r["targets"] for r in rows)
    pooled = {
        k: (sum(r[k] * r["targets"] for r in rows) / total_t if total_t else 0.0)
        for k in ("hash", "oprf_deployed", "oprf_sized")
    }
    check = _token_check(tokens, pl.concat(hit_frames) if hit_frames else None, sample)
    return {
        "per_adversary": rows,
        "pooled": pooled,
        "deployed_budget": QUERY_BUDGET,
        "sized_budget": sized,
        "ratio_hash_to_oprf_sized": (pooled["hash"] / pooled["oprf_sized"])
        if pooled["oprf_sized"]
        else None,
        "ratio_hash_to_oprf_deployed": (pooled["hash"] / pooled["oprf_deployed"])
        if pooled["oprf_deployed"]
        else None,
        "mechanism_check": check,
    }


def _token_check(tokens: Any, hits: pl.DataFrame | None, sample: int) -> dict[str, Any]:
    """On real tokens: a candidate the adversary tokenises matches the holder's token."""
    if hits is None:
        return {"checked": 0}
    per = max(1, sample // max(1, hits["adversary"].n_unique()))
    pairs = hits.select("adversary", "account", "holder").group_by("adversary").head(per)
    if pairs.height == 0:
        return {"checked": 0}
    shared = HashTokenClient(shared_key=b"audit-shared-key")
    epoch = 1
    match_hash = match_oprf = 0
    for adv, acct, holder in pairs.select("adversary", "account", "holder").iter_rows():
        ident = identifier(int(acct))
        a = HashTokenClient(shared.shared_key, bank=int(adv)).tokens(epoch, [ident])[0]
        b = HashTokenClient(shared.shared_key, bank=int(holder)).tokens(epoch, [ident])[0]
        match_hash += int(a == b)
        fresh = TokenClient(-1000 - int(adv), tokens.clients[next(iter(tokens.clients))].transport)
        a2 = fresh.tokens(epoch, [ident])[0]
        holder_client = tokens.clients.get(int(holder))
        b2 = holder_client.tokens(epoch, [ident])[0] if holder_client is not None else None
        match_oprf += int(a2 == b2)
    return {"checked": pairs.height, "hash_matches": match_hash, "oprf_matches": match_oprf}


__all__ = ["MARGIN", "TARGETS", "Auditor", "a1_reidentification", "tpr_at_fpr"]
