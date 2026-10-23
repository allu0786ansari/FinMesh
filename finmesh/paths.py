"""Filesystem locations used across FinMesh.

Everything large lives under one data root, which defaults to ``./data`` in the
repository and can be moved with the ``FINMESH_DATA`` environment variable
(useful when the repository sits on a small disk):

    data/
      raw/<dataset>/        original AMLworld CSV and TXT files, never modified
      parquet/<dataset>/    typed Parquet produced by ``finmesh ingest``
      artifacts/            provenance-stamped results (JSON, plots, tables)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def data_root() -> Path:
    """Return the data root, honouring ``FINMESH_DATA`` if it is set."""
    env = os.environ.get("FINMESH_DATA")
    return Path(env).expanduser().resolve() if env else REPO_ROOT / "data"


@dataclass(frozen=True)
class DatasetPaths:
    """Standard locations for one dataset (for example ``HI-Small``)."""

    name: str
    root: Path
    raw_override: Path | None = None

    @property
    def raw(self) -> Path:
        """Raw files; ``raw_override`` lets them live outside the data root."""
        return self.raw_override if self.raw_override else self.root / "raw" / self.name

    @property
    def parquet(self) -> Path:
        return self.root / "parquet" / self.name

    @property
    def transactions(self) -> Path:
        return self.parquet / "transactions.parquet"

    @property
    def scheme_links(self) -> Path:
        return self.parquet / "scheme_links.parquet"

    @property
    def schemes(self) -> Path:
        return self.parquet / "schemes.parquet"

    @property
    def accounts(self) -> Path:
        return self.parquet / "accounts.parquet"

    @property
    def manifest(self) -> Path:
        return self.parquet / "manifest.json"

    @property
    def ingest_report(self) -> Path:
        return self.parquet / "ingest_report.json"


def dataset_paths(name: str, root: Path | None = None, raw_dir: Path | None = None) -> DatasetPaths:
    return DatasetPaths(
        name=name,
        root=root if root is not None else data_root(),
        raw_override=raw_dir.expanduser().resolve() if raw_dir else None,
    )


def artifacts_dir(root: Path | None = None) -> Path:
    return (root if root is not None else data_root()) / "artifacts"
