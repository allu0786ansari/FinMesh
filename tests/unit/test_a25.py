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
    fixture_paths: Any,
    ingested: object,
    monkeypatch: pytest.MonkeyPatch,
    data_env: Path,
    capsys: pytest.CaptureFixture[str],
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
    # The command saves its result (the stamp is frozen) and reuses the finished seed.
    from finmesh.cli import main

    assert main(["flag-frontier", "--dataset", fixture_paths.name, "--seeds", "0",
                 "--reps", "50"]) == 0  # fmt: skip
    assert "kept from flag_frontier_FIXTURE-Small_seed0.pkl" in capsys.readouterr().out
    assert (data_env / "artifacts" / "a25" / "flag_frontier_FIXTURE-Small.json").exists()
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
    # N4: the model selects at most four fields; a longer citation list is cut to four.
    c0 = r["cases"][0]
    shown = [e["field"] for e in nar.shown(c0)]
    reply = _json.loads(c0["first"]["raw"])
    reply["cited_fields"] = shown + shown
    long = {**r, "cases": [{**c0, "first": {**c0["first"], "raw": _json.dumps(reply)}}]}
    f0 = select_then_template(long, load_catalogue())["cases"][0]["first"]
    assert len(shown) > 4 and f0["cited_fields"] == shown[:4] and f0["cites_ok"]
    again = run_cases(bundle, lambda *_: (_ for _ in ()).throw(AssertionError), "fake:1b", ckpt)
    assert len(again["cases"]) == 20  # resumed from the checkpoint, no new call
    assert nar.PROTOCOLS[-1] == "A25N"


@pytest.fixture()
def keep_access_log(fixture_paths: Any) -> Any:
    """This module sorts before the tests that expect a fresh sealed-test log."""
    from finmesh.eval.sealed import access_log_path

    path = access_log_path(fixture_paths)
    saved = path.read_bytes() if path.exists() else None
    yield
    if saved is None:
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(saved)


def test_large_runner_extras_flag_noart_and_case_quality(
    fixture_paths: Any,
    ingested: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    keep_access_log: None,
) -> None:
    from finmesh.eval.budgets import Budget
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.sealed import read_access_log
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.training import sealed_runs, x1

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    build_features(fixture_paths, "B8", view="pooled")
    monkeypatch.setattr(x1, "PRIMARY", Budget("per_1000_per_day", 300.0))
    monkeypatch.setattr(x1, "AE_SAMPLE", 3000)
    monkeypatch.setattr(sealed_runs, "test_dir", lambda p, o: tmp_path / "test")
    before = len(read_access_log(fixture_paths))
    r = sealed_runs.run_x1_test(
        fixture_paths,
        headline_seeds=(0,),
        other_seeds=(0,),
        reps=50,
        window_reps=20,
        x6=False,
        allow_repeat=True,
        flags=("S1F[eps=2]",),
    )
    s = r["summary"]
    assert "S1F[eps=2]/stacker" in s and r["flags"] == ["S1F[eps=2]"]
    fc = s["flag_check"]["S1F[eps=2]"]
    assert fc["within_margin"] in (True, False, None) and "estimate" in fc["share_of_S1_gain"]
    cq = s["case_quality"]
    assert {"S0", "S2/stacker"} <= set(cq["configurations"])
    c0 = cq["configurations"]["S2/stacker"]  # the fixture's test holds one undetected scheme
    assert c0["completeness"] is None or 0 < c0["completeness"] <= 1
    assert c0["workload_alerts_per_linked_scheme"] > 0

    n = sealed_runs.run_x1_test(
        fixture_paths,
        other_seeds=(0,),
        reps=50,
        window_reps=20,
        allow_repeat=True,
        feature_set="no_artefacts",
    )
    assert n["feature_set"] == "no_artefacts" and not n["sweeps"] and n["audit"] is None
    assert set(n["per_seed"][0]["linked"]) == set(sealed_runs.NOART_CONFIGS)
    log = read_access_log(fixture_paths)[before:]
    assert [e["purpose"].startswith("week 18: X1") for e in log] == [True, True]
    assert len({e["config_hash"] for e in log}) == 2  # the artefact-free track opens separately
    assert (tmp_path / "test" / "x1noart_seed0.pkl").exists()

    # P4: the adaptive budget replays the saved run (validation history recorded by it).
    from finmesh.training import budget_replay

    rp = budget_replay.run_budget_replay(fixture_paths, recompute_validation=False)
    v = rp["seeds"][0]
    assert v["with_validation_history"] and v["adaptive"]["bank_epochs"] > 0
    assert v["adaptive"]["share_refused"] <= v["frozen"]["share_refused"] + 1e-12
    assert "A1" in v and "ratchet" in v["A1"]
    assert "Ratchet" in budget_replay.render(rp)
    recorded = budget_replay.as_use(_ckpt(tmp_path)["token_use_val"])
    assert budget_replay.validation_token_use(fixture_paths, "B8", 0) == recorded  # week-18 path
    assert len(read_access_log(fixture_paths)) == before + 2  # the replay opens nothing


