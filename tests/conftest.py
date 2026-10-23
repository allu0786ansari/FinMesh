"""Shared test fixtures: one synthetic dataset, ingested once per test session."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from finmesh.data.fixture import FixtureTruth, write_fixture
from finmesh.data.pipeline import ingest_dataset
from finmesh.data.schema import FIXTURE_DATASET
from finmesh.paths import DatasetPaths, dataset_paths


@pytest.fixture(scope="session")
def fixture_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("finmesh-data")


@pytest.fixture(scope="session")
def fixture_paths(fixture_root: Path) -> DatasetPaths:
    return dataset_paths(FIXTURE_DATASET, root=fixture_root)


@pytest.fixture(scope="session")
def fixture_truth(fixture_paths: DatasetPaths) -> FixtureTruth:
    return write_fixture(fixture_paths.raw, seed=7)


@pytest.fixture(scope="session")
def ingested(fixture_paths: DatasetPaths, fixture_truth: FixtureTruth) -> dict[str, object]:
    return ingest_dataset(fixture_paths)


@pytest.fixture()
def data_env(monkeypatch: pytest.MonkeyPatch, fixture_root: Path) -> Iterator[Path]:
    """Point FINMESH_DATA at the session's temporary data root."""
    monkeypatch.setenv("FINMESH_DATA", str(fixture_root))
    yield fixture_root
