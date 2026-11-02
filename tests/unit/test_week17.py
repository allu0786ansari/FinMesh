"""Week 17: X7 on real processes (smoke world), persistent nonces, process tools."""

from __future__ import annotations

import json
import os
from pathlib import Path

from finmesh.services.cluster import proc_resources
from finmesh.services.nonces import PersistentNonces
from finmesh.services.world import load_world
from finmesh.services.x7 import PHASES, _phases, build_smoke_world, render_x7, run_x7
from finmesh.sharing.requests import RequestGuard, RequestIssuer


def test_nonces_survive_a_restart_so_a_replay_is_still_refused(tmp_path: Path) -> None:
    issuer = RequestIssuer()
    req = issuer.issue(0, 1, b"t" * 16, 0, 0, 9, 3, now=9)
    before = RequestGuard(1, issuer.public_key)
    before.seen = PersistentNonces(tmp_path / "n.db")  # type: ignore[assignment]
    assert before.refuse_reason(req, now=9) is None
    after = RequestGuard(1, issuer.public_key)  # a restarted node process
    after.seen = PersistentNonces(tmp_path / "n.db")  # type: ignore[assignment]
    assert after.refuse_reason(req, now=9) == "replayed"
    assert len(PersistentNonces(tmp_path / "n.db")) == 1 and 5 not in after.seen


def test_phase_split_covers_every_alert_and_every_phase() -> None:
    for n in (5, 24, 200):
        got = _phases(n)
        assert len(got) == n and set(got) == {p for p, _ in PHASES}
        assert got == sorted(got, key=[p for p, _ in PHASES].index)  # phases in order


def test_process_resources_are_read_from_proc() -> None:
    r = proc_resources(os.getpid())
    assert r["peak_rss_mb"] is None or r["peak_rss_mb"] > 10
    assert proc_resources(10**9) == {"peak_rss_mb": None, "cpu_s": None}


def test_x7_smoke_world_passes_every_acceptance_check(tmp_path: Path) -> None:
    world = tmp_path / "world"
    build_smoke_world(world)
    w = load_world(world)
    assert len(w.alerts) == 24 and stat_mode(world / "secrets.json") == 0o600
    r = run_x7(world, tmp_path / "work", node_timeout=1.0)
    failed = [c["criterion"] for c in r["checks"] if not c["passed"]]
    assert not failed, failed
    assert r["final_states"] == {"closed": 24} and r["pt6_met"]
    assert all(v > 0 for v in r["faults"].values())  # every fault really happened
    assert all(p["passed"] for p in r["probes"]) and len(r["probes"]) == 10
    assert r["replay"]["requests_before"] == r["replay"]["requests_after"]
    assert set(r["resources"]) >= {"token", "node0", "orchestration (this process)"}
    page = render_x7(r)
    assert "Engineering acceptance" in page and "**fail**" not in page
    json.dumps(r, default=str)  # the artifact is serialisable


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777
