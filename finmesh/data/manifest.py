"""SHA-256 manifests for raw and derived data files.

Every artifact FinMesh produces records the manifest hash of the data it was
built from (see finmesh.eval.provenance), so a reported number can always be
traced back to exact input bytes. The manifest also carries the ``fixture``
flag: data produced by the synthetic fixture generator can never pass a gate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_CHUNK = 1 << 20


def sha256_file(path: Path) -> str:
    """Stream a file through SHA-256 without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class FileEntry:
    role: str
    path: str
    sha256: str
    bytes: int


@dataclass
class Manifest:
    dataset: str
    fixture: bool
    files: list[FileEntry] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    def add(self, role: str, path: Path, relative_to: Path | None = None) -> FileEntry:
        shown = path.relative_to(relative_to) if relative_to else path
        entry = FileEntry(
            role=role, path=shown.as_posix(), sha256=sha256_file(path), bytes=path.stat().st_size
        )
        self.files.append(entry)
        return entry

    @property
    def manifest_hash(self) -> str:
        """Hash over roles and file hashes only, so it is stable across machines."""
        payload = json.dumps(
            {
                "dataset": self.dataset,
                "fixture": self.fixture,
                "files": sorted((f.role, f.sha256) for f in self.files),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["manifest_hash"] = self.manifest_hash
        return out

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")


def load_manifest(path: Path) -> Manifest:
    raw = json.loads(path.read_text())
    manifest = Manifest(dataset=raw["dataset"], fixture=bool(raw["fixture"]))
    manifest.created_at = raw["created_at"]
    manifest.files = [FileEntry(**f) for f in raw["files"]]
    if manifest.manifest_hash != raw["manifest_hash"]:
        raise ValueError(f"manifest hash mismatch in {path}; the file was edited by hand")
    return manifest
