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
        held = {"B8": 2000, "B8c50": 1000, "A64": 94}[option]  # all accounts held by members
        pl.DataFrame({"member": [0, 1], "accounts": [held // 2, held - held // 2]}).write_parquet(
            meta.parent / "accounts_per_member.parquet"
        )
    rows = collect("DS", art, pq)
    assert [r["option"] for r in rows] == ["A64", "B8c50", "B8"]
    assert rows[1]["account_share"] == pytest.approx(0.52) and rows[1]["target"] == 50
    assert rows[1]["held_share"] == pytest.approx(0.5) and rows[0]["held_share"] == pytest.approx(
        0.047
    )
    fig = coverage_figure(rows, "DS", tmp_path / "c.png")
    assert fig is not None and fig.exists()
    page = render_coverage(rows, "DS", fig.name)
    assert "Not yet run: B8c10, B8c25, B8c75, B8c90." in page and "52.0%" in page
    assert "4.7%" in page and "sets the budget" in page


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
    assert '"FAN-OUT"' in prompt and "others_fan_out = at least 5, below 10" in prompt
    assert "[" not in prompt.split("Evidence about this case:")[1]  # A22: no bracketed names
    assert "own_max_gather_scatter" not in prompt  # missing values are not shown
    assert "CYCLE (" not in prompt  # only the assigned entry as context
    assert "Red flags" not in prompt and "general reference" in prompt
    example = prompt.split("fictitious case:\n")[1].split("\n")[0]
    assert json.loads(example)["typology_id"] == "FAN-OUT"
    assert not any(ch.isdigit() for ch in example)  # the example cannot leak numbers
    assert (
        prompt.index('"narrative"')
        < prompt.index('"cited_fields"')
        < prompt.index('"typology_id" (exactly')
    )
    old = build_prompt(case, cat, "A21")  # the first run's prompt is kept unchanged
    assert "[others_fan_out]" in old and "Red flags" in old
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


def test_strict_grounding_adds_citations_numbers_and_typology_mentions() -> None:
    cat = load_catalogue()
    case = build_case(_row(), CLASSES, _proba("CYCLE", 0.3), 0.5, cat, 6)  # unattributed
    allowed = nar.allowed_typologies(case)
    assert allowed == {"CYCLE", "FAN-OUT", "FAN-IN"} or len(allowed) == 3
    fields = [e["field"] for e in nar.shown(case)]
    known = nar.evidence_numbers(case)
    assert 12.0 in known and 0.3 in known and 6.0 not in known  # evidence and confidences only

    def reply(text: str, cited: list[str]) -> dict[str, Any]:
        raw = json.dumps({"narrative": text, "cited_fields": cited, "typology_id": UNATTRIBUTED})
        return check_reply(raw, UNATTRIBUTED, fields, known, allowed, cat)

    ok = reply(
        "One account at your bank paid 12 payees; the analyst could check CYCLE.",
        ["own_max_fan_out"],
    )
    assert ok["grounded"] and ok["strict"]
    outside = reply("This looks like a gather-scatter scheme.", ["own_max_fan_out"])
    assert outside["grounded"] and not outside["strict"] and outside["named"] == ["GATHER-SCATTER"]
    many = reply("Linked accounts.", fields[:5])
    assert many["grounded"] and not many["cites_ok"] and not many["strict"]
    none = reply("Linked accounts.", [])
    assert none["grounded"] and not none["strict"]  # H3b allows no citation; strict does not
    sums = reply("Together they paid 13 payees.", ["own_max_fan_out"])
    assert sums["grounded"] and not sums["numeric"] and not sums["strict"]


def test_typology_mentions_follow_the_rule() -> None:
    cat = load_catalogue()
    named = nar.typologies_named
    assert named("a Fan Out then fan-in, then Scatter-Gather", cat) == {
        "FAN-OUT",
        "FAN-IN",
        "SCATTER-GATHER",
    }
    assert named("a bipartite layer and a CYCLE", cat) == {"BIPARTITE", "CYCLE"}
    assert named("a random stack of cycles; own_max_fan_out is high", cat) == set()
    assert named("gather-then-scatter fan", cat) == set()  # an evidence label, not a pattern


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
    assert schema["properties"]["cited_fields"]["maxItems"] == 4
    assert list(schema["properties"]) == ["narrative", "cited_fields", "typology_id"]
    # A22 retries on a strict failure: grounded but naming an outside typology.
    bad = json.dumps(
        {"typology_id": "FAN-OUT", "cited_fields": ["case_accounts"], "narrative": "A CYCLE."}
    )
    strict = narrate(case, cat, FakeModel([bad, _good(case)]))
    assert strict["first"]["grounded"] and strict["final_source"] == "retry"
    # A21 kept its rule: an H3b-grounded reply is accepted.
    loose = narrate(case, cat, FakeModel([bad]), protocol="A21")
    assert loose["final_source"] == "first"
    down = narrate(case, cat, FakeModel([TimeoutError("slow"), OSError("refused")]))
    assert down["final_source"] == "template" and len(down["errors"]) == 2
    assert down["narrative"] == template_narrative(case) and down["final_numeric"]
    assert down["final_mentions_ok"]
    una = build_case(_row(), CLASSES, _proba("CYCLE", 0.3), 0.5, cat, 6)
    t = template_narrative(una)
    assert "unattributed" in t and "CYCLE" in t
    assert nar.typologies_named(t, cat) <= nar.allowed_typologies(una)  # template is safe too


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
    s0 = t.with_columns(pl.col("own_max_fan_in") * 0, pl.col("own_max_fan_out") * 0)  # no signal
    proba0: dict[str, Any] = {}
    attribute(s0, "S0", 0, load_catalogue(), proba0)
    seen: list[tuple[str, ...]] = []

    def fake_x6(*_: Any, **kw: Any) -> dict[str, Any]:
        seen.append(kw["levels"])
        assert kw["keep_tables"]
        tables = {"S0": {"table": s0, **proba0}, "S2": {"table": t, **proba}}
        return {"tables": {lv: tables[lv] for lv in kw["levels"]}}

    monkeypatch.setattr("finmesh.training.x6.run_seed_x6", fake_x6)

    def model(prompt: str, fmt: Any) -> str:
        import re

        m = re.search(r'"typology_id" \(exactly "([^"]+)"\)', prompt) or re.search(
            r'"typology_id" to "([^"]+)"', prompt
        )
        assert m is not None
        return json.dumps(
            {"typology_id": m.group(1), "cited_fields": ["case_members"], "narrative": "Linked."}
        )

    r = nar.run_narrative(fixture_paths, n=40, call=model)
    assert seen[-1] == ("S0", "S2") and r["protocol"] == "A22"
    s = r["summary"]
    assert s["cases"] == 40 and s["H3b"]["grounding"]["estimate"] == 1.0
    assert s["strict_grounding"]["estimate"] == 1.0
    assert r["selective"]["detected_schemes"] == 216 and r["selective"]["tau"] is not None
    assert {c["pattern"] for c in r["cases"]} == {"FAN-IN", "FAN-OUT", "CYCLE"}
    tk = r["topk"]
    assert tk["schemes"] == 240 and tk["levels"]["S2"]["top3"]["estimate"] == pytest.approx(0.9)
    assert tk["comparisons"]["S2 - S0 (top 1)"]["low"] > 0
    old = nar.run_narrative(fixture_paths, n=40, call=model, protocol="A21")
    assert seen[-1] == ("S2",) and old["topk"] is None
    page = render_narrative(r, previous=old)
    assert "Strict grounding (A22)" in page and "A21 → A22" in page and "top three" in page
    assert "H3b on validation" in render_narrative(old)
    out = write_cases(r, Path(str(fixture_paths.parquet)) / "cases.jsonl")  # type: ignore[attr-defined]
    assert len(out.read_text().splitlines()) == 40
    from finmesh.attribution.narrative_report import write_review

    rev = write_review(r, Path(str(fixture_paths.parquet)) / "review.csv")  # type: ignore[attr-defined]
    text = rev.read_text()
    assert len(text.strip().splitlines()) == 31 and "faithful" in text
    assert "FAN-IN," not in text.split("\n")[0]  # no true-pattern column


def test_topk_and_frequency_baseline() -> None:
    pats = np.array(["A"] * 6 + ["B"] * 3 + ["C"] * 2 + ["D"] * 1)
    det = np.ones(12, dtype=bool)
    det[-1] = False
    proba = np.tile([0.1, 0.2, 0.3, 0.4], (12, 1))  # always ranks D, C, B, A
    h3 = nar.topk_hits(pats, det, ["A", "B", "C", "D"], proba, 3)
    assert h3.tolist() == [False] * 6 + [True] * 5 + [False]  # D undetected counts as a miss
    fold = np.array([0, 1] * 6)
    f = nar.frequency_top3(pats, det, fold)
    assert f[:6].all()  # A is among the three most frequent in either half


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


def test_ollama_call_unloads_the_model_periodically(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, Any]] = []

    class Reply:
        def __enter__(self) -> Reply:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"response": "{}"}'

    def fake_urlopen(request: Any, timeout: float) -> Reply:
        sent.append(json.loads(request.data))
        return Reply()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    call = nar.ollama_call("http://localhost:11434", "llama3.2:3b", 600)
    for _ in range(12):
        assert call("hi", "json") == "{}"
    unloads = [i for i, body in enumerate(sent, 1) if body.get("keep_alive") == 0]
    assert unloads == [6, 12]  # bounded prompt cache without a reload per call
    assert "keep_alive" not in sent[0]  # Ollama's default keeps the model between calls
    assert sent[0]["options"]["num_predict"] == 400 and sent[0]["options"]["temperature"] == 0
    each = nar.ollama_call("http://localhost:11434", "llama3.2:3b", 600, unload_every=1)
    each("hi", "json")
    assert sent[-1]["keep_alive"] == 0


