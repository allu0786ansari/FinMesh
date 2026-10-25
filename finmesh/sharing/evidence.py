"""Minimised evidence records (proposal Section 8.4; schema ``evidence_v1.json``).

A member builds a record for each of its account-windows whose calibrated
probability reaches the evidence floor (the lowest probability bucket edge).
Records stay in the member's evidence store; only the fields below ever leave
it, and only in a response the member's sharing level allows:

* time bucket (window), probability bucket, alert flag;
* the three most deviating features (index, direction, magnitude bucket);
* bucketed behaviour counters.

The account itself never leaves the node: a response names its subject by
the token the requester already holds.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "evidence_v1.json"


@dataclass(frozen=True)
class EvidenceSchema:
    prob_edges: tuple[float, ...]
    magnitude_edges: tuple[float, ...]
    top: int
    counters: tuple[tuple[str, str, tuple[float, ...]], ...]  # (name, feature, edges)
    sha256: str

    @property
    def floor(self) -> float:
        """Records exist for account-windows at or above the first probability edge."""
        return self.prob_edges[0]

    def cardinality(self) -> dict[str, int]:
        """Number of values per field (regular buckets plus one for missing)."""
        out = {"prob_bucket": len(self.prob_edges) + 1}
        for name, _, edges in self.counters:
            out[name] = len(edges) + 2
        return out


@cache
def load_evidence_schema() -> EvidenceSchema:
    raw = SCHEMA_PATH.read_bytes()
    doc = json.loads(raw)
    return EvidenceSchema(
        prob_edges=tuple(doc["probability"]["edges"]),
        magnitude_edges=tuple(doc["deviations"]["magnitude_edges"]),
        top=int(doc["deviations"]["top"]),
        counters=tuple((c["name"], c["feature"], tuple(c["edges"])) for c in doc["counters"]),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def bucket(values: np.ndarray[Any, Any], edges: tuple[float, ...]) -> np.ndarray[Any, Any]:
    """Index of the bucket (number of edges at or below the value); missing -> len + 1."""
    v = np.asarray(values, dtype=np.float64)
    out = np.searchsorted(np.asarray(edges), np.nan_to_num(v, nan=0.0), side="right")
    return np.where(np.isnan(v), len(edges) + 1, out).astype(np.int8)


def build_records(
    frame: pl.DataFrame,
    prob: np.ndarray[Any, Any],
    alerted: np.ndarray[Any, Any],
    top_idx: np.ndarray[Any, Any],
    top_dir: np.ndarray[Any, Any],
    top_err: np.ndarray[Any, Any],
) -> pl.DataFrame:
    """Records for the rows of ``frame`` (member, account, window, counter features).

    ``prob`` are calibrated probabilities, ``alerted`` the member's own alert
    decisions, ``top_*`` the autoencoder's top deviations for the same rows.
    Rows below the evidence floor are dropped unless alerted.
    """
    s = load_evidence_schema()
    keep = (prob >= s.floor) | alerted
    cols: dict[str, Any] = {
        "member": frame["member"].to_numpy()[keep],
        "account": frame["account"].to_numpy()[keep],  # stays on the node
        "window": frame["window"].to_numpy()[keep],
        "alert": alerted[keep],
        "prob_bucket": bucket(prob[keep], s.prob_edges),
    }
    mag = bucket(top_err[keep], s.magnitude_edges)
    for k in range(s.top):
        cols[f"dev{k}_feature"] = top_idx[keep, k].astype(np.int8)
        cols[f"dev{k}_direction"] = top_dir[keep, k].astype(np.int8)
        cols[f"dev{k}_magnitude"] = mag[:, k]
    for name, feature, edges in s.counters:
        cols[f"c_{name}"] = bucket(frame[feature].cast(pl.Float64).to_numpy()[keep], edges)
    return pl.DataFrame(cols)


WIRE_FIELDS: tuple[str, ...] = (
    "window",
    "alert",
    "prob_bucket",
    *(f"dev{k}_{p}" for k in range(3) for p in ("feature", "direction", "magnitude")),
    *(f"c_{c['name']}" for c in json.loads(SCHEMA_PATH.read_text())["counters"]),
)
