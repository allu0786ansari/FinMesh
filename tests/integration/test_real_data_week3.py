"""Week-3 checks on real data (skipped when absent): frozen splits and labels.

uv run pytest -m real_data -v
"""

from __future__ import annotations

import json

import pytest

from finmesh.eval.sealed import EvalStore, SealedTestError
from finmesh.paths import REPO_ROOT, dataset_paths

DATASETS = ("HI-Small", "LI-Small", "HI-Medium", "LI-Medium")


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_split_plan_matches_frozen_copy(name: str) -> None:
    frozen = REPO_ROOT / "docs" / "protocol" / f"split_plan_{name}.json"
    local = dataset_paths(name).parquet / "split_plan.json"
    if not (frozen.exists() and local.exists()):
        pytest.skip(f"{name}: no frozen or no local split plan")
    a, b = json.loads(frozen.read_text()), json.loads(local.read_text())
    assert a["periods"] == b["periods"] and a["window_hours"] == b["window_hours"]


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_labels_built_and_test_sealed(name: str) -> None:
    try:
        store = EvalStore(dataset_paths(name), "B8")
    except FileNotFoundError:
        pytest.skip(f"{name}: labels not built")
    for part in ("train", "val"):
        c = store.meta["counts"][part]
        assert c["positives"] > 0 and c["account_windows"] > c["positives"]
        assert c["multi_member_schemes"] <= c["schemes"]
    with pytest.raises(SealedTestError):
        store.partition("test")
