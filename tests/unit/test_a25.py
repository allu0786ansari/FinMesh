"""Amendment A25: improvements confirmed on fresh data (Large windows)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest


def test_window_rule_ends_at_the_dense_period() -> None:
    from finmesh.data.window import choose_window

    daily = {date(2022, 9, d): 1000 for d in range(1, 21)}
    daily[date(2022, 9, 21)] = 10  # sparse tail
    daily[date(2022, 9, 22)] = 5
    assert choose_window(daily, 16) == (date(2022, 9, 5), date(2022, 9, 20))
    with pytest.raises(ValueError):
        choose_window(daily, 25)


def test_cut_window_on_the_fixture(fixture_paths: Any, fixture_truth: object) -> None:
    from finmesh.data.window import cut_window

    raw_root = Path(fixture_paths.raw).parent
    r = cut_window(raw_root, "FIXTURE-Small", days=6)
    assert r["dataset"] == "FIXTURE-Small-W6"
    assert r["window"] == ["2022-09-05", "2022-09-10"]
    dst = raw_root / "FIXTURE-Small-W6"
    lines = (dst / "FIXTURE-Small-W6_Trans.csv").read_text().splitlines()
    assert lines[0].startswith("Timestamp") and len(lines) - 1 == r["transactions"]
    assert all("2022/09/05" <= x[:10] <= "2022/09/10" for x in lines[1:])
    pat = (dst / "FIXTURE-Small-W6_Patterns.txt").read_text()
    body = [x for x in pat.splitlines() if x and not x.startswith(("BEGIN", "END"))]
    assert body and all("2022/09/05" <= x[:10] <= "2022/09/10" for x in body)
    assert pat.count("BEGIN") == pat.count("END") == r["pattern_blocks"]["kept"]
    assert (dst / "FIXTURE-Small-W6_accounts.csv").exists()
    assert json.loads((dst / "window.json").read_text())["transactions"] == r["transactions"]


def test_case_quality_columns() -> None:
    import polars as pl

    from finmesh.eval.schemes import scheme_outcomes

    # Scheme 1: accounts 1, 2, 3 (windows 10, 11, 12); scheme 2: accounts 7, 8; scheme 3 undetected.
    sw = pl.DataFrame(
        {
            "scheme_id": [1, 1, 1, 2, 2, 3],
            "member": [0, 1, 2, 0, 1, 0],
            "account": [1, 2, 3, 7, 8, 9],
            "window": [10, 11, 12, 20, 21, 30],
        }
    )
    schemes = pl.DataFrame(
        {
            "scheme_id": [1, 2, 3],
            "pattern": ["FAN-OUT", "CYCLE", "STACK"],
            "members": [3, 2, 1],
            "first_window": [10, 20, 30],
        }
    )
    alerts = sw.select("member", "account", "window").with_columns(
        pl.Series("alert", [True, True, True, True, True, False])
    )
    incidents = pl.DataFrame(
        {
            "member": [0, 1, 2, 0, 1],
            "account": [1, 2, 3, 7, 8],
            "window": [10, 11, 12, 20, 21],
            "incident": [100, 100, 101, 200, 201],  # scheme 1 split in two; scheme 2 unlinked
        }
    )
    out = scheme_outcomes(alerts, sw, schemes, 6, 12, incidents).sort("scheme_id")
    r = out.to_dicts()
    assert r[0]["linked"] and r[0]["completeness"] == pytest.approx(2 / 3)
    assert r[0]["fragmentation"] == 2 and r[0]["time_to_link_h"] == 6.0  # second account, window 11
    assert not r[1]["linked"] and r[1]["completeness"] == 0.5 and r[1]["time_to_link_h"] is None
    assert r[2]["completeness"] is None and not r[2]["detected"]
    plain = scheme_outcomes(alerts, sw, schemes, 6, 12)
    assert plain["completeness"].null_count() == 3


def _node(**kw: Any) -> Any:
    import numpy as np
    import polars as pl

    from finmesh.sharing.node import BankNode

    node = BankNode(1, "S1", None, None, pl.DataFrame(), **kw)  # type: ignore[arg-type]
    node._acct = np.arange(10_000, dtype=np.int64)
    return node


def _req(bucket: int = 4, epoch: int = 1, token: bytes = b"t" * 16) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(
        request_id="r", requester_bucket=bucket, epoch=epoch, token=token, window_hi=9
    )


def test_protected_flag_randomised_response_and_gate() -> None:
    import math

    # Large eps: the truth; a gate below the requester's bucket answers "no_record".
    sharp = _node(flag_eps=50.0)
    assert sharp._protected_flag(_req(), [5], True, 7).alert
    assert sharp._protected_flag(_req(), [6], False, -1).status == "no_record"
    gated = _node(flag_tau=3)
    assert gated._protected_flag(_req(bucket=2), [5], True, 7).status == "no_record"
    assert gated._protected_flag(_req(bucket=3), [5], True, 7).alert
    # eps = 1: the true bit is kept at rate e / (1 + e), memoised per account and epoch;
    # accounts without a record (token only) are randomised too.
    rr = _node(flag_eps=1.0)
    kept = sum(rr._protected_flag(_req(), [i], True, 7).alert for i in range(4000)) / 4000
    assert abs(kept - math.e / (1 + math.e)) < 0.03
    again = [rr._protected_flag(_req(), [i], True, 7).alert for i in range(50)]
    assert again == [rr._protected_flag(_req(), [i], True, 7).alert for i in range(50)]
    false_pos = sum(
        rr._protected_flag(_req(token=bytes([k % 256, k // 256]) * 8), [], False, -1).alert
        for k in range(4000)
    )
    assert abs(false_pos / 4000 - 1 / (1 + math.e)) < 0.03
    fake = next(
        r
        for k in range(200)
        if (r := rr._protected_flag(_req(token=bytes([k]) * 16), [], False, -1)).alert
    )
    assert fake.alert_window == 9  # a false flag carries the request's own time bucket


def test_flag_frontier_and_selection_on_the_fixture(
    fixture_paths: Any, ingested: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finmesh.eval.budgets import Budget
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.training import x1
    from finmesh.training.flags import candidates, run_flag_frontier, select_flag

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    build_features(fixture_paths, "B8", view="pooled")
    monkeypatch.setattr(x1, "PRIMARY", Budget("per_1000_per_day", 300.0))
    monkeypatch.setattr(x1, "AE_SAMPLE", 3000)
    r = run_flag_frontier(fixture_paths, seeds=(0,), reps=50, window_reps=20)
    assert set(r["candidates"]) == {"S1", *candidates()}
    assert r["candidates"]["S1"]["share_of_S1_gain"]["estimate"] == 1.0
    for n in candidates():
        assert isinstance(r["candidates"][n]["within_margin"], bool)
    sel = select_flag([r, r])
    assert sel["chosen"] is None or sel["chosen"] in candidates()
    forced = {**r, "candidates": {**r["candidates"]}}
    for n in candidates():
        forced["candidates"][n] = {
            **r["candidates"][n],
            "within_margin": n.endswith("eps=2]"),
            "share_of_S1_gain": {"estimate": 0.9},
        }
    assert select_flag([forced])["chosen"] == "S1F[eps=2]"  # a tie goes to the ungated one


def test_narrative_export_run_and_select_then_template(
    monkeypatch: pytest.MonkeyPatch, fixture_paths: Any, ingested: object, tmp_path: Path
) -> None:
    import json as _json

    from finmesh.attribution import narrative as nar
    from finmesh.attribution.claims import scope_check
    from finmesh.attribution.narrative_cases import export_cases, run_cases, select_then_template
    from finmesh.attribution.narrative_report import render_narrative
    from finmesh.eval.g0 import run_g0
    from finmesh.training.x6 import attribute, load_catalogue
    from tests.unit.test_week14 import _table

    run_g0(fixture_paths)
    t = _table()
    proba: dict[str, Any] = {}
    attribute(t, "S2", 0, load_catalogue(), proba)
    tables = {lv: {"table": t, **proba} for lv in ("S0", "S2")}
    monkeypatch.setattr("finmesh.training.x6.run_seed_x6", lambda *a, **k: {"tables": tables})
    bundle = export_cases(fixture_paths, n=20, protocol="A25N")
    assert len(bundle["cases"]) == 20 and bundle["selective"]["tau"] is not None
    bundle = _json.loads(_json.dumps(bundle, default=str))  # what crosses to the notebook

    def model(prompt: str, fmt: Any) -> str:  # a model that confuses scope
        return _json.dumps(
            {
                "narrative": "Nine accounts at your bank moved money.",
                "cited_fields": ["case_accounts"],
                "typology_id": "UNATTRIBUTED",
            }
        )

    ckpt = tmp_path / "run.partial.json"
    r = run_cases(bundle, model, "fake:1b", ckpt)
    assert r["split"] == "val" and len(r["cases"]) == 20 and ckpt.exists()
    assert r["summary"]["first_scope_ok"] < 1.0  # the scope rule caught it
    assert all(not c["first"]["strict"] for c in r["cases"] if not c["first"]["scope_ok"])
    assert "Constrained case narrative" in render_narrative(r)
    n4 = select_then_template(r, load_catalogue())
    assert n4["design"] == "N4 select-then-template" and len(n4["cases"]) == 20
    for c in n4["cases"]:
        ev = {e["field"]: e["value"] for e in c["evidence"]}
        assert scope_check(c["narrative"], ev)["scope_ok"]
        assert c["final_consistent"]
    again = run_cases(bundle, lambda *_: (_ for _ in ()).throw(AssertionError), "fake:1b", ckpt)
    assert len(again["cases"]) == 20  # resumed from the checkpoint, no new call
    assert nar.PROTOCOLS[-1] == "A25N"
