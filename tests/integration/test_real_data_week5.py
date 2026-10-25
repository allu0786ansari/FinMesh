"""Week-5 checks on real data (skipped when absent): labels A9, features v3, baselines."""

from __future__ import annotations

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.eval.sealed import EvalStore
from finmesh.features.build import FeatureStore
from finmesh.paths import artifacts_dir, dataset_paths

DATASETS = ("HI-Medium", "LI-Medium", "HI-Small", "LI-Small")


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_labels_and_both_feature_views_line_up(name: str) -> None:
    paths = dataset_paths(name)
    try:
        store = EvalStore(paths, "B8")
        store.partition("val")  # refuses labels built before amendment A9
        member = FeatureStore(paths, "B8", "member")
        pooled = FeatureStore(paths, "B8", "pooled")
    except FileNotFoundError as exc:
        pytest.skip(f"{name}: {exc}")
    for part in ("train", "val"):
        assert member.meta["rows"][part] == store.meta["counts"][part]["account_windows"]
        assert pooled.meta["rows"][part] == member.meta["rows"][part]


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_baselines_are_sane(name: str) -> None:
    path = artifacts_dir() / "week05" / f"baselines_{name}_seed0.json"
    if not path.exists():
        pytest.skip(f"{name}: baselines not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    res = r["results"]
    prevalence = res["random"]["window"]["prevalence"]
    # The random scorer sits on its baseline; trained models clear it.
    assert abs(res["random"]["window"]["auprc"]["estimate"] - prevalence) < 0.2 * prevalence
    for name_ in ("S0-BG", "oracle"):
        assert res[name_]["window"]["auprc"]["estimate"] > 2 * prevalence, name_
    primary = r["primary_budget"]
    rnd = next(b for b in res["random"]["budgets"] if b["budget"] == primary)
    band = rnd["random_alert_detected"]
    assert band["low"] - 0.02 <= rnd["detected"]["estimate"] <= band["high"] + 0.02
