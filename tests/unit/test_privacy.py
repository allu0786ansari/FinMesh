"""Week 8: S3 (local DP), progressive disclosure, the audit's metrics, the relational oracle."""

from __future__ import annotations

import math

import numpy as np
import polars as pl
import pytest

from finmesh.matching.tokens import TokenClient, TokenService, identifier
from finmesh.sharing.evidence import WIRE_FIELDS
from finmesh.sharing.ldp import (
    EPSILON_CAP,
    LDP_FIELDS,
    LdpReleaser,
    field_domains,
    k_rr,
    keep_probability,
)
from finmesh.sharing.messages import check
from finmesh.sharing.node import BankNode
from finmesh.sharing.requests import RequestGuard, RequestIssuer
from finmesh.training.audit import MARGIN, _bootstrap, _h1c, tpr_at_fpr
from finmesh.training.relational import neighbour_features, propagate

N_FEATURES = 47


def _client(service: TokenService, bank: int) -> TokenClient:
    return TokenClient(bank, lambda b, e, p: service.evaluate(b, e, p))


def _valid_wire(window: int, alert: bool) -> list[int]:
    dom = field_domains(N_FEATURES)
    v = []
    for f in WIRE_FIELDS:
        if f == "window":
            v.append(window)
        elif f == "alert":
            v.append(int(alert))
        else:
            v.append(dom[f][-1])  # the last value of every domain
    return v


def test_domains_cover_every_noised_field() -> None:
    dom = field_domains(N_FEATURES)
    assert set(dom) == set(LDP_FIELDS)
    assert len(LDP_FIELDS) == len(WIRE_FIELDS) - 2  # window and alert stay in the clear
    assert dom["dev0_direction"] == (-1, 1) and len(dom["dev0_feature"]) == N_FEATURES


def test_k_rr_keeps_the_true_value_at_the_stated_rate() -> None:
    rng = np.random.default_rng(0)
    dom = tuple(range(5))
    v = np.full(200_000, 3)
    for eps in (0.1, 1.0, 4.0):
        out = k_rr(v, dom, eps, rng)
        assert set(np.unique(out)) <= set(dom)
        p = keep_probability(eps, 5)
        assert np.mean(out == 3) == pytest.approx(p, abs=0.005)
        # the other values share the rest uniformly
        others = np.bincount(out[out != 3], minlength=5)[[0, 1, 2, 4]]
        assert others.std() / others.mean() < 0.05
        assert p == pytest.approx(math.exp(eps) / (math.exp(eps) + 4))
    with pytest.raises(ValueError):
        k_rr(np.array([7]), dom, 1.0, rng)


def test_releases_are_memoised_and_budgeted_per_account_epoch() -> None:
    wire = tuple(_valid_wire(5, True))
    rel = LdpReleaser(epsilon=4.0, n_features=N_FEATURES, seed=1)
    first = rel.release(0, account=9, epoch=0, wire=wire)
    assert first is not None and rel.release(0, 9, 0, wire) == first  # memoised: no new spend
    assert first[WIRE_FIELDS.index("window")] == 5 and first[WIRE_FIELDS.index("alert")] == 1
    assert rel.release(1, 9, 0, wire) is not None  # second record: 8 = cap
    assert rel.release(2, 9, 0, wire) is None and rel.withheld == 1  # over the cap
    assert rel.release(3, 9, 1, wire) is not None  # a new epoch has its own budget
    assert rel.max_account_epsilon == pytest.approx(EPSILON_CAP)


def _node(level: str, **kw: object) -> tuple[RequestIssuer, BankNode, TokenService]:
    service = TokenService(seed=b"\x05" * 32)
    issuer = RequestIssuer()
    rows = [_valid_wire(5, True), _valid_wire(9, False)]
    recs = pl.DataFrame(
        {
            "member": [1, 1],
            "account": [20, 20],
            **{f: [r[i] for r in rows] for i, f in enumerate(WIRE_FIELDS)},
        },
        schema_overrides={"account": pl.UInt64},
    ).with_columns(pl.col("alert").cast(pl.Boolean))
    node = BankNode(1, level, _client(service, 1), RequestGuard(1, issuer.public_key), recs, **kw)  # type: ignore[arg-type]
    node.build_index()
    return issuer, node, service


