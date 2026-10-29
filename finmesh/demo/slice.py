"""Thin demo slice (proposal section 13): one bank node, one alert, one evidence
request, one attribution, end to end, with latency.

Setup (not timed): every member's S0 detector, calibration and evidence store,
the token service at the dataset's protocol budget, and each node's token index.

Online path (timed, per alert):

1. **Session.** An alerted account-window at one member opens a session.
2. **Counterparties.** The member looks up the alerted account's
   counterparties at other members within the 72 h lookback (its own
   payment data).
3. **Tokens.** It tokenises them through the token service (blind, evaluate,
   unblind).
4. **Requests.** The issuer signs one request per counterparty and epoch; the
   responding node checks it and answers at S2.
5. **Fusion.** Noisy-OR of the member's own probability with each
   counterparty's alert flag and record probability bucket (no fitting).
6. **Attribution.** A rule-based typology from the account's own behaviour
   (a placeholder: the typology catalogue and supervised attributor are
   weeks 13–14).
7. **Card.** An incident card is written and the action recorded in a ledger;
   it never names another member's account.

PT6 asks for a p95 of 3 s from session opened to action recorded.
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import polars as pl

from finmesh.eval.guard import KEY_COLUMNS
from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.features.build import FeatureStore
from finmesh.fusion.local import link_edges
from finmesh.fusion.triage import BUCKET_MID
from finmesh.matching.tokens import identifier, token_budget
from finmesh.models.autoencoder import Autoencoder
from finmesh.paths import DatasetPaths
from finmesh.sharing.evidence import WIRE_FIELDS, bucket, build_records, load_evidence_schema
from finmesh.sharing.node import BankNode, request_epochs
from finmesh.sharing.requests import RequestGuard, RequestIssuer
from finmesh.sharing.simulate import TokenEnv
from finmesh.training.baselines import _per_member, feature_sets, fit_local_models, score_rows
from finmesh.training.data import sample_rows, slices, training_windows
from finmesh.training.sharing_run import _calibrators, store_membership

PT6_SECONDS = 3.0
ATTRIBUTION_FEATURES = (
    "fan_in",
    "fan_out",
    "pass_through",
    "cyc2",
    "cyc3",
    "cyc4",
    "sg_out_max",
    "sg_in_max",
)
FLAG_WEIGHT = 0.5  # noisy-OR weight of a counterparty's alert flag (fixed, not fitted)


def attribute(row: dict[str, Any]) -> tuple[str, str]:
    """Placeholder typology from the account's own behaviour; (label, reason)."""
    v = {k: float(row.get(k) or 0.0) for k in ATTRIBUTION_FEATURES}
    if v["cyc2"] + v["cyc3"] + v["cyc4"] > 0:
        return "cycle", "the account sits on a short cycle"
    if v["sg_out_max"] >= 3:
        return "scatter-gather", f"funds scatter to {v['sg_out_max']:.0f} accounts that re-converge"
    if v["sg_in_max"] >= 3:
        return "gather-scatter", f"funds gather from {v['sg_in_max']:.0f} accounts then scatter"
    if v["fan_out"] >= 5 and v["fan_in"] <= 1:
        return "fan-out", f"{v['fan_out']:.0f} payees from one source"
    if v["fan_in"] >= 5 and v["fan_out"] <= 1:
        return "fan-in", f"{v['fan_in']:.0f} payers into one account"
    if v["pass_through"] >= 0.8:
        return "pass-through", f"{v['pass_through']:.0%} of inflow passed on"
    return "unknown", "no rule fired"


