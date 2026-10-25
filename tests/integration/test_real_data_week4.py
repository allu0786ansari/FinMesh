"""Week-4 checks on real data (skipped when absent): feature coverage, schema, leakage."""

from __future__ import annotations

import json

import pytest

from finmesh.features.build import FeatureStore
from finmesh.features.schema import load_schema
from finmesh.paths import REPO_ROOT, artifacts_dir, dataset_paths

DATASETS = ("HI-Medium", "LI-Medium", "HI-Small", "LI-Small")


def _store(name: str) -> FeatureStore:
    try:
        return FeatureStore(dataset_paths(name), "B8")
    except FileNotFoundError:
        pytest.skip(f"{name}: features not built")


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_features_cover_every_labelled_account_window(name: str) -> None:
    store = _store(name)
    counts = REPO_ROOT / "docs" / "protocol" / f"eval_counts_{name}.json"
    if not counts.exists():
        pytest.skip(f"{name}: no frozen evaluation counts")
    frozen = json.loads(counts.read_text())["counts"]
    for part in ("train", "val"):
        assert store.meta["rows"][part] == frozen[part]["account_windows"], part
    assert store.meta["schema_sha256"] == load_schema().sha256


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_no_single_feature_looks_like_a_leak(name: str) -> None:
    path = artifacts_dir() / "week04" / f"feature_signal_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: feature-report not run")
    result = json.loads(path.read_text())["result"]
    assert result["flagged"] == [], f"inspect {result['flagged']} before week 5"
