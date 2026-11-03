"""Week 18: the sealed-test runners, the seal's bookkeeping, two raters, the results page."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest

from finmesh.eval.guard import LabelFrame
from finmesh.eval.sealed import PartitionData, SealedTestError, aligned_labels


def _part(frame: pl.DataFrame) -> PartitionData:
    return PartitionData(
        partition="test",
        labels=LabelFrame(frame, "test"),
        scheme_windows=pl.DataFrame(),
        schemes=pl.DataFrame(),
        hours=24.0,
        windows=(0, 3),
    )


def test_aligned_labels_fast_path_join_and_missing_rows() -> None:
    frame = pl.DataFrame(
        {
            "member": [0, 0, 1],
            "account": [1, 2, 3],
            "window": [0, 1, 1],
            "label": [0, 1, 0],
            "masked": [False, False, True],
        }
    )
    part = _part(frame)
    y, use = aligned_labels(part, frame.select("member", "account", "window"))
    assert y.tolist() == [0, 1, 0] and use.tolist() == [True, True, False]
    shuffled = frame.select("member", "account", "window")[[2, 0]]
    y, use = aligned_labels(part, shuffled)
    assert y.tolist() == [0, 0] and use.tolist() == [False, True]
    with pytest.raises(ValueError, match="missing"):
        aligned_labels(part, pl.DataFrame({"member": [5], "account": [9], "window": [0]}))


def test_fit_and_apply_stackers() -> None:
    from finmesh.training.x1 import apply_stackers, fit_stackers

    rng = np.random.default_rng(0)
    n = 400
    x = rng.normal(size=n)
    y = (x + rng.normal(scale=0.5, size=n) > 0).astype(np.int8)
    member = np.where(np.arange(n) < 300, 0, 1)
    member[-5:] = 2  # too few rows: member 2 keeps its own probability
    feats = pl.DataFrame({"member": member, "prob": np.full(n, 0.3), "f": x})
    fitted = fit_stackers(feats, ("f",), y, np.ones(n, dtype=bool), seed=0)
    assert set(fitted) == {0, 1}
    out = apply_stackers(feats, ("f",), fitted)
    assert np.all(out[-5:] == 0.3)
    assert np.corrcoef(out[:300], x[:300])[0, 1] > 0.9
    assert apply_stackers(feats.head(0), ("f",), fitted).shape == (0,)


def _outcomes(values: list[int]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "scheme_id": list(range(len(values))),
            "linked": values,
            "detected": values,
            "linked_cross_member": values,
        }
    )


def test_combine_uses_each_configurations_own_seeds_and_holm() -> None:
    from finmesh.training.x1 import combine

    n = 40
    s0 = [0] * n
    s2 = [1] * 30 + [0] * 10
    s1 = [1] * 10 + [0] * 30
    protocol = {"S2": {"accounts_disclosed": 10}, "PD[tau=2]": {"accounts_disclosed": 4}}
    seeds: list[dict[str, Any]] = []
    for seed in range(5):
        outcomes = {"S0": _outcomes(s0), "S2/stacker": _outcomes(s2)}
        outcomes["PD[tau=2]/stacker"] = _outcomes(s2)
        auprc = {"S0": 0.1, "S2/stacker": 0.2, "PD[tau=2]/stacker": 0.2}
        if seed < 3:
            outcomes["S1/stacker"] = _outcomes(s1)
            auprc["S1/stacker"] = 0.15
        seeds.append({"seed": seed, "outcomes": outcomes, "auprc": auprc, "protocol": protocol})
    s = combine(seeds, reps=200, holm_family=True)
    assert s["S2/stacker"]["seeds"] == [0, 1, 2, 3, 4]
    assert s["S1/stacker"]["seeds"] == [0, 1, 2]
    assert s["holm_family"] == ["S2/stacker", "PD[tau=2]/stacker", "S1/stacker"]
    for lv in s["holm_family"]:
        assert s[lv]["linked_gain"]["p_holm"] >= s[lv]["linked_gain"]["p"]
        assert "p_holm" in s[lv]["detected_gain"]
    assert s["H1d"]["PD[tau=2]"]["disclosure_share_of_S2"] == pytest.approx(0.4)
    assert s["H1d"]["PD[tau=2]"]["gain_share_of_S2"]["estimate"] == pytest.approx(1.0)
    assert s["H1d"]["S1"]["gain_share_of_S2"]["estimate"] == pytest.approx(1 / 3)
    # One seed set: the plain validation behaviour, no Holm keys.
    plain = combine(seeds[:3], reps=200)
    assert "holm_family" not in plain and "p_holm" not in plain["S2/stacker"]["linked_gain"]


def test_slices_refuse_the_sealed_partition_without_an_opening(
    fixture_paths: Any, ingested: object
) -> None:
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.sealed import EvalStore
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import FeatureStore, build_features
    from finmesh.training.data import feature_slices, slices

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    store, feats = EvalStore(fixture_paths), FeatureStore(fixture_paths, "B8", "member")
    with pytest.raises(SealedTestError):
        next(slices(store, feats, "test"))
    first = next(feature_slices(feats, "test"))
    assert "label" not in first.columns and first.height > 0


def test_x1_and_x6_on_test_with_the_seal(
    fixture_paths: Any, ingested: object, monkeypatch: pytest.MonkeyPatch
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
    before = len(read_access_log(fixture_paths))
    r = sealed_runs.run_x1_test(
        fixture_paths,
        headline_seeds=(0, 1),
        other_seeds=(0,),
        reps=50,
        window_reps=20,
    )
    s = r["summary"]
    assert s["S2/stacker"]["seeds"] == [0, 1] and s["S1/stacker"]["seeds"] == [0]
    assert s["oracle"]["linked"]["estimate"] > 0
    assert "p_holm" in s["S2/stacker"]["linked_gain"]
    assert r["x6"] is not None and r["x6"]["seeds"] == [0]
    assert "met" in r["x6"]["summary"]["H3a"]
    assert r["audit"] is not None and r["audit"]["A6"]["rows"] > 0  # A6 after the opening
    assert r["random"] is not None
    log = read_access_log(fixture_paths)[before:]
    assert [(e["seed"], e["repeat"]) for e in log] == [(0, False), (1, False)]
    assert all(len(e["extra"]["scores_sha256"]) == 64 for e in log)
    folder = sealed_runs.test_dir(fixture_paths, "B8")
    inputs = sealed_runs._load(folder / "narrative_inputs.pkl")
    assert set(inputs["val"]) == set(inputs["test"]) == {"S0", "S2"}
    assert inputs["test"]["S2"]["p"].shape[0] == inputs["test"]["S2"]["table"].height

    # A rerun keeps the saved seeds and opens nothing.
    again = sealed_runs.run_x1_test(
        fixture_paths,
        headline_seeds=(0, 1),
        other_seeds=(0,),
        reps=50,
        window_reps=20,
    )
    assert len(read_access_log(fixture_paths)) == before + 2
    assert again["per_seed"][1]["scores_sha256"] == r["per_seed"][1]["scores_sha256"]
    # A lost result after an opening is refused before any work, unless repeats are allowed.
    (folder / "x1_seed1.pkl").unlink()
    with pytest.raises(SealedTestError, match="already opened"):
        sealed_runs.run_x1_test(
            fixture_paths,
            headline_seeds=(0, 1),
            other_seeds=(0,),
            reps=50,
            window_reps=20,
        )
    redo = sealed_runs.run_x1_test(
        fixture_paths,
        headline_seeds=(0, 1),
        other_seeds=(0,),
        reps=50,
        window_reps=20,
        allow_repeat=True,
    )
    assert redo["per_seed"][1]["scores_sha256"] == r["per_seed"][1]["scores_sha256"]  # same scores
    assert read_access_log(fixture_paths)[-1]["repeat"] is True


def _inputs_table(n: int, patterns: list[str]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "scheme_id": list(range(n)),
            "pattern": [patterns[i % len(patterns)] for i in range(n)],
            "fold": [i % 2 for i in range(n)],
            "incident": [i for i in range(n)],
            "owner": [0] * n,
            "own_accounts": [2.0] * n,
        }
    )


def test_narrative_on_test_logs_once_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finmesh.attribution import narrative
    from finmesh.eval import sealed
    from finmesh.paths import dataset_paths
    from finmesh.training import sealed_runs

    paths = dataset_paths("HI-Medium", root=tmp_path)
    classes = ["FAN-IN", "FAN-OUT", "CYCLE"]
    t_val, t_test = _inputs_table(40, classes), _inputs_table(30, classes)

    def proba(t: pl.DataFrame) -> np.ndarray:
        p = np.full((t.height, 3), 0.1)
        for i, pat in enumerate(t["pattern"]):
            p[i, classes.index(pat)] = 0.8
        return p

    tables = {
        "val": {lv: {"table": t_val, "classes": classes, "p": proba(t_val)} for lv in ("S0", "S2")},
        "test": {
            lv: {"table": t_test, "classes": classes, "p": proba(t_test)} for lv in ("S0", "S2")
        },
        "seed": 0,
    }
    folder = sealed_runs.test_dir(paths, "B8")
    sealed_runs._save(folder / "narrative_inputs.pkl", tables)
    log: list[dict[str, Any]] = []

    class Plan:
        window_hours = 6

    def fake_open(store: Any, config: dict[str, Any], seed: int, purpose: str, **kw: Any) -> Any:
        log.append({"config_hash": json.dumps(config, sort_keys=True), "seed": seed, **kw})

        class P:
            schemes = t_test.select("scheme_id", "pattern")

        return P()

    def fake_before(p: Any, config: dict[str, Any], seed: int) -> Any:
        h = json.dumps(config, sort_keys=True)
        return next((e | {"time": "t"} for e in log if e["config_hash"] == h), None)

    monkeypatch.setattr(sealed, "open_sealed_test", fake_open)
    monkeypatch.setattr(sealed, "opened_before", fake_before)
    monkeypatch.setattr(sealed, "EvalStore", lambda p, o: None)
    monkeypatch.setattr("finmesh.eval.split_io.load_plan", lambda p: Plan())
    monkeypatch.setattr(
        "finmesh.training.x6.load_catalogue",
        lambda: {
            "entries": [{"id": c, "review_actions": ["look"], "description": c} for c in classes]
        },
    )
    calls = {"n": 0}

    def stop_after_three(prompt: str, fmt: Any) -> str:
        calls["n"] += 1
        if calls["n"] > 3:
            raise narrative.ModelUnavailable("down")
        return json.dumps({"narrative": "", "cited_fields": [], "typology_id": "UNATTRIBUTED"})

    monkeypatch.setattr(narrative, "narrate", lambda case, cat, call, prot: _fake(case, call))
    monkeypatch.setattr(narrative, "summarise", lambda results: {"cases": len(results)})
    first = narrative.run_narrative(paths, n=6, call=stop_after_three, split="test")
    assert "error" in first and "resumes" in first["error"]
    assert len(log) == 1
    done = sealed_runs._load(folder / "narrative_A23_cases.pkl")["results"]
    assert len(done) == 3
    calls["n"] = -100
    second = narrative.run_narrative(paths, n=6, call=stop_after_three, split="test")
    assert "error" not in second, second
    assert len(log) == 1  # resumed without a second opening
    assert second["split"] == "test" and len(second["cases"]) == 6
    assert second["selective"]["tau_from"] == "validation (frozen)"
    assert second["topk"]["levels"]["S2"]["frequency_top3"] is not None


def _fake(case: dict[str, Any], call: Any) -> dict[str, Any]:
    call("prompt", "json")
    return {
        "scheme_id": case["scheme_id"],
        "pattern": case["pattern"],
        "assigned": case["assigned"],
        "grounded": True,
        "strict": True,
        "final_source": "model",
    }


def test_cohen_kappa_and_two_raters(tmp_path: Path) -> None:
    from finmesh.attribution.narrative_report import (
        AB_COLUMNS,
        cohen_kappa,
        prepare_rater_sheets,
        render_two_raters,
        score_two_raters,
    )

    assert cohen_kappa(["yes", "no"], ["yes", "no"], ("no", "partly", "yes")) == 1.0
    k = cohen_kappa(["yes", "no", "yes", "no"], ["yes", "yes", "no", "no"], ("no", "yes"))
    assert k == pytest.approx(0.0)
    assert cohen_kappa([], [], ("no", "yes")) is None
    lin = cohen_kappa(
        ["no", "yes", "partly"], ["partly", "yes", "partly"], ("no", "partly", "yes"), "linear"
    )
    assert lin is not None and 0 < lin < 1

    master = tmp_path / "narrative_X_A23_review.csv"
    key = tmp_path / "narrative_X_A23_review_KEY_do_not_open.csv"
    with master.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(AB_COLUMNS)
        for i in (1, 2, 3, 4):
            w.writerow([i, "ev", "c", "a", "b", "", "", "", "", "", ""])
    with key.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case", "scheme_id", "A", "B", "model_source", "model_claim_consistent"])
        for i, (a, b, ok) in enumerate(
            [("model", "template", "True"), ("template", "model", "False")] * 2, 1
        ):
            w.writerow([i, 100 + i, a, b, "model", ok])
    sheets = prepare_rater_sheets(master, ["allaudin", "ravi"])
    assert [p.name for p in sheets] == [
        "narrative_X_A23_review_allaudin.csv",
        "narrative_X_A23_review_ravi.csv",
    ]

    def fill(path: Path, faithful_model: list[str], prefer: list[str]) -> None:
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
        for r, fm, p in zip(rows, faithful_model, prefer, strict=True):
            model_side = "A" if int(r["case"]) % 2 else "B"
            other = "B" if model_side == "A" else "A"
            r[f"faithful {model_side} (yes/partly/no)"] = fm
            r[f"useful {model_side} (1-3)"] = "2"
            r[f"faithful {other} (yes/partly/no)"] = "yes"
            r[f"useful {other} (1-3)"] = "3"
            r["prefer (A/B/same)"] = p
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=AB_COLUMNS)
            w.writeheader()
            w.writerows(rows)

    fill(sheets[0], ["yes", "no", "yes", "no"], ["A", "A", "same", "B"])
    fill(sheets[1], ["yes", "no", "partly", "no"], ["A", "A", "same", "A"])
    s = score_two_raters({"allaudin": sheets[0], "ravi": sheets[1]}, key)
    assert s["per_rater"]["allaudin"]["rated"] == 4
    ag = s["agreement"]
    assert ag["cases"] == 4 and 0 < ag["faithful_exact"] < 1
    ck = s["checker_vs_consensus"]
    assert ck["consensus_faithful"] == 1 and ck["checker_consistent"] == 2
    page = render_two_raters(s, "X")
    assert "two raters" in page and "Agreement between the raters" in page
    assert prepare_rater_sheets(master, ["ravi"])[0].read_text() == sheets[1].read_text()


def test_results_page_and_test_relabelling(tmp_path: Path) -> None:
    from finmesh.cli import as_test_page
    from finmesh.eval.provenance import Stamp, write_artifact
    from finmesh.eval.test_report import write_results

    page = as_test_page("# X1 · sharing ladder on validation · HI\n\nMet on validation | yes")
    assert page.startswith("# X1 · sharing ladder on test · HI") and "Sealed test" in page
    assert "Met on test" in page

    ci = {"estimate": 0.5, "low": 0.4, "high": 0.6}
    x1 = {
        "summary": {
            "S0": {"linked": {"estimate": 0.2, "low": 0.1, "high": 0.3}},
            "S2/stacker": {
                "linked": {"estimate": 0.7, "low": 0.6, "high": 0.8},
                "linked_gain": {"difference": ci, "p": 0.001, "p_holm": 0.01},
            },
            "oracle-relational": {
                "linked": ci,
                "linked_gain": {"difference": {"estimate": 0.5, "low": 0.4, "high": 0.6}, "p": 0},
            },
            "H1b": {
                "oracle-relational": {"S2/stacker": {"estimate": 1.0, "low": 0.9, "high": 1.1}}
            },
            "H1d": {
                "PD[tau=3]": {
                    "gain_share_of_S2": ci,
                    "disclosure_share_of_S2": 0.3,
                    "met_on_validation": False,
                }
            },
        },
        "random": {"linked": 0.01},
        "audit": {"H1c": {"S1_and_S3_le2_within": True, "not_assessable": []}},
        "x6": {
            "summary": {
                "H3a": {
                    "S2_minus_S0": ci,
                    "S2_above_majority": ci,
                    "S2_above_rules": ci,
                    "met": True,
                }
            }
        },
    }
    stamp = Stamp(kind="x1-test", dataset="HI-Medium", manifest_hash="h", fixture=False)
    folder = tmp_path / "week18"
    write_artifact(folder / "x1_test_HI-Medium.json", stamp, x1)
    out = write_results(folder, tmp_path / "RESULTS.md")
    text = out.read_text()
    assert "## HI-Medium" in text and "H1a" in text and "H1b" in text and "H3a" in text
    assert "## LI-Medium" in text and "Not run yet." in text


def test_frozen_commit_is_read_from_the_plan(tmp_path: Path) -> None:
    from finmesh.eval.test_plan import frozen_commit

    plan = tmp_path / "plan.md"
    plan.write_text("**Frozen commit:** pending owner sign-off\n")
    assert frozen_commit(plan) is None
    plan.write_text("**Frozen commit:** `abc1234def`\n")
    assert frozen_commit(plan) == "abc1234def"
    assert frozen_commit(tmp_path / "missing.md") is None


def test_preflight_on_the_fixture(
    fixture_paths: Any, ingested: object, data_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finmesh.eval import test_plan
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    build_features(fixture_paths, "B8", view="pooled")
    monkeypatch.setattr(test_plan, "_clean_tree", lambda: True)
    monkeypatch.setattr(test_plan, "frozen_commit", lambda plan=None: None)
    r = test_plan.preflight(fixture_paths, "B8", "x1,narrative")
    assert r["ok"], r["lines"]
    text = "\n".join(r["lines"])
    assert "sealed test universe present" in text and "member view" in text
    monkeypatch.setattr(test_plan, "frozen_commit", lambda plan=None: "0" * 12)
    monkeypatch.setattr(test_plan, "code_changes_since", lambda c: ["finmesh/cli.py"])
    bad = test_plan.preflight(fixture_paths, "B8", "x1")
    assert not bad["ok"] and any("FAIL" in line and "cli.py" in line for line in bad["lines"])


def test_token_traffic_reads_no_test_label(
    fixture_paths: Any, ingested: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finmesh.eval import sealed
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.training.sealed_runs import token_traffic

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")

    def no(*a: Any, **k: Any) -> None:
        raise AssertionError("the traffic check must not open the test")

    monkeypatch.setattr(sealed, "open_sealed_test", no)
    rows = token_traffic(fixture_paths)
    assert [(r["partition"], r["calibration"]) for r in rows] == [
        ("val", "end of training"),
        ("val", "fitted on validation"),
        ("test", "end of training"),
        ("test", "fitted on validation"),
    ]
    assert all(r["candidates"] > 0 and r["peak_tokens"] > 0 for r in rows)