def run_slice(
    paths: DatasetPaths, option: str = "B8", n_alerts: int = 50, seed: int = 0
) -> dict[str, Any]:
    t_setup = time.perf_counter()
    plan = load_plan(paths)
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    windows = training_windows(store, feats)
    cols = feature_sets()["all"]
    members = sorted(store.accounts_per_member()["member"].to_list())
    lookback = int(feats.meta["neighbourhood"]["lookback_windows"])
    v0, v1 = (int(x) for x in store.meta["partition_windows"]["val"])
    apm = store.accounts_per_member()
    from finmesh.training.x1 import _alerts

    models = fit_local_models(store, feats, cols, windows, seed, members)
    fn = _per_member(models)
    val = score_rows(store, feats, "val", fn)
    cal = _calibrators(score_rows(store, feats, "train", fn, windows.stop_from))
    prob = np.zeros(val.height)
    member_arr = val["member"].to_numpy()
    for m, c in cal.items():
        idx = member_arr == m
        prob[idx] = c(val["score"].to_numpy()[idx])
    keys = val.select(*KEY_COLUMNS)
    alerted = _alerts(keys, prob, apm, plan.window_hours)
    del val
    schema = load_evidence_schema()
    sample = sample_rows(feats, cols, windows, 50_000, seed)
    encoders = {
        m: Autoencoder(cols, seed).fit(sample.filter(pl.col("member") == m))
        for m in members
        if sample.filter(pl.col("member") == m).height > 100
    }
    del sample
    keep = (prob >= schema.floor) | alerted
    counters = [c[1] for c in schema.counters]
    parts, offset = [], 0
    for _, feat in slices(store, feats, "val"):
        n = feat.height
        sel = keep[offset : offset + n]
        parts.append(
            feat.filter(pl.Series(sel)).with_columns(pl.Series("row", np.nonzero(sel)[0] + offset))
        )
        offset += n
    chosen = pl.concat(parts)
    records: dict[int, pl.DataFrame] = {}
    for m in members:
        part = chosen.filter(pl.col("member") == m)
        if part.height == 0 or m not in encoders:
            continue
        idx, direction, err = encoders[m].top(part, schema.top)
        r = part["row"].to_numpy()
        records[m] = build_records(
            part.select("member", "account", "window", *counters),
            prob[r],
            alerted[r],
            idx,
            direction,
            err,
            encoders[m].embedding(part),
        )
    # Sessions: alerts with at least one counterparty at another member.
    alert_rows = np.nonzero(alerted)[0]
    rng = np.random.default_rng(seed)
    sample_alerts = keys[alert_rows].with_columns(pl.Series("row", alert_rows))
    edges = link_edges(
        paths.transactions,
        plan,
        v0,
        v1,
        lookback,
        store_membership(paths, option),
        touching=sample_alerts.select("account"),
    )
    own_feats = chosen.filter(pl.col("row").is_in(alert_rows)).select("row", *ATTRIBUTION_FEATURES)
    del chosen
    env = TokenEnv.new(token_budget(paths.name))
    issuer = RequestIssuer()
    nodes = {
        m: BankNode(m, "S2", env.client(m), RequestGuard(m, issuer.public_key), recs)
        for m, recs in records.items()
    }
    for node in nodes.values():
        node.build_index()
    setup_seconds = time.perf_counter() - t_setup

    # Pre-select sessions with cross-member counterparties (selection is not timed).
    out_e = edges.select(
        pl.col("src").alias("account"),
        pl.col("dst").alias("cp"),
        "window",
        pl.col("src_member").alias("own"),
        pl.col("dst_member").alias("cp_member"),
    )
    in_e = edges.select(
        pl.col("dst").alias("account"),
        pl.col("src").alias("cp"),
        "window",
        pl.col("dst_member").alias("own"),
        pl.col("src_member").alias("cp_member"),
    )
    sides = pl.concat([out_e, in_e]).filter(
        pl.col("cp_member").is_not_null() & (pl.col("cp_member") != pl.col("own"))
    )
    with_cp = sample_alerts.join(sides.select("account").unique(), on="account", how="semi")
    pick = rng.choice(with_cp.height, min(n_alerts, with_cp.height), replace=False)
    sessions = with_cp[np.sort(pick)]
    feats_by_row = {r["row"]: r for r in own_feats.iter_rows(named=True)}
    prob_idx = WIRE_FIELDS.index("prob_bucket")

    latencies, cards, ledger = [], [], []
    for m, acct, w, row in sessions.select(*KEY_COLUMNS, "row").iter_rows():
        t0 = time.perf_counter()
        # 2. counterparties at other members within the lookback
        cps = (
            sides.filter(
                (pl.col("account") == acct)
                & (pl.col("own") == m)
                & (pl.col("window") <= w)
                & (pl.col("window") > w - lookback)
            )
            .select("cp", "cp_member")
            .unique()
            .sort("cp")
        )
        flags, buckets, n_req, refused = 0, [], 0, 0
        for cp, cp_m in cps.iter_rows():
            if cp_m not in nodes:
                continue
            for epoch, lo, hi in request_epochs(int(w), v0, lookback):
                # 3. token, 4. signed request and S2 response
                token = env.client(int(m)).tokens(epoch, [identifier(int(cp))])[0]
                bucket_now = int(bucket(np.array([prob[row]]), schema.prob_edges)[0])
                request = issuer.issue(
                    int(m), int(cp_m), token, epoch, lo, hi, bucket_now, now=int(w)
                )
                response = nodes[int(cp_m)].respond(request, now=int(w))
                n_req += 1
                refused += int(response.status == "refused")
                flags += int(response.alert)
                if response.record is not None:
                    buckets.append(response.record.values[prob_idx])
        # 5. fusion (noisy-OR, fixed weights)
        keep_p = (1 - prob[row]) * (1 - FLAG_WEIGHT) ** flags
        for b in buckets:
            keep_p *= 1 - BUCKET_MID[min(int(b), len(BUCKET_MID) - 1)]
        fused = 1 - keep_p
        # 6. attribution (placeholder)
        label, reason = attribute(feats_by_row.get(row, {}))
        # 7. incident card and ledger
        card = {
            "member": int(m),
            "account": int(acct),  # the member's own account (hashed key)
            "window": int(w),
            "own_probability": round(float(prob[row]), 4),
            "counterparties_asked": int(cps.height),
            "requests": n_req,
            "refused": int(refused),
            "peer_alerts": int(flags),
            "peer_records": len(buckets),
            "fused_score": round(float(fused), 4),
            "typology": label,
            "typology_reason": reason,
            "action": "open case" if fused >= 0.5 or flags else "monitor",
        }
        ledger.append({"member": int(m), "window": int(w), "requests": n_req, "level": "S2"})
        latencies.append(time.perf_counter() - t0)
        cards.append(card)
    lat = np.asarray(latencies)
    return {
        "dataset": paths.name,
        "sessions": len(cards),
        "setup_seconds": round(setup_seconds, 1),
        "latency": {
            "p50": float(np.percentile(lat, 50)) if len(lat) else None,
            "p95": float(np.percentile(lat, 95)) if len(lat) else None,
            "max": float(np.max(lat)) if len(lat) else None,
        },
        "pt6_seconds": PT6_SECONDS,
        "pt6_met": bool(len(lat) and np.percentile(lat, 95) <= PT6_SECONDS),
        "typologies": {
            k: sum(c["typology"] == k for c in cards) for k in {c["typology"] for c in cards}
        },
        "actions": {k: sum(c["action"] == k for c in cards) for k in {c["action"] for c in cards}},
        "example": cards[0] if cards else None,
        "cards": cards,
        "ledger_entries": len(ledger),
        "token_budget": int(env.service.budget),
    }