def _ckpt(tmp_path: Path) -> dict[str, Any]:
    import pickle

    with (tmp_path / "test" / "x1_seed0.pkl").open("rb") as f:  # this test's own checkpoint
        return pickle.load(f)  # type: ignore[no-any-return]


def test_adaptive_budget_rule_refusals_and_ratchet() -> None:
    from finmesh.training.budget_replay import adaptive_budgets, ratchet, replay

    use = {(0, 1): 50, (0, 2): 180, (0, 3): 60, (1, 2): 10}
    b = adaptive_budgets(use, floor=100)
    assert b == {(0, 1): 100, (0, 2): 100, (0, 3): 360, (1, 2): 100}
    assert adaptive_budgets(use, 100, cap=200)[(0, 3)] == 200
    rows = [
        {"adversary": 0, "targets": 10, "candidates": 1000, "hash": 0.5, "legit_queries": 60},
        {"adversary": 1, "targets": 10, "candidates": 1000, "hash": 0.5, "legit_queries": 10},
    ]
    r = replay({(0, 2): 180, (0, 3): 60, (1, 2): 10}, {(0, 1): 50}, 100, rows)
    # Frozen: bank 0 epoch 2 asks 180 of 100 -> 80 refused of 250.
    assert abs(r["frozen"]["share_refused"] - 80 / 250) < 1e-12
    # Adaptive: epoch 2 budget = max(100, 2 x 50) = 100 -> still 80 refused; epoch 3: 360.
    assert r["adaptive"]["bank_epochs_over"] == 1
    # A1: adversary 0's best epoch under adaptive has 360 - 60 = 300 spare -> 0.5 x 0.3.
    assert abs(r["A1"]["adaptive"]["oprf"] - (0.5 * 0.3 + 0.5 * 0.09) / 2) < 1e-12
    rt = ratchet(rows, floor=100)
    assert rt["epochs_to_every_candidate"] == 4  # 100 x 2^4 = 1,600 >= 1,060
    assert rt["steps"][4]["ratio"] == 1.0  # hashing level: PT2 gone
    assert ratchet(rows, floor=100, cap=400)["epochs_to_every_candidate"] is None


def test_benchmark_day_split_rule() -> None:
    from finmesh.data.benchmark_split import day_split

    assert day_split([10] * 10) == (6, 8)  # 60/20/20 exactly
    i, j = day_split([100] * 15 + [5] * 3)  # a sparse tail stays in test
    assert (i, j) == (9, 12)


