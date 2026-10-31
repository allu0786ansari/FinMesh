"""Week 14 (A21): the coverage curve and the constrained narrative with its grounding test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest

from finmesh.attribution import narrative as nar
from finmesh.attribution.narrative import (
    UNATTRIBUTED,
    bucket_range,
    build_case,
    build_prompt,
    check_reply,
    narrate,
    numbers_in,
    risk_coverage,
    selective_threshold,
    stratified_sample,
    summarise,
    template_narrative,
)
from finmesh.data.consortium import ConsortiumSpec, build_membership
from finmesh.training.x6 import attribute, load_catalogue


# --------------------------------------------------------------------------- coverage
def _sizes() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "bank": list(range(12)),
            "accounts": [400, 200, 120, 80, 60, 50, 40, 20, 10, 10, 5, 5],
            "tx_touching": [0] * 12,
        }
    )


def test_coverage_spec_parses_and_rejects() -> None:
    spec = ConsortiumSpec.parse("B8c50")
    assert (spec.option, spec.k, spec.coverage, spec.name) == ("B", 8, 50, "B8c50")
    assert ConsortiumSpec.parse("B8").coverage is None and ConsortiumSpec.parse("B8").name == "B8"
    for bad in ("A8c50", "B8c0", "B8c100", "B8cx", "B1c50"):
        with pytest.raises(ValueError):
            ConsortiumSpec.parse(bad)


def test_coverage_takes_largest_banks_until_the_share_is_reached() -> None:
    sizes = _sizes()
    total = sizes["accounts"].sum()
    for p, banks in ((10, {0}), (50, {0, 1}), (75, {0, 1, 2, 3}), (90, {0, 1, 2, 3, 4, 5})):
        m = build_membership(sizes, ConsortiumSpec.parse(f"B8c{p}"))
        assert set(m["bank"].to_list()) == banks, p
        held = sizes.filter(pl.col("bank").is_in(list(banks)))["accounts"].sum()
        assert held / total >= p / 100  # the last bank added crosses the target
        assert m["member"].n_unique() <= 8
    full = build_membership(sizes, ConsortiumSpec.parse("B8"))
    assert full.height == 12 and full["member"].n_unique() == 8


def _x1(linked_s0: float, linked_s2: float) -> dict[str, Any]:
    def ci(v: float) -> dict[str, float]:
        return {"estimate": v, "low": v - 0.01, "high": v + 0.01}

    s: dict[str, Any] = {
        k: {"linked": ci(v)}
        for k, v in (
            ("S0", linked_s0),
            ("S1/stacker", linked_s2 - 0.01),
            ("S2/stacker", linked_s2),
            ("S4/stacker", linked_s2),
            ("propagation", linked_s2),
            ("oracle-relational", linked_s2 + 0.1),
        )
    }
    s["S2/stacker"]["linked_gain"] = {"difference": ci(linked_s2 - linked_s0)}
    s["H1b"] = {"oracle-relational": {"S2/stacker": ci(0.8)}}
    return {"result": {"summary": s}}


def test_coverage_collects_orders_and_renders(tmp_path: Path) -> None:
    from finmesh.eval.coverage import collect, coverage_figure, render_coverage

    art, pq = tmp_path / "art", tmp_path / "pq"
    art.mkdir()
    for option, accounts, s0, s2 in (("B8", 1000, 0.2, 0.6), ("B8c50", 520, 0.1, 0.3),
                                     ("A64", 50, 0.0, 0.01)):  # fmt: skip
        tag = "DS" if option == "B8" else f"DS_{option}"
        (art / f"x1_{tag}.json").write_text(json.dumps(_x1(s0, s2)))
        meta = pq / f"eval_w6_{option}" / "meta.json"
        meta.parent.mkdir(parents=True)
        val = {"accounts": accounts, "schemes": 500, "multi_member_schemes": accounts // 2}
        meta.write_text(json.dumps({"counts": {"val": val}}))
    rows = collect("DS", art, pq)
    assert [r["option"] for r in rows] == ["A64", "B8c50", "B8"]
    assert rows[1]["account_share"] == pytest.approx(0.52) and rows[1]["target"] == 50
    fig = coverage_figure(rows, "DS", tmp_path / "c.png")
    assert fig is not None and fig.exists()
    page = render_coverage(rows, "DS", fig.name)
    assert "Not yet run: B8c10, B8c25, B8c75, B8c90." in page and "52.0%" in page


# --------------------------------------------------------------------------- abstention and sample
def test_selective_threshold_is_the_smallest_qualifying_tau() -> None:
    rng = np.random.default_rng(0)
    conf = rng.uniform(0.0, 0.6, 2000)
    correct = rng.random(2000) < conf  # calibrated: accuracy above tau is about (tau + 0.6) / 2
    tau = selective_threshold(conf, correct)
    assert tau is not None and 0.35 <= tau <= 0.45
    grid = {r["tau"]: r for r in risk_coverage(conf, correct)}
    assert grid[tau]["selective_accuracy"] >= 0.5 and grid[tau]["coverage"] >= 0.1
    assert selective_threshold(conf, np.zeros(2000, dtype=bool)) is None  # never accurate
    assert selective_threshold(np.full(50, 0.2), np.ones(50, dtype=bool)) is None  # coverage


def test_stratified_sample_caps_patterns_then_fills() -> None:
    ids = np.arange(1000, 1300)
    pats = np.array(["A"] * 200 + ["B"] * 80 + ["C"] * 20)
    idx = stratified_sample(ids, pats, n=60, per_pattern=15, seed=0)
    assert len(idx) == 60 and len(set(idx.tolist())) == 60
    got = pats[idx]
    assert (got == "C").sum() >= 15 and (got == "B").sum() >= 15
    assert np.array_equal(idx, stratified_sample(ids, pats, n=60, per_pattern=15, seed=0))
    small = stratified_sample(ids[:10], pats[:10], n=200)
    assert len(small) == 10  # fewer schemes than n: all of them


def test_bucket_ranges_follow_the_bucket_rule() -> None:
    edges = (1.0, 2.0, 3.0, 5.0, 10.0, 20.0)
    assert bucket_range(0, edges) == "below 1"
    assert bucket_range(3, edges) == "at least 3, below 5"
    assert bucket_range(6, edges) == "20 or more"
    assert bucket_range(7, edges) == "not reported"
    assert bucket_range(None, edges) == "no record from another member"
    assert bucket_range(2, (0.2, 0.5, 0.8, 0.95)) == "at least 0.5, below 0.8"


# --------------------------------------------------------------------------- prompt and checks
def _row() -> dict[str, Any]:
    row: dict[str, Any] = {
        "scheme_id": 7,
        "pattern": "FAN-OUT",
        "own_accounts": 3,
        "own_rows": 4,
        "own_span": 2,
        "own_max_fan_out": 12.0,
        "own_max_fan_in": 1.0,
        "own_mean_pass_through": 0.9123,
        "own_max_cyc2": 0.0,
        "own_max_cyc3": float("nan"),
        "own_max_amt_out": 15234.6,
        "n_accounts": 9,
        "n_members": 3,
        "n_rows": 11,
        "span": 4,
        "rec_max_c_fan_out": 4.0,
        "rec_max_c_pass_through": 3.0,
    }
    return row


CLASSES = [e["id"] for e in load_catalogue()["entries"]]


def _proba(top: str, p: float) -> np.ndarray:
    v = np.full(len(CLASSES), (1 - p) / (len(CLASSES) - 1))
    v[CLASSES.index(top)] = p
    return v


def test_case_shows_label_only_above_tau_and_actions_come_from_the_catalogue() -> None:
    cat = load_catalogue()
    entries = {e["id"]: e for e in cat["entries"]}
    case = build_case(_row(), CLASSES, _proba("FAN-OUT", 0.7), 0.5, cat, 6)
    assert (
        case["assigned"] == "FAN-OUT"
        and case["review_actions"] == entries["FAN-OUT"]["review_actions"]
    )
    ev = {e["field"]: e["value"] for e in case["evidence"]}
    assert ev["own_span_hours"] == "12" and ev["case_span_hours"] == "24"  # windows x 6 h
    assert ev["own_mean_pass_through"] == "0.91" and ev["own_max_amount_out"] == "15,235"
    assert ev["own_max_cycles"] == "0"  # NaN ignored, max of the rest
    assert ev["own_max_gather_scatter"] == "not available"
    assert ev["others_fan_out"] == "at least 5, below 10"
    prompt = build_prompt(case, cat)
    assert '"FAN-OUT"' in prompt and "[others_fan_out]" in prompt
    assert "CYCLE (" not in prompt  # only the assigned entry as context
    low = build_case(_row(), CLASSES, _proba("CYCLE", 0.3), 0.5, cat, 6)
    assert low["assigned"] == UNATTRIBUTED and len(low["candidates"]) == 3
    assert low["review_actions"][0] == entries["CYCLE"]["review_actions"][0]
    p2 = build_prompt(low, cat)
    assert UNATTRIBUTED in p2 and "CYCLE (" in p2
    none = build_case(_row(), CLASSES, _proba("CYCLE", 0.9), None, cat, 6)
    assert none["assigned"] == UNATTRIBUTED  # no qualifying tau: never labelled


def test_check_reply_measures_each_part_of_grounding() -> None:
    fields = ["own_max_fan_out", "case_accounts"]
    known = numbers_in("fan-out 12, accounts 9, amount 15,235 and share 0.91")
    good = json.dumps(
        {
            "typology_id": "FAN-OUT",
            "cited_fields": ["own_max_fan_out"],
            "narrative": "One account paid 12 payees; 9 accounts and 15,235 moved, 0.91 passed on.",
        }
    )
    c = check_reply(good, "FAN-OUT", fields, known)
    assert c["grounded"] and c["numeric"] and c["cites_any"]
    assert not check_reply(good, "CYCLE", fields, known)["grounded"]  # wrong typology
    invented = json.loads(good) | {"cited_fields": ["own_max_fan_out", "customer_name"]}
    assert not check_reply(json.dumps(invented), "FAN-OUT", fields, known)["grounded"]
    extra = json.loads(good) | {"narrative": "About 13 payees received 20,000."}
    e = check_reply(json.dumps(extra), "FAN-OUT", fields, known)
    assert e["grounded"] and not e["numeric"]  # numbers are reported, not part of H3b
    assert not check_reply("not json", "FAN-OUT", fields, known)["json"]
    assert not check_reply("[1, 2]", "FAN-OUT", fields, known)["json"]
    assert numbers_in("S2 and FAN-OUT in 2 of 3 banks, 1,250.5") == {2.0, 3.0, 1250.5}


class FakeModel:
    """Scripted replies; records the format of each call."""

    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = list(replies)
        self.formats: list[Any] = []

    def __call__(self, prompt: str, fmt: dict[str, Any] | str) -> str:
        self.formats.append(fmt)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _good(case: dict[str, Any], text: str = "Accounts were linked across banks.") -> str:
    return json.dumps(
        {"typology_id": case["assigned"], "cited_fields": ["case_accounts"], "narrative": text}
    )


def test_narrate_retries_once_with_the_schema_then_falls_back() -> None:
    cat = load_catalogue()
    case = build_case(_row(), CLASSES, _proba("FAN-OUT", 0.7), 0.5, cat, 6)
    ok = narrate(case, cat, FakeModel([_good(case)]))
    assert ok["final_source"] == "first" and ok["retry"] is None and ok["first"]["grounded"]
    fake = FakeModel(["{bad", _good(case)])
    fixed = narrate(case, cat, fake)
    assert fixed["final_source"] == "retry" and fake.formats[0] == "json"
    schema = fake.formats[1]
    assert schema["properties"]["typology_id"]["enum"] == ["FAN-OUT"]
    assert "case_accounts" in schema["properties"]["cited_fields"]["items"]["enum"]
    down = narrate(case, cat, FakeModel([TimeoutError("slow"), OSError("refused")]))
    assert down["final_source"] == "template" and len(down["errors"]) == 2
    assert down["narrative"] == template_narrative(case) and down["final_numeric"]
    una = build_case(_row(), CLASSES, _proba("CYCLE", 0.3), 0.5, cat, 6)
    t = template_narrative(una)
    assert "unattributed" in t and "CYCLE" in t


def test_summary_rates_and_h3b() -> None:
    cat = load_catalogue()
    cases = []
    for i in range(20):
        case = build_case(_row() | {"scheme_id": i}, CLASSES, _proba("FAN-OUT", 0.7), 0.5, cat, 6)
        replies: list[str | Exception] = [_good(case)] if i else ["{bad", "{bad"]
        cases.append(narrate(case, cat, FakeModel(replies)))
    s = summarise(cases)
    assert s["H3b"]["grounding"]["estimate"] == pytest.approx(0.95)
    assert s["H3b"]["met_on_validation"] and s["fallback_rate"] == pytest.approx(0.05)
    assert s["attributed"]["accuracy"] == 1.0 and s["by_pattern"]["FAN-OUT"]["cases"] == 20
    assert s["latency_s"]["p95"] is not None


# --------------------------------------------------------------------------- X6 hooks and driver
def _table(n: int = 240) -> pl.DataFrame:
    rng = np.random.default_rng(0)
    pats = np.array(["FAN-IN", "FAN-OUT", "CYCLE"])[rng.integers(0, 3, n)]
    base = {"FAN-IN": (8, 1, 0), "FAN-OUT": (1, 8, 0), "CYCLE": (2, 2, 3)}
    data: dict[str, object] = {
        "scheme_id": np.arange(n),
        "pattern": pats,
        "fold": (np.arange(n) >= n // 2).astype(np.int8),
        "incident": [None if i % 10 == 0 else i for i in range(n)],
        "own_accounts": rng.integers(1, 5, n).astype(float),
        "own_rows": rng.integers(1, 9, n).astype(float),
        "own_span": rng.integers(1, 4, n).astype(float),
        "own_mean_pass_through": rng.random(n),
        "n_accounts": rng.integers(2, 12, n).astype(float),
        "n_members": rng.integers(1, 4, n).astype(float),
        "n_rows": rng.integers(2, 20, n).astype(float),
        "span": rng.integers(1, 6, n).astype(float),
    }
    for j, c in enumerate(("fan_in", "fan_out", "cyc2")):
        data[f"own_max_{c}"] = [base[p][j] + rng.random() for p in pats]
    for c in ("gs_min_fan", "cyc3", "cyc4", "sg_out_max", "sg_in_max"):
        data[f"own_max_{c}"] = rng.random(n)
    return pl.DataFrame(data)


def test_attributor_probabilities_match_its_predictions() -> None:
    t = _table()
    proba: dict[str, Any] = {}
    preds = attribute(t, "S1", 0, load_catalogue(), proba)
    det = t["incident"].is_not_null().to_numpy()
    p = proba["p"]
    assert proba["classes"] == CLASSES and p.shape == (t.height, len(CLASSES))
    assert np.isnan(p[~det]).all() and np.allclose(p[det].sum(axis=1), 1)
    top = np.array(CLASSES, dtype=object)[p[det].argmax(axis=1)]
    assert (top == preds["attributor"][det]).all()
    assert (
        attribute(t, "S1", 0, load_catalogue())["attributor"].tolist()
        == preds["attributor"].tolist()
    )


def test_run_narrative_end_to_end_with_a_fake_model(
    monkeypatch: pytest.MonkeyPatch, fixture_paths: object, ingested: object
) -> None:
    from finmesh.attribution.narrative_report import render_narrative, write_cases
    from finmesh.eval.g0 import run_g0

    run_g0(fixture_paths)  # type: ignore[arg-type]  (writes the split plan)
    t = _table()
    proba: dict[str, Any] = {}
    attribute(t, "S2", 0, load_catalogue(), proba)

    def fake_x6(*_: Any, **kw: Any) -> dict[str, Any]:
        assert kw["levels"] == ("S2",) and kw["keep_tables"]
        return {"tables": {"S2": {"table": t, **proba}}}

    monkeypatch.setattr("finmesh.training.x6.run_seed_x6", fake_x6)

    def model(prompt: str, fmt: Any) -> str:
        assigned = (
            UNATTRIBUTED
            if "UNATTRIBUTED" in prompt
            else prompt.split('"typology_id" to "')[1].split('"')[0]
        )
        return json.dumps(
            {"typology_id": assigned, "cited_fields": ["case_members"], "narrative": "Linked."}
        )

    r = nar.run_narrative(fixture_paths, n=40, call=model)
    s = r["summary"]
    assert s["cases"] == 40 and s["H3b"]["grounding"]["estimate"] == 1.0
    assert r["selective"]["detected_schemes"] == 216 and r["selective"]["tau"] is not None
    assert {c["pattern"] for c in r["cases"]} == {"FAN-IN", "FAN-OUT", "CYCLE"}
    page = render_narrative(r)
    assert "H3b on validation" in page and "Example cases" in page
    out = write_cases(r, Path(str(fixture_paths.parquet)) / "cases.jsonl")  # type: ignore[attr-defined]
    assert len(out.read_text().splitlines()) == 40


def test_narrative_refuses_remote_endpoints() -> None:
    with pytest.raises(ValueError):
        nar.ollama_call("http://example.com:11434", "llama3.2:3b", 5)


def test_cli_has_the_week14_commands() -> None:
    from finmesh.cli import build_parser

    p = build_parser()
    a = p.parse_args(["narrative", "--dataset", "HI-Medium"])
    assert (a.n, a.model, a.url) == (200, "llama3.2:3b", "http://localhost:11434")
    assert p.parse_args(["coverage", "--dataset", "HI-Medium"]).func.__name__ == "cmd_coverage"


def test_narrative_fails_fast_when_ollama_is_down(fixture_paths: object) -> None:
    r = nar.run_narrative(fixture_paths, url="http://localhost:9", timeout=2)
    assert "error" in r and "ollama serve" in r["error"]
