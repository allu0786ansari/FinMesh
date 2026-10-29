"""The relational oracle (amendment A14): pooled data *and* relational re-ranking.

X1 on validation (week 7) showed every sharing level, and plaintext score
propagation, beating the preregistered oracle in linked detection. The
oracle pools the data but scores each account-window on its own; the
sharing levels re-rank each queue from counterparties' evidence, which
concentrates alerts on connected scheme accounts. So the oracle is not a
ceiling for relational triage, and H1b's denominator needs one that is.

The relational oracle gives the pooled model the same re-ranking with full
plaintext access:

* candidates: account-windows with calibrated oracle probability at the
  evidence floor (0.01), or an oracle alert;
* features: own oracle logit; over *every* counterparty in the federation
  (any member, both directions) within the lookback: their number, how
  many the oracle alerted, the highest and the summed oracle probability;
* the same cross-fitted per-member stacker as the sharing levels (A13).

``oracle+propagation`` is its fixed-rule counterpart: own oracle probability
plus 0.5 x the strongest counterparty's.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from finmesh.eval.guard import KEY_COLUMNS

RELATIONAL_FEATURES: tuple[str, ...] = (
    "own_logit",
    "n_cp",
    "n_cp_alert",
    "max_cp_prob",
    "sum_cp_prob",
)
FLOOR = 0.01


def neighbour_features(
    keys: pl.DataFrame,
    prob: np.ndarray,
    alerted: np.ndarray,
    rows: np.ndarray,
    edges: pl.DataFrame,
    lookback: int,
) -> pl.DataFrame:
    """Features of :data:`RELATIONAL_FEATURES` for ``rows`` of ``keys``.

    ``edges`` has src, dst, window (both directions are used). A counterparty
    counts when an edge falls in the candidate's lookback, and its probability
    is its highest over its own windows in the same span.
    """
    cand = keys[rows].select(*KEY_COLUMNS).with_columns(pl.Series("row", rows))
    acc = cand.select(pl.col("account").unique())
    e = edges.select("src", "dst", pl.col("window").alias("w_edge"))
    sides = pl.concat(
        [
            e.join(acc, left_on="src", right_on="account", how="semi").select(
                pl.col("src").alias("account"), pl.col("dst").alias("cp"), "w_edge"
            ),
            e.join(acc, left_on="dst", right_on="account", how="semi").select(
                pl.col("dst").alias("account"), pl.col("src").alias("cp"), "w_edge"
            ),
        ]
    )
    pairs = (
        cand.select("account", "window", "row")
        .join(sides, on="account")
        .filter(
            (pl.col("w_edge") <= pl.col("window"))
            & (pl.col("w_edge") > pl.col("window") - lookback)
        )
        .select("row", "window", "cp")
        .unique()
    )
    cp_probs = keys.select(pl.col("account").alias("cp"), pl.col("window").alias("cp_window"))
    cp_probs = cp_probs.with_columns(
        pl.Series("cp_prob", prob), pl.Series("cp_alert", alerted.astype(np.int8))
    ).join(pairs.select("cp").unique(), on="cp", how="semi")
    per_cp = (
        pairs.join(cp_probs, on="cp")
        .filter(
            (pl.col("cp_window") <= pl.col("window"))
            & (pl.col("cp_window") > pl.col("window") - lookback)
        )
        .group_by("row", "cp")
        .agg(pl.col("cp_prob").max(), pl.col("cp_alert").max())
    )
    agg = per_cp.group_by("row").agg(
        pl.len().alias("n_cp"),
        pl.col("cp_alert").sum().alias("n_cp_alert"),
        pl.col("cp_prob").max().alias("max_cp_prob"),
        pl.col("cp_prob").sum().alias("sum_cp_prob"),
    )
    p = np.clip(prob[rows], 1e-6, 1 - 1e-6)
    out = (
        cand.with_columns(
            pl.Series("prob", prob[rows]), pl.Series("own_logit", np.log(p / (1 - p)))
        )
        .join(agg, on="row", how="left")
        .sort("row")
    )
    return out.with_columns(
        pl.col(c).cast(pl.Float64).fill_null(0.0) for c in RELATIONAL_FEATURES[1:]
    ).select(*KEY_COLUMNS, "row", "prob", *RELATIONAL_FEATURES)


def propagate(feats: pl.DataFrame, weight: float) -> np.ndarray:
    """Own probability + ``weight`` x the strongest counterparty probability."""
    return np.asarray(feats["prob"].to_numpy() + weight * feats["max_cp_prob"].to_numpy())


__all__ = ["FLOOR", "RELATIONAL_FEATURES", "neighbour_features", "propagate"]