def test_benchmark_dataset_and_runner(
    fixture_paths: Any, ingested: object, fixture_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finmesh.data.benchmark_split import link_benchmark
    from finmesh.data.pipeline import ingest_dataset
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.split_io import load_plan
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.paths import dataset_paths
    from finmesh.training import benchmark

    link_benchmark(fixture_root / "raw", fixture_paths.name)
    full = dataset_paths(fixture_paths.name + "-FULL", root=fixture_root)
    ingest_dataset(full)
    g0 = run_g0(full)
    plan = load_plan(full)
    assert [p.name for p in plan.periods] == ["train", "gap", "val", "gap", "test"]
    assert plan.period("gap").start == plan.period("gap").end  # no gaps
    assert g0["observation_window"]["rows_after"] == 0  # every transaction is in
    build_universe(full, "B8")
    build_features(full, "B8")
    build_features(full, "B8", view="pooled")
    r = benchmark.run_benchmark(full, seeds=(0, 1), negative_rate=0.5)
    assert r["rows"]["test"]["rows"] > 0 and r["rows"]["test"]["missing_account_windows"] == 0
    for m in ("A", "B"):
        x = r["models"][m]
        assert 0 <= x["test_f1_mean"] <= 100 and len(x["per_seed"]) == 2
    assert r["adequacy"]["reference_f1"] is None  # the fixture has no published numbers
    assert "pooled detector" in benchmark.render(r)
    assert "published" in benchmark.render_table([r])


def test_best_f1_threshold() -> None:
    import numpy as np

    from finmesh.training.benchmark import best_f1, f1_at

    y = np.array([1, 0, 1, 0, 0, 1])
    s = np.array([0.9, 0.8, 0.7, 0.3, 0.3, 0.1])
    f1, thr = best_f1(y, s)
    assert abs(f1 - 2 / 3) < 1e-12 and thr == 0.7  # top 3: tp 2 of 3 flagged, 2 of 3 positives
    assert abs(f1_at(y, s, thr) - f1) < 1e-12


def test_plus_track_validation_and_test(
    fixture_paths: Any,
    ingested: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    data_env: Path,
    keep_access_log: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from finmesh.cli import main
    from finmesh.eval.budgets import Budget
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.sealed import read_access_log
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.training import sealed_runs, txdetector, x1

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    build_features(fixture_paths, "B8", view="pooled")
    monkeypatch.setattr(x1, "PRIMARY", Budget("per_1000_per_day", 300.0))
    monkeypatch.setattr(x1, "AE_SAMPLE", 3000)
    monkeypatch.setattr(txdetector, "NEGATIVE_RATE", 0.5)

    # Validation: S0+, S2+, oracle+ through the command, next to the current detector.
    assert main(["plus-validation", "--dataset", fixture_paths.name, "--seeds", "0",
                 "--reps", "50", "--window-reps", "20"]) == 0  # fmt: skip
    out = capsys.readouterr().out
    assert "+ (transaction detector)" in out and "current (account-window LightGBM)" in out
    assert "peak token use" in out

    # The A16 budget was sized on the current detector's traffic: the + track is served in
    # full on validation (as at test), so a budget it exceeds does not stop it.
    monkeypatch.setattr(x1, "token_budget", lambda _name: 1)
    assert main(["plus-validation", "--dataset", fixture_paths.name, "--seeds", "0",
                 "--reps", "50", "--window-reps", "20", "--no-compare"]) == 0  # fmt: skip
    monkeypatch.undo()
    monkeypatch.setattr(x1, "PRIMARY", Budget("per_1000_per_day", 300.0))
    monkeypatch.setattr(x1, "AE_SAMPLE", 3000)
    monkeypatch.setattr(txdetector, "NEGATIVE_RATE", 0.5)
    monkeypatch.setenv("FINMESH_DATA", str(data_env))

    # The scorer covers every account-window it is asked about (no missing rows).
    t, _ = x1._train(fixture_paths, "B8", 0, False, lambda _p: None, detector="tx")
    assert isinstance(t.fn, txdetector.TableScorer) and t.fn.missing == 0
    assert t.fn.detector.models and -1 in t.oracle.detector.models

    # Test: its own experiment, opening and checkpoint.
    monkeypatch.setattr(sealed_runs, "test_dir", lambda p, o: tmp_path / "test")
    before = len(read_access_log(fixture_paths))
    r = sealed_runs.run_x1_test(
        fixture_paths, other_seeds=(0,), reps=50, window_reps=20, allow_repeat=True,
        detector="tx",
    )  # fmt: skip
    assert r["detector"] == "tx" and r["audit"] is None and not r["sweeps"]
    assert set(r["per_seed"][0]["linked"]) == set(sealed_runs.PLUS_CONFIGS)
    log = read_access_log(fixture_paths)[before:]
    assert len(log) == 1 and (tmp_path / "test" / "x1plus_seed0.pkl").exists()
    assert sealed_runs.x1_config(fixture_paths, "B8", False, detector="tx")["experiment"] == (
        "X1-plus"
    )


def test_preflight_reads_the_a25_plan_for_large_windows(tmp_path: Path) -> None:
    from finmesh.eval.test_plan import A25_PLAN, PLAN, frozen_commit, plan_for
    from finmesh.paths import dataset_paths

    assert plan_for(dataset_paths("HI-Large-W16", root=tmp_path)) == A25_PLAN
    assert plan_for(dataset_paths("HI-Medium", root=tmp_path)) == PLAN
    doc = tmp_path / "plan.md"
    doc.write_text("**Frozen commit (before any Large opening):** —\\n")
    assert frozen_commit(doc) is None
    doc.write_text("**Frozen commit (before any Large opening):** `abc1234`\\n")
    assert frozen_commit(doc) == "abc1234"
    doc.write_text("**Frozen commit:** 0123abcd\\n")
    assert frozen_commit(doc) == "0123abcd"
