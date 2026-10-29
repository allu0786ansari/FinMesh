"""Week 9: attacks A4 and A6, the demo slice's attribution rules, G2, token budgets."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from finmesh.demo.slice import attribute
from finmesh.eval.g2 import render_g2, summarise
from finmesh.matching.tokens import QUERY_BUDGET, token_budget
from finmesh.sharing.evidence import WIRE_FIELDS
from finmesh.sharing.ldp import field_domains
from finmesh.training.attacks import a4_linkability, a6_query_leakage

SCHEMA = {
    "member": pl.Int32,
    "window": pl.Int32,
    "accounts": pl.List(pl.UInt64),
    "cp_member": pl.Int32,
    "cp": pl.UInt64,
    "status": pl.String,
    "alert": pl.Boolean,
    "record": pl.List(pl.Int64),
}


def _records(n_accounts: int, seed: int) -> pl.DataFrame:
    """Each account gets the same random record in both halves (windows 40 and 47)."""
    rng = np.random.default_rng(seed)
    dom = field_domains(47)
    rows = []
    for a in range(n_accounts):
        rec = []
        for f in WIRE_FIELDS:
            rec.append(0 if f in ("window", "alert") else int(rng.choice(dom[f])))
        for w in (40, 47):
            r = list(rec)
            r[WIRE_FIELDS.index("window")] = w
            rows.append((0, w, [a], 1, a, "ok", False, r))
    return pl.DataFrame(rows, schema=SCHEMA, orient="row")


def test_a4_links_identical_records_and_not_fresh_ldp_releases() -> None:
    resp = _records(300, 0)
    same = a4_linkability("S2", resp, 39, 50, seed=0)
    assert same["queries"] == 300 and same["hit1"] == pytest.approx(1.0)
    assert same["chance_hit1"] == pytest.approx(0.01)
    fresh = a4_linkability("S3", resp, 39, 50, seed=0, epsilon=0.5, n_features=47)
    assert fresh["hit1"] < 0.05  # independent releases at ε = 0.5 are near chance
    strong = a4_linkability("S3", resp, 39, 50, seed=0, epsilon=400.0, n_features=47)
    assert strong["hit1"] > 0.95  # almost no noise: linkable again


def test_a6_measures_what_requests_reveal() -> None:
    rng = np.random.default_rng(1)
    n = 6000
    label = (rng.random(n) < 0.1).astype(np.int8)
    cands = pl.DataFrame(
        {
            "member": np.zeros(n, dtype=np.int32),
            "account": np.arange(n, dtype=np.uint64),
            "window": np.full(n, 40, dtype=np.int32),
            "prob": np.full(n, 0.05),  # the responder's own score says nothing
        }
    )
    asked = np.nonzero(label == 1)[0][: int(label.sum() * 0.8)]  # peers ask about positives
    inbound = pl.DataFrame(
        {
            "member": np.zeros(len(asked), dtype=np.int32),
            "account": asked.astype(np.uint64),
            "window": np.full(len(asked), 40, dtype=np.int32),
            "bucket": np.full(len(asked), 3, dtype=np.int8),
        }
    )
    r = a6_query_leakage(cands, label, np.ones(n, dtype=bool), inbound, seed=0)
    att = r["attack"]
    assert att["own"]["auc"]["estimate"] == pytest.approx(0.5, abs=0.05)
    assert att["own+requests"]["auc"]["estimate"] > 0.8
    assert att["gain_tpr_0.01"]["estimate"] > 0.5
    assert r["positives_asked_share"] > r["asked_share"]


@pytest.mark.parametrize(
    ("row", "label"),
    [
        ({"cyc3": 1}, "cycle"),
        ({"sg_out_max": 4}, "scatter-gather"),
        ({"sg_in_max": 3}, "gather-scatter"),
        ({"fan_out": 6, "fan_in": 1}, "fan-out"),
        ({"fan_in": 7, "fan_out": 0}, "fan-in"),
        ({"pass_through": 0.9}, "pass-through"),
        ({}, "unknown"),
    ],
)
def test_placeholder_attribution_rules(row: dict[str, float], label: str) -> None:
    assert attribute(row)[0] == label


def test_token_budgets_are_sized_per_dataset() -> None:
    assert token_budget("HI-Medium") == 74_510 and token_budget("LI-Medium") == 87_580
    assert token_budget("FIXTURE-Small") == QUERY_BUDGET


def _ci(e: float) -> dict[str, float]:
    return {"estimate": e, "low": e - 0.05, "high": e + 0.05}


def test_g2_summary_and_page() -> None:
    r = {
        "summary": {
            "S2/stacker": {"linked": _ci(0.7), "linked_gain": {"difference": _ci(0.5), "p": 0.0}},
            "S3[eps=2]/stacker": {"linked": _ci(0.69)},
            "H1b": {
                "oracle-relational": {"S2/stacker": _ci(0.9)},
                "oracle": {"S2/stacker": _ci(1.1)},
            },
            "H1d": {
                "S1": {"gain_share_of_S2": _ci(0.95)},
                "PD[tau=3]": {"gain_share_of_S2": _ci(0.9), "disclosure_share_of_S2": 0.1},
            },
        },
        "random": {"linked": {"estimate": 0.0}},
        "per_seed": [{"protocol": {"S1": {"service_refused": 0}}}],
        "audit": {
            "H1c": {"S1_and_S3_le2_within": True, "S4_above_S2": {"A2": True, "A3": False}},
            "A1": {
                "pooled": {"hash": 0.42},
                "ratio_hash_to_oprf_protocol": 11.0,
                "mechanism_check": {"checked": 200, "oprf_matches": 200, "hash_matches": 200},
            },
            "A4": {"S2": {"hit1": 0.3, "chance_hit1": 0.01}},
        },
    }
    s = summarise("HI-Medium", "week09", r)
    assert s["h1a_met"] and s["h1b_met"] and s["h1c_met"] and s["pt2_met"]
    assert s["risk_ldp_ok"] and s["risk_oprf_ok"] and s["risk_attacks_ok"]
    page = render_g2([s])
    assert "Gate G2 evidence" in page and "HI-Medium (artifacts week09)" in page
    assert "No HI-Medium" in render_g2([])
