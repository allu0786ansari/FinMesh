"""Attacks A4-A6 of the leakage audit (week 9; amendment A16).

* **A4 linkability across epochs.** Tokens change when the epoch key rotates,
  and S3 releases are fresh after a rotation (memoised per record and epoch),
  so a peer can link two records about one account only through what the
  records say. Validation lies inside one 7-day epoch, so rotation is
  simulated at its midpoint: records an adversary received in the first half
  are candidates, records from the second half are queries. For each query
  whose account also appears in the first half, the true record is ranked
  among up to 99 random records from the same responder (at least 9) by similarity (negative
  Hamming distance over the record's fields; at S4, distance over the
  standardised fields and embedding). Reported: hit@1 and mean reciprocal rank
  against chance (1/100). Positive control: static tokens link every pair.
* **A5 membership inference on S4.** Can a peer tell whether an
  account-window was in the training sample of another member's autoencoder,
  from what S4 discloses (top deviations, their magnitude buckets, the
  embedding)? Members: the autoencoder's training rows; non-members: other
  training-window rows of the same member. Strong adversary (classifier
  trained on half), TPR at low FPR against 1% chance.
* **A6 query leakage.** What does being asked reveal? A responder predicts
  whether its own candidate account-window is laundering from its own score,
  then from its own score plus the requests it received about it (count,
  distinct requesters, highest requester bucket). The gain is what requests
  reveal; it is inherent to any exchange (proposal: measured, not prevented).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from finmesh.sharing.evidence import EMBED_DIM, S4_FIELDS, WIRE_FIELDS, bucket
from finmesh.sharing.ldp import LDP_FIELDS, field_domains, k_rr

A4_CANDIDATES = 100  # the true record plus up to 99 decoys
A4_MIN_DECOYS = 9
A4_MAX_QUERIES = 20_000
A5_PER_MEMBER = 5_000


# --- A4 ---------------------------------------------------------------------------------


def _record_matrix(level: str, records: pl.Series) -> np.ndarray:
    n = len(S4_FIELDS) if level == "S4" else len(WIRE_FIELDS)
    keep = [WIRE_FIELDS.index(f) for f in LDP_FIELDS]  # drop window and alert
    if level == "S4":
        keep += [S4_FIELDS.index(f"emb{i}") for i in range(EMBED_DIM)]
    m = np.asarray(records.to_list(), dtype=np.float64).reshape(-1, n)
    return m[:, keep]


def a4_linkability(
    level: str,
    responses: pl.DataFrame,
    v0: int,
    v1: int,
    seed: int,
    epsilon: float | None = None,
    n_features: int | None = None,
) -> dict[str, Any]:
    """Rank the true early record of an account among decoys from the same responder.

    With ``epsilon`` (S3), ``responses`` are the S2 run's true records and each
    half's record is released independently through k-RR at ``epsilon``: after a
    key rotation a record gets a fresh release, as the node does.
    """
    r = responses.filter(pl.col("record").is_not_null()).select(
        pl.col("member").alias("adversary"),
        pl.col("cp_member").alias("responder"),
        "cp",
        "window",
        "record",
    )
    if r.height == 0:
        return {"queries": 0}
    mid = v0 + (v1 - v0 + 1) // 2
    # One record per (adversary, responder, account, half): the latest.
    r = (
        r.with_columns((pl.col("window") >= mid).cast(pl.Int8).alias("half"))
        .sort("window")
        .group_by("adversary", "responder", "cp", "half")
        .agg(pl.col("record").last())
    )
    x_all = _record_matrix(level, r["record"])
    if epsilon is not None:
        dom = field_domains(int(n_features or 0))
        noise_rng = np.random.default_rng(seed + 101)
        per_field = epsilon / len(LDP_FIELDS)
        for c, name in enumerate(LDP_FIELDS):
            x_all[:, c] = k_rr(x_all[:, c].astype(np.int64), dom[name], per_field, noise_rng)
    if level == "S4":  # standardise so embedding units and bucket indices are comparable
        sd = x_all.std(axis=0)
        x_all = (x_all - x_all.mean(axis=0)) / np.where(sd > 0, sd, 1.0)
    r = r.with_row_index("i")
    rng = np.random.default_rng(seed)
    early = r.filter(pl.col("half") == 0)
    late = r.filter(pl.col("half") == 1)
    pairs = late.join(
        early.select("adversary", "responder", "cp", pl.col("i").alias("j")),
        on=["adversary", "responder", "cp"],
    )
    if pairs.height > A4_MAX_QUERIES:
        pairs = pairs.sample(n=A4_MAX_QUERIES, seed=seed)
    pools = {k: g["i"].to_numpy() for k, g in early.group_by("adversary", "responder")}
    ranks: list[int] = []
    sizes: list[int] = []
    for adv, resp, qi, tj in pairs.select("adversary", "responder", "i", "j").iter_rows():
        pool = pools[(adv, resp)]
        decoys = pool[pool != tj]
        if len(decoys) < A4_MIN_DECOYS:
            continue
        k = min(len(decoys), A4_CANDIDATES - 1)
        cand = np.concatenate([[tj], rng.choice(decoys, k, replace=False)])
        sizes.append(k + 1)
        if level == "S4":
            d = np.sqrt(((x_all[cand] - x_all[qi]) ** 2).sum(axis=1))
        else:
            d = (x_all[cand] != x_all[qi]).sum(axis=1).astype(np.float64)
        d = d + rng.random(len(d)) * 1e-6  # random tie-break
        ranks.append(int((d < d[0]).sum()) + 1)
    if not ranks:
        return {"queries": 0}
    rk = np.asarray(ranks)
    boot = rng.integers(0, len(rk), (200, len(rk)))
    hit = (rk == 1).astype(float)
    return {
        "queries": len(rk),
        "candidates_mean": float(np.mean(sizes)),
        "chance_hit1": float(np.mean(1 / np.asarray(sizes))),
        "hit1": float(hit.mean()),
        "hit1_low": float(np.percentile(hit[boot].mean(axis=1), 2.5)),
        "hit1_high": float(np.percentile(hit[boot].mean(axis=1), 97.5)),
        "mrr": float((1 / rk).mean()),
        "static_token_hit1": 1.0,  # positive control: tokens equal without rotation
    }


# --- A5 ---------------------------------------------------------------------------------


def a5_membership(
    encoders: dict[int, Any],
    members: pl.DataFrame,
    pool: pl.DataFrame,
    magnitude_edges: tuple[float, ...],
    top: int,
    seed: int,
) -> dict[str, Any]:
    """Member rows (the autoencoders' training sample) against other training rows."""
    from finmesh.training.audit import _attack, _bootstrap, _ci, _metrics

    keys = ["member", "account", "window"]
    non = pool.join(members.select(keys), on=keys, how="anti")
    xs, ys, groups = [], [], []
    rng = np.random.default_rng(seed)
    for m, enc in encoders.items():
        a = members.filter(pl.col("member") == m)
        b = non.filter(pl.col("member") == m)
        n = min(a.height, b.height, A5_PER_MEMBER)
        if n < 50:
            continue
        for frame, flag in ((a.sample(n=n, seed=seed), 1), (b.sample(n=n, seed=seed), 0)):
            idx, direction, err = enc.top(frame, top)
            mag = bucket(err, magnitude_edges)
            emb = enc.embedding(frame)
            xs.append(np.column_stack([idx, direction, mag, emb, np.full(n, m)]))
            ys.append(np.full(n, flag))
            groups.append(frame["account"].to_numpy())
    if not xs:
        return {"rows": 0}
    x, y, g = np.vstack(xs), np.concatenate(ys), np.concatenate(groups)
    split = (pl.Series(g).hash(seed=31) % 2).to_numpy() == 0
    scores = _attack(x[split], y[split], x[~split], seed)
    prior = rng.random(int((~split).sum()))  # chance: no information
    yt = y[~split]
    draws = _bootstrap(yt, {"S4": scores, "prior": prior}, g[~split], 200, seed)
    out = {k: _ci(v, draws["S4"][k]) for k, v in _metrics(yt, scores).items()}
    return {"rows": len(y), "test": int((~split).sum()), "S4": out}


# --- A6 ---------------------------------------------------------------------------------


def a6_query_leakage(
    candidates: pl.DataFrame,
    label: np.ndarray,
    usable: np.ndarray,
    inbound: pl.DataFrame,
    seed: int,
) -> dict[str, Any]:
    """Responder's prediction of its own label: own score alone, then with inbound requests.

    ``candidates``: member, account, window, prob (the responder's own rows that
    could be asked about); ``label`` and ``usable`` align with it.
    """
    from finmesh.training.audit import _attack, _bootstrap, _ci, _metrics

    keys = ["member", "account", "window"]
    inb = inbound.group_by(keys).agg(
        pl.len().alias("inbound_n"), pl.col("bucket").max().alias("inbound_max")
    )
    f = candidates.select(*keys, "prob").join(inb, on=keys, how="left").fill_null(0)
    p = np.clip(f["prob"].to_numpy(), 1e-6, 1 - 1e-6)
    own = np.log(p / (1 - p))[:, None]
    full = np.column_stack([own, f["inbound_n"].to_numpy(), f["inbound_max"].to_numpy()]).astype(
        np.float64
    )
    keep = usable
    acct = f["account"].to_numpy()
    split = (pl.Series(acct).hash(seed=37) % 2).to_numpy() == 0
    tr, te = split & keep, (~split) & keep
    y = label.astype(np.int8)
    s_own = _attack(own[tr], y[tr], own[te], seed)
    s_full = _attack(full[tr], y[tr], full[te], seed)
    draws = _bootstrap(y[te], {"own": s_own, "own+requests": s_full}, acct[te], 200, seed)
    res: dict[str, Any] = {}
    for name, s in (("own", s_own), ("own+requests", s_full)):
        res[name] = {k: _ci(v, draws[name][k]) for k, v in _metrics(y[te], s).items()}
    diff = _metrics(y[te], s_full)["tpr_0.01"] - _metrics(y[te], s_own)["tpr_0.01"]
    res["gain_tpr_0.01"] = _ci(diff, draws["own+requests"]["tpr_0.01"] - draws["own"]["tpr_0.01"])
    asked = f["inbound_n"].to_numpy() > 0
    return {
        "rows": int(keep.sum()),
        "asked_share": float(asked[keep].mean()) if keep.any() else 0.0,
        "positives_asked_share": float(asked[keep & (y == 1)].mean())
        if (keep & (y == 1)).any()
        else 0.0,
        "attack": res,
        "requester_bucket_in_clear": True,
    }


__all__ = ["a4_linkability", "a5_membership", "a6_query_leakage"]