def test_a_stopped_server_stops_the_run_and_saves_nothing(
    monkeypatch: pytest.MonkeyPatch, fixture_paths: object, ingested: object
) -> None:
    import http.client
    import urllib.error

    from finmesh.eval.g0 import run_g0

    refused = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
    assert nar.server_down(refused)
    assert nar.server_down(http.client.RemoteDisconnected("Remote end closed connection"))
    assert not nar.server_down(TimeoutError("timed out"))  # a slow model is a failed reply
    assert not nar.server_down(urllib.error.URLError(TimeoutError("timed out")))
    http500 = urllib.error.HTTPError("http://localhost", 500, "error", None, None)  # type: ignore[arg-type]
    assert not nar.server_down(http500)

    run_g0(fixture_paths)  # type: ignore[arg-type]
    t = _table()
    proba: dict[str, Any] = {}
    attribute(t, "S2", 0, load_catalogue(), proba)
    monkeypatch.setattr(
        "finmesh.training.x6.run_seed_x6",
        lambda *_, **kw: {"tables": {lv: {"table": t, **proba} for lv in kw["levels"]}},
    )
    calls = {"n": 0}

    def dies_after_three(prompt: str, fmt: Any) -> str:
        calls["n"] += 1
        if calls["n"] > 3:
            raise refused
        return json.dumps({"narrative": "Linked.", "cited_fields": ["case_members"],
                           "typology_id": "UNATTRIBUTED"})  # fmt: skip

    r = nar.run_narrative(fixture_paths, n=40, call=dies_after_three)
    assert "error" in r and "nothing was saved" in r["error"] and " of 40 " in r["error"]


def test_rerun_script_discards_a_narrative_made_while_the_server_was_down(tmp_path: Path) -> None:
    import subprocess

    script = Path(__file__).resolve().parents[2] / "scripts" / "week14_rerun.sh"
    text = script.read_text()
    body = text[text.index("discard_if_broken() {") : text.index("\nif ! curl")]
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps({"result": {"cases": [{"errors": ["TimeoutError: timed out"]}]}}))
    bad.write_text(json.dumps({"result": {"cases": [
        {"errors": []}, {"errors": ["URLError: <urlopen error [Errno 111] Connection refused>"]}
    ]}}))  # fmt: skip
    run = f'set -euo pipefail\n{body}\ndiscard_if_broken "{good}"\ndiscard_if_broken "{bad}"\n'
    out = subprocess.run(["bash", "-c", run], capture_output=True, text=True, check=True)
    assert good.exists() and not bad.exists(), out.stdout + out.stderr
    good2 = tmp_path / "again.json"
    good2.write_text(good.read_text())
    fresh = f'set -euo pipefail\n{body}\nFRESH=1 discard_if_broken "{good2}"\n'
    subprocess.run(["bash", "-c", fresh], capture_output=True, text=True, check=True)
    assert not good2.exists()
