"""Provenance stamps for every artifact (proposal Section 9, criterion CC3).

A stamp records what produced a result: code version, data manifest hash,
parameters, seed and split, plus privacy settings once the DP weeks start.
``assert_gate_eligible`` is the single place that refuses fixture-based
results at a gate.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finmesh import __version__
from finmesh.paths import REPO_ROOT


class GateIneligibleError(RuntimeError):
    """Raised when a fixture-based or unstamped artifact is offered to a gate."""


def git_commit(repo: Path = REPO_ROOT) -> str:
    """Current commit hash, with ``+dirty`` when the tree has local changes."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{commit}+dirty" if dirty else commit


@dataclass(frozen=True)
class Stamp:
    kind: str
    dataset: str
    manifest_hash: str
    fixture: bool
    params: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    split: str | None = None
    privacy: dict[str, Any] | None = None
    code_version: str = __version__
    git_commit: str = field(default_factory=git_commit)
    python: str = field(default_factory=lambda: sys.version.split()[0])
    platform: str = field(default_factory=platform.platform)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_artifact(path: Path, stamp: Stamp, payload: dict[str, Any]) -> Path:
    """Write ``{"provenance": stamp, "result": payload}`` as indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"provenance": stamp.to_dict(), "result": payload}
    path.write_text(json.dumps(document, indent=2, default=str) + "\n")
    return path


def read_artifact(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    document = json.loads(path.read_text())
    if "provenance" not in document:
        raise GateIneligibleError(f"{path} has no provenance stamp")
    return document["provenance"], document["result"]


def assert_gate_eligible(provenance: dict[str, Any]) -> None:
    """CC3: only stamped artifacts built on real data may pass a gate."""
    if provenance.get("fixture", True):
        raise GateIneligibleError(
            f"artifact from dataset {provenance.get('dataset')!r} is fixture-based "
            "and cannot be used as gate evidence"
        )
    if not provenance.get("manifest_hash"):
        raise GateIneligibleError("artifact has no data manifest hash")