def _s(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f} s"


def render_slice(r: dict[str, Any]) -> str:
    lat = r["latency"]
    ex = json.dumps(r["example"], indent=2) if r["example"] else "(none)"
    return "\n".join(
        [
            f"# Thin demo slice · {r['dataset']}",
            "",
            "One bank node, one alert, one evidence request, one attribution, end to end "
            "(proposal section 13). Setup (detectors, evidence stores, token indexes) is not "
            f"timed: {r['setup_seconds']:,.0f} s. Each session runs: counterparties at other "
            "members → tokens through the token service → signed S2 requests answered by the "
            "responders' nodes → noisy-OR fusion → rule-based typology (placeholder until "
            "weeks 13–14) → incident card and ledger entry. "
            f"Token budget {r['token_budget']:,} per bank and epoch.",
            "",
            f"**Latency over {r['sessions']} sessions:** p50 {_s(lat['p50'])}, p95 "
            f"{_s(lat['p95'])}, max {_s(lat['max'])}. PT6 (p95 ≤ {r['pt6_seconds']:g} s): "
            f"**{'met' if r['pt6_met'] else 'not met'}**.",
            "",
            f"Typologies (placeholder rules): {r['typologies']}. Actions: {r['actions']}. Ledger "
            f"entries: {r['ledger_entries']}.",
            "",
            "## Example incident card",
            "",
            "```json",
            ex,
            "```",
            "",
            "The card names only the member's own account-window; counterparties at other "
            "members appear as counts.",
            "",
        ]
    )


__all__ = ["attribute", "render_slice", "run_slice"]
