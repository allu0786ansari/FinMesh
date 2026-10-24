from __future__ import annotations

import json
import random
from pathlib import Path

import polars as pl
import pytest

from finmesh.attribution import llm_probe
from finmesh.data import ingest
from finmesh.data.schema import CANONICAL_COLUMNS
from finmesh.paths import DatasetPaths


def test_validate_reply() -> None:
    cands = ["T-CYCLE", "T-FAN-IN"]
    good = json.dumps(
        {
            "typology_id": "T-CYCLE",
            "confidence": 0.7,
            "cited_fields": ["burst_level"],
            "rationale": "x",
        }
    )
    assert llm_probe.validate_reply(good, cands) == {"json": True, "schema": True, "grounded": True}
    off_list = good.replace("T-CYCLE", "T-STACK")
    assert llm_probe.validate_reply(off_list, cands)["grounded"] is False
    bad_field = good.replace("burst_level", "account_number")
    assert llm_probe.validate_reply(bad_field, cands)["grounded"] is False
    assert llm_probe.validate_reply("not json", cands) == {
        "json": False,
        "schema": False,
        "grounded": False,
    }
    assert llm_probe.validate_reply("[1, 2]", cands)["json"] is False
    no_conf = json.dumps({"typology_id": "T-CYCLE", "cited_fields": [], "rationale": "x"})
    assert llm_probe.validate_reply(no_conf, cands)["schema"] is False


def test_prompt_contains_no_identifiers() -> None:
    prompt, cands, evidence = llm_probe.make_prompt(random.Random(1))
    assert len(cands) == 5 and all(c in prompt for c in cands)
    assert set(evidence) == set(llm_probe.EVIDENCE_FIELDS)
    schema = llm_probe.response_schema(cands)
    assert schema["properties"]["typology_id"]["enum"] == cands


def test_only_local_endpoints() -> None:
    llm_probe.assert_local("http://localhost:11434")
    llm_probe.assert_local("http://127.0.0.1:11434")
    with pytest.raises(ValueError):
        llm_probe.assert_local("https://api.example.com")


def test_probe_reports_unreachable_server() -> None:
    out = llm_probe.run_probe(n=1, url="http://127.0.0.1:9", timeout=1)
    assert "error" in out


def test_sliced_duplicate_count_matches_exact(
    fixture_paths: DatasetPaths, ingested: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    lf = pl.scan_parquet(fixture_paths.transactions)
    cols = list(CANONICAL_COLUMNS)
    exact = (
        lf.group_by(cols)
        .agg(pl.len().alias("n"))
        .filter(pl.col("n") > 1)
        .select((pl.col("n") - 1).sum())
        .collect()
        .item()
    )
    rows = lf.select(pl.len()).collect().item()
    monkeypatch.setattr(ingest, "ROWS_PER_DUPLICATE_SLICE", 500)  # force about nine slices
    extra, groups = ingest._duplicate_counts(lf, cols, rows)
    assert extra == exact == 1
    assert groups == 1


def test_quality_query_stays_streamable(tmp_path: Path) -> None:
    """Guard against the week-2 regression: ``is_in`` forced the in-memory engine."""
    src = Path(ingest.__file__).read_text()
    code = "\n".join(line for line in src.splitlines() if not line.strip().startswith("#"))
    assert "is_in(" not in code