def test_s3_responses_are_noised_memoised_and_allowlisted() -> None:
    issuer, node, service = _node("S3", ldp=LdpReleaser(0.5, N_FEATURES, seed=3))
    token = _client(service, 0).tokens(0, [identifier(20)])[0]
    r1 = node.respond(issuer.issue(0, 1, token, 0, 0, 9, 3, now=9), now=9)
    r2 = node.respond(issuer.issue(0, 1, token, 0, 0, 9, 3, now=9), now=9)
    check(r1)
    assert r1.record is not None and r2.record is not None
    assert r1.record.values == r2.record.values  # the same release twice
    assert r1.alert and r1.alert_window == 5  # S1 content in the clear
    dom = field_domains(N_FEATURES)
    for f, v in zip(WIRE_FIELDS, r1.record.values, strict=True):
        if f in dom:
            assert v in dom[f]
    assert node.disclosed == {1}


@pytest.mark.parametrize(("bucket", "has_record"), [(1, False), (2, False), (3, True), (4, True)])
def test_pd_discloses_records_only_above_tau(bucket: int, has_record: bool) -> None:
    issuer, node, service = _node("PD", tau=3)
    token = _client(service, 0).tokens(0, [identifier(20)])[0]
    r = node.respond(issuer.issue(0, 1, token, 0, 0, 9, bucket, now=9), now=9)
    check(r)
    assert r.alert and r.alert_window == 5  # PD always gives the S1 answer
    assert (r.record is not None) is has_record
    assert len(node.disclosed) == int(has_record)
    assert node.inbound and node.inbound[-1][1] == bucket


def test_tpr_at_fpr_and_bootstrap() -> None:
    y = np.array([0] * 1000 + [1] * 100)
    s = np.concatenate([np.linspace(0, 1, 1000), np.linspace(0.995, 2, 100)])
    assert tpr_at_fpr(y, s, 0.01) == pytest.approx(1.0)
    assert tpr_at_fpr(y, np.zeros(1100), 0.01) == 0.0  # ties at the threshold never count
    assert math.isnan(tpr_at_fpr(np.zeros(5), np.zeros(5), 0.01))
    draws = _bootstrap(y, {"a": s, "b": -s}, np.arange(1100) // 2, reps=20)
    assert draws["a"]["tpr_0.01"].shape == (20,) and draws["b"]["auc"].max() < 0.1


def test_h1c_margin_rule() -> None:
    def res(high: float | None) -> dict[str, object]:
        return {
            "diff_tpr_0.01": {"estimate": 0.0, "low": -0.01, "high": high},
            "tpr_0.01": {"estimate": 0.01},
        }

    targets = ("A2_third_party", "A3_amount_top", "A3_fan_in_top", "A3_pass_through")
    attacks = {
        t: {
            "S1": res(0.02),
            "S3[eps=1]": res(MARGIN + 0.01 if t == "A3_amount_top" else 0.0),
            "S4": res(0.2),
            "S2": res(0.1),
            "S4_minus_S2_tpr_0.01": {"low": 0.01},
        }
        for t in targets
    }
    attacks["A3_pass_through"]["S1"] = res(None)  # not assessable
    h = _h1c(attacks, {"S1": "S1", "S3[eps=1]": "S3", "S4": "S4", "S2": "S2"})
    assert h["within_margin"]["S1"] is True  # assessable targets all within
    assert h["within_margin"]["S3[eps=1]"] is False
    assert h["S1_and_S3_le2_within"] is False
    assert h["not_assessable"] == ["A3_pass_through"]
    assert all(h["S4_above_S2"].values())


def test_relational_features_use_every_counterparty_in_the_lookback() -> None:
    keys = pl.DataFrame(
        {"member": [0, 1, 2, 1], "account": [1, 2, 3, 2], "window": [10, 10, 9, 5]},
        schema={"member": pl.Int32, "account": pl.UInt64, "window": pl.Int32},
    )
    prob = np.array([0.2, 0.6, 0.3, 0.9])
    alerted = np.array([False, True, False, True])
    edges = pl.DataFrame(
        {"src": [1, 3, 1], "dst": [2, 1, 9], "window": [10, 9, 2]},
        schema={"src": pl.UInt64, "dst": pl.UInt64, "window": pl.Int32},
    )
    f = neighbour_features(keys, prob, alerted, np.array([0]), edges, lookback=4)
    row = f.row(0, named=True)
    # account 2 (same window, alerted) and 3 (window 9) count; account 2's window 5 is
    # outside the lookback; the edge to 9 is too old.
    assert row["n_cp"] == 2 and row["n_cp_alert"] == 1
    assert row["max_cp_prob"] == pytest.approx(0.6) and row["sum_cp_prob"] == pytest.approx(0.9)
    assert row["own_logit"] == pytest.approx(math.log(0.2 / 0.8))
    assert propagate(f, 0.5)[0] == pytest.approx(0.2 + 0.3)
