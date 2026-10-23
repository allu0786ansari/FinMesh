from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from finmesh.data.manifest import Manifest, load_manifest, sha256_file
from finmesh.eval.provenance import (
    GateIneligibleError,
    Stamp,
    assert_gate_eligible,
    read_artifact,
    write_artifact,
)
from finmesh.paths import DatasetPaths


def test_sha256_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "f.bin"
    path.write_bytes(b"finmesh" * 100_000)
    assert sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_round_trip_and_tamper(
    fixture_paths: DatasetPaths, ingested: dict[str, object]
) -> None:
    manifest = load_manifest(fixture_paths.manifest)
    assert manifest.fixture is True
    roles = {f.role for f in manifest.files}
    assert {"raw_transactions", "raw_patterns", "transactions", "scheme_links", "schemes"} <= roles
    assert manifest.manifest_hash == ingested["manifest_hash"]

    raw = json.loads(fixture_paths.manifest.read_text())
    raw["files"][0]["sha256"] = "0" * 64
    tampered = fixture_paths.manifest.with_name("tampered.json")
    tampered.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_manifest(tampered)


def test_manifest_hash_ignores_paths_and_time(tmp_path: Path) -> None:
    f = tmp_path / "a.csv"
    f.write_text("x")
    one, two = Manifest("D", fixture=False), Manifest("D", fixture=False)
    one.add("raw", f)
    two.add("raw", f, relative_to=tmp_path)
    two.created_at = "2000-01-01T00:00:00+00:00"
    assert one.manifest_hash == two.manifest_hash


def test_fixture_artifacts_cannot_pass_a_gate(tmp_path: Path) -> None:
    fixture_stamp = Stamp(kind="x", dataset="FIXTURE-Small", manifest_hash="abc", fixture=True)
    path = write_artifact(tmp_path / "a.json", fixture_stamp, {"value": 1})
    provenance, result = read_artifact(path)
    assert result == {"value": 1}
    with pytest.raises(GateIneligibleError):
        assert_gate_eligible(provenance)

    real = Stamp(kind="x", dataset="HI-Small", manifest_hash="abc", fixture=False).to_dict()
    assert_gate_eligible(real)
    with pytest.raises(GateIneligibleError):
        assert_gate_eligible({**real, "manifest_hash": ""})


def test_unstamped_artifact_rejected(tmp_path: Path) -> None:
    path = tmp_path / "plain.json"
    path.write_text(json.dumps({"value": 1}))
    with pytest.raises(GateIneligibleError):
        read_artifact(path)
