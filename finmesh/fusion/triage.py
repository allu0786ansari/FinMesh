"""Evidence features for triage, and the label-free fusion variants (week 7).

After the protocol run, each member holds, per candidate account-window:

* what it received about the candidate's counterparties at other members
  (S1: alert flags; S2: records; S4: records with embeddings), and
* what it was asked about the candidate (inbound requests and the
  requesters' score buckets), at every level that answers requests.

:func:`evidence_features` turns these into one row of features per
candidate. The fitted triage stacker (``finmesh.training.x1``) and the two
fixed fusion rules below turn the features into a new score, and each member
cuts its own queue at its budget.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from finmesh.sharing.evidence import EMBED_DIM, S4_FIELDS

KEYS = ("member", "account", "window")
# Probability-bucket midpoints for evidence probability buckets 0..4 (edges 0.01..0.5).
BUCKET_MID = (0.005, 0.03, 0.12, 0.35, 0.75)

COMMON = ("own_logit", "n_req", "n_refused", "n_cp_alert", "inbound_n", "inbound_max")
S2_EXTRA = (
    "n_cp_record",
    "max_cp_prob",
    "sum_cp_prob",
    "max_cp_dev",
    "max_cp_fan_in",
    "max_cp_fan_out",
    "max_cp_pass",
)
S4_EXTRA = tuple(f"cp_emb{i}" for i in range(EMBED_DIM))


def feature_names(level: str) -> tuple[str, ...]:
    if level == "S1":
        return COMMON
    if level == "S2":
        return (*COMMON, *S2_EXTRA)
    if level == "S4":
        return (*COMMON, *S2_EXTRA, *S4_EXTRA)
    raise ValueError(level)


def _field(name: str) -> int:
    return S4_FIELDS.index(name)


def evidence_features(
    level: str,
    candidates: pl.DataFrame,
    responses: pl.DataFrame,
    inbound: pl.DataFrame,
    asked: pl.DataFrame,
) -> pl.DataFrame:
    """One row per candidate (KEYS + prob), with the features of ``level``.

    ``responses`` holds the informative answers (alert, record or refusal);
    ``asked`` every request group with its request count, for ``n_req``.
    """
    r = responses.explode("accounts", empty_as_null=False).rename({"accounts": "account"})
    n_req = (
        asked.explode("accounts", empty_as_null=False)
        .rename({"accounts": "account"})
        .group_by(KEYS)
        .agg(pl.col("n").sum().alias("n_req"))
    )
    agg = [
        (pl.col("status") == "refused").sum().alias("n_refused"),
        pl.col("alert").sum().alias("n_cp_alert"),
    ]
    if level in ("S2", "S4"):
        rec = pl.col("record")
        prob = rec.list.get(_field("prob_bucket"), null_on_oob=True)
        dev = pl.max_horizontal(
            *[rec.list.get(_field(f"dev{k}_magnitude"), null_on_oob=True) for k in range(3)]
        )
        agg += [
            rec.is_not_null().sum().alias("n_cp_record"),
            prob.max().alias("max_cp_prob"),
            prob.sum().alias("sum_cp_prob"),
            dev.max().alias("max_cp_dev"),
            rec.list.get(_field("c_fan_in"), null_on_oob=True).max().alias("max_cp_fan_in"),
            rec.list.get(_field("c_fan_out"), null_on_oob=True).max().alias("max_cp_fan_out"),
            rec.list.get(_field("c_pass_through"), null_on_oob=True).max().alias("max_cp_pass"),
        ]
    if level == "S4":
        agg += [
            (rec.list.get(_field(f"emb{i}"), null_on_oob=True).mean() / 100).alias(f"cp_emb{i}")
            for i in range(EMBED_DIM)
        ]
    per = r.group_by(KEYS).agg(agg) if r.height else None
    inb = inbound.group_by(KEYS).agg(
        pl.len().alias("inbound_n"), pl.col("bucket").max().alias("inbound_max")
    )
    out = candidates.select(*KEYS, "prob").with_columns(
        pl.col("prob").clip(1e-6, 1 - 1e-6).pipe(lambda p: (p / (1 - p)).log()).alias("own_logit")
    )
    out = out.join(n_req, on=list(KEYS), how="left")
    if per is not None:
        out = out.join(per, on=list(KEYS), how="left")
    out = out.join(inb, on=list(KEYS), how="left")
    names = feature_names(level)
    for n in names:
        if n not in out.columns:
            out = out.with_columns(pl.lit(None, pl.Float64).alias(n))
    return out.with_columns(
        pl.col(c).cast(pl.Float64).fill_null(0.0) for c in names if c != "own_logit"
    ).select(*KEYS, "prob", *names)


def noisy_or(feats: pl.DataFrame, level: str, flag_q: float | np.ndarray) -> np.ndarray:
    """1 - (1 - p_own) * prod over counterparties (1 - q).

    S1: each flagged counterparty contributes ``flag_q`` (the member's own
    alert precision on its fitting fold). S2/S4: the strongest counterparty
    record contributes its probability-bucket midpoint, and every flag
    contributes ``flag_q``.
    """
    p = feats["prob"].to_numpy()
    flags = feats["n_cp_alert"].to_numpy()
    keep = (1 - p) * (1 - flag_q) ** flags
    if level in ("S2", "S4"):
        mid = np.asarray(BUCKET_MID)
        has = feats["n_cp_record"].to_numpy() > 0
        b = np.clip(feats["max_cp_prob"].to_numpy().astype(int), 0, len(mid) - 1)
        keep = keep * np.where(has, 1 - mid[b], 1.0)
    return np.asarray(1 - keep)


def k_of_n(feats: pl.DataFrame, k: int = 1) -> np.ndarray:
    """Candidates with at least ``k`` flagged counterparties first, then by own score."""
    return np.asarray(feats["prob"].to_numpy() + (feats["n_cp_alert"].to_numpy() >= k))


__all__ = ["BUCKET_MID", "evidence_features", "feature_names", "k_of_n", "noisy_or"]
