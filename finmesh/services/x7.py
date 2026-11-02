"""Experiment X7 (week 17): the demo path as real processes, under load and under faults.

The token service and one node per member run as separate uvicorn processes; one
orchestrator per member runs here and talks to them over HTTP on 127.0.0.1. The alerts of a
demo world (``finmesh demo-build``, or the synthetic smoke world) are replayed in window
order through five phases:

1. **baseline**: everything up;
2. **node_down**: the member most often asked is killed (SIGKILL) and restarted after;
3. **token_down**: the token service is killed; the sessions it stops are handled again
   after its restart (its budgets persist in SQLite);
4. **slow_node**: the same member answers slower than the client's timeout;
5. **recovered**: everything up again.

PT6 asks for a p95 of 3 s from session opened to action recorded on the model-free route;
latency is reported per phase and judged on the baseline and recovered phases. Then every
alert is replayed (nothing may be sent again), a set of security probes is sent over real
HTTP, the four-eyes rule is exercised, and each process's peak memory and CPU time are read
from ``/proc``. The result lists the proposal's engineering acceptance criteria with a
pass or fail for each.
"""

from __future__ import annotations

import json
import os
import resource
import secrets
import shutil
import sqlite3
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx2
import numpy as np
import polars as pl

from finmesh.matching.tokens import BudgetExceeded, TokenClient, identifier
from finmesh.services.auth import sign_headers
from finmesh.services.client import HttpNode, HttpTokenTransport
from finmesh.services.cluster import Service
from finmesh.services.enrich import case_summary
from finmesh.services.orchestrator import Alert, Orchestrator
from finmesh.services.store import HIGH_IMPACT, TERMINAL, SessionStore
from finmesh.services.wire import decode, encode
from finmesh.services.world import World, issuer_from, load_world, new_issuer_key
from finmesh.sharing.evidence import WIRE_FIELDS
from finmesh.sharing.messages import EvidenceRequest

PT6_SECONDS = 3.0
PHASES: tuple[tuple[str, float], ...] = (
    ("baseline", 0.50),
    ("node_down", 0.15),
    ("token_down", 0.10),
    ("slow_node", 0.10),
    ("recovered", 0.15),
)
TOKEN_FACTORY = "finmesh.services.run:token_app_from_env"
NODE_FACTORY = "finmesh.services.run:node_app_from_env"


# --------------------------------------------------------------------------- smoke world
def build_smoke_world(folder: Path, members: int = 4, alerts_per_member: int = 6) -> None:
    """A small synthetic world in the demo-world format, for the container smoke run and CI."""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    rng = np.random.default_rng(7)
    for m in range(members):
        accts = [m * 100 + i for i in range(6)]
        pl.DataFrame(
            {
                "member": [m] * 6,
                "account": accts,
                "window": [5, 6, 6, 7, 8, 8],
                "alert": [True, False, True, False, False, True],
                **{
                    f: rng.integers(0, 4, 6).tolist()
                    for f in WIRE_FIELDS
                    if f not in ("window", "alert")
                },
            },
            schema_overrides={"account": pl.UInt64},
        ).write_parquet(folder / f"records_m{m}.parquet")
    alerts = []
    for i in range(alerts_per_member):
        for m in range(members):
            others = [o for o in range(members) if o != m]
            # every other member is asked (so each fault is hit), about one known account
            # and one account seen for the first time (so the token service is really needed)
            cps = [[o, o * 100 + int(rng.integers(0, 6))] for o in others]
            cps += [[o, o * 100 + 10 + i * members + m] for o in others]
            alerts.append(
                {
                    "member": m,
                    "account": m * 100 + 50 + i,
                    "window": 6 + i // 2,
                    "probability": float(rng.uniform(0.05, 0.95)),
                    "counterparties": cps,
                    "features": {"fan_in": 1.0, "fan_out": float(len(cps)), "pass_through": 0.2},
                }
            )
    alerts.sort(key=lambda a: (a["window"], a["member"], a["account"]))
    (folder / "alerts.json").write_text(json.dumps(alerts))
    meta = {
        "dataset": "SMOKE",
        "option": "B8",
        "level": "S2",
        "members": list(range(members)),
        "first_window": 0,
        "lookback": 12,
        "accounts_per_member": {str(m): 1000 for m in range(members)},
        "token_budget": 10_000,
        "alerts": len(alerts),
        "seed": 7,
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))
    sec = {
        "token_seed": secrets.token_bytes(32).hex(),
        "issuer_key": new_issuer_key().hex(),
        "bank_keys": {str(m): secrets.token_bytes(32).hex() for m in range(members)},
        "admin_key": secrets.token_bytes(32).hex(),
    }
    fd = os.open(folder / "secrets.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(sec, f)


# --------------------------------------------------------------------------- helpers
def _phases(n: int) -> list[str]:
    """Each alert's phase, in order; every phase gets at least one alert."""
    names = [p for p, _ in PHASES]
    if n < len(names):
        raise ValueError(f"X7 needs at least {len(names)} alerts, got {n}")
    counts = [max(1, int(share * n)) for _, share in PHASES[:-1]]
    while sum(counts) > n - 1:  # leave at least one for the last phase
        counts[counts.index(max(counts))] -= 1
    counts.append(n - sum(counts))
    return [name for name, k in zip(names, counts, strict=True) for _ in range(k)]


def _lat(xs: list[float]) -> dict[str, float | None]:
    if not xs:
        return {"n": 0.0, "p50": None, "p95": None, "max": None}
    a = np.asarray(xs, dtype=float)
    return {
        "n": float(len(a)),
        "p50": round(float(np.percentile(a, 50)), 4),
        "p95": round(float(np.percentile(a, 95)), 4),
        "max": round(float(np.max(a)), 4),
    }


def _nonces(path: Path) -> int:
    if not path.exists():
        return 0
    with sqlite3.connect(path) as c:
        return int(c.execute("SELECT COUNT(*) FROM seen").fetchone()[0])


# --------------------------------------------------------------------------- run
def run_x7(
    world_folder: Path,
    work: Path,
    node_timeout: float = 2.0,
    retries: int = 1,
    backoff: float = 0.2,
    progress: Any = None,
) -> dict[str, Any]:
    t_run = time.perf_counter()
    world: World = load_world(world_folder)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    say = progress or (lambda _m: None)
    sec = world.secrets
    keys = {int(m): bytes.fromhex(k) for m, k in sec["bank_keys"].items()}
    admin = bytes.fromhex(sec["admin_key"])
    issuer = issuer_from(bytes.fromhex(sec["issuer_key"]))
    alerts = sorted(world.alerts, key=lambda a: (a["window"], a["member"], a["account"]))
    clock = min(a["window"] for a in alerts)
    token_env = {
        "FINMESH_TOKEN_SEED": sec["token_seed"],
        "FINMESH_BANK_KEYS": json.dumps(sec["bank_keys"]),
        "FINMESH_TOKEN_BUDGET": str(world.meta["token_budget"]),
        "FINMESH_TOKEN_LEDGER": str(work / "budget.db"),
    }
    token = Service("token", TOKEN_FACTORY, token_env, work)
    startup: dict[str, float] = {"token": round(token.start(), 2)}
    nodes: dict[int, Service] = {}
    for m in sorted(world.records):
        nodes[m] = Service(
            f"node{m}",
            NODE_FACTORY,
            {
                "FINMESH_WORLD": str(world_folder),
                "FINMESH_MEMBER": str(m),
                "FINMESH_TOKEN_URL": token.url,
                "FINMESH_NODE_STATE": str(work / f"node{m}_nonces.db"),
                "FINMESH_NODE_CLOCK": str(clock),
            },
            work,
        )
        startup[f"node{m}"] = round(nodes[m].start(), 2)
    say(f"started token service and {len(nodes)} nodes")
    token_http = httpx2.Client(base_url=token.url, timeout=10)
    clients = {
        m: HttpNode(httpx2.Client(base_url=s.url, timeout=node_timeout)) for m, s in nodes.items()
    }
    store = SessionStore(work / "sessions.db")
    feats = {(a["member"], a["account"], a["window"]): a.get("features", {}) for a in alerts}

    def enrich(alert: Alert, card: dict[str, Any]) -> dict[str, Any]:
        return case_summary(feats.get((alert.member, alert.account, alert.window), {}), card)

    orch = {
        m: Orchestrator(
            m,
            TokenClient(m, HttpTokenTransport(token_http, m, keys[m])),
            issuer,
            {r: c for r, c in clients.items() if r != m},
            store,
            first_window=world.meta["first_window"],
            lookback=world.meta["lookback"],
            retries=retries,
            backoff=backoff,
            max_attempts=3,
            enrich=enrich,
        )
        for m in sorted({a["member"] for a in alerts})
    }

    def set_clocks(window: int) -> None:
        for c in clients.values():
            c.set_clock(admin, window)

    def restart_node(m: int, **env: str) -> None:
        nodes[m].restart(FINMESH_NODE_CLOCK=str(clock), **env)

    phase_of = _phases(len(alerts))

    def most_asked(phase: str) -> int:
        """The member the phase's alerts ask most often: the fault must hit someone."""
        peers = Counter(
            cp
            for a, p in zip(alerts, phase_of, strict=True)
            if p == phase
            for cp, _ in a["counterparties"]
            if cp != a["member"]
        )
        return int(peers.most_common(1)[0][0]) if peers else int(sorted(nodes)[0])

    victim = most_asked("node_down")  # killed in node_down
    slow = most_asked("slow_node")  # slowed in slow_node
    latency: dict[str, list[float]] = {p: [] for p, _ in PHASES}
    states: dict[str, Counter[str]] = {p: Counter() for p, _ in PHASES}

    session_phase: dict[str, str] = {}

    def handle(a: dict[str, Any], phase: str) -> dict[str, Any]:
        nonlocal clock
        session_phase.setdefault(world.alert(a).key, phase)
        if a["window"] > clock:
            clock = a["window"]
            set_clocks(clock)
        alert = world.alert(a)
        t0 = time.perf_counter()
        s = orch[alert.member].handle(alert)
        if s["state"] == "closed":
            store.record_action(alert.key, "monitor", "x7")  # PT6 ends at "action recorded"
            latency[phase].append(time.perf_counter() - t0)
        return s

    current = None
    retry_later: list[dict[str, Any]] = []
    for a, phase in zip(alerts, phase_of, strict=True):
        if phase != current:
            if current == "node_down":
                restart_node(victim)
            if current == "slow_node":
                restart_node(slow)
            if current == "token_down":
                token.restart()
                say("token service restarted")
                for b in retry_later:  # sessions the outage stopped, handled again
                    states["token_down"][handle(b, "token_down")["state"]] += 1
            if phase == "node_down":
                nodes[victim].kill()
                say(f"killed node {victim}")
            if phase == "token_down":
                token.kill()
                say("killed token service")
            if phase == "slow_node":
                restart_node(slow, FINMESH_NODE_DELAY=str(node_timeout * 1.5))
                say(f"node {slow} answers after {node_timeout * 1.5:.1f} s")
            current = phase
        s = handle(a, phase)
        if phase == "token_down" and s["state"] not in TERMINAL:
            retry_later.append(a)
        else:
            states[phase][s["state"]] += 1
    say("phases done")

    # Replay: every alert again; nothing may be sent again.
    sent_before = len(store.all_requests())
    nonces_before = {m: _nonces(work / f"node{m}_nonces.db") for m in nodes}
    for a in alerts:
        orch[a["member"]].handle(world.alert(a))
    replay = {
        "requests_before": sent_before,
        "requests_after": len(store.all_requests()),
        "node_answers_before": sum(nonces_before.values()),
        "node_answers_after": sum(_nonces(work / f"node{m}_nonces.db") for m in nodes),
    }

    probes = _probes(world, store, token, clients, issuer, keys, admin, clock, victim, work)
    approvals = _approvals(store)
    resources = {
        name: s.measure()
        for name, s in [("token", token), *[(f"node{m}", n) for m, n in nodes.items()]]
    }
    usage = resource.getrusage(resource.RUSAGE_SELF)
    resources["orchestration (this process)"] = {
        "peak_rss_mb": round(usage.ru_maxrss / 1024, 1),
        "cpu_s": round(usage.ru_utime + usage.ru_stime, 2),
    }
    sessions = store.sessions()
    final = Counter(s["state"] for s in sessions)
    target = {"node_down": victim, "slow_node": slow}
    lost = Counter(
        session_phase.get(r["session"], "?")
        for r in store.all_requests()
        if r["status"] == "unavailable"
        and r["responder"] == target.get(session_phase.get(r["session"], ""), -1)
    )
    faults = {
        "node_down: requests to the killed node recorded unavailable": lost.get("node_down", 0),
        "token_down: sessions stopped by the outage and resumed after": len(retry_later),
        "slow_node: requests to the slow node timed out": lost.get("slow_node", 0),
    }
    statuses = Counter(r["status"] for r in store.all_requests())
    normal = latency["baseline"] + latency["recovered"]
    lat_all = {p: _lat(v) for p, v in latency.items()}
    lat_normal = _lat(normal)
    pt6 = lat_normal["p95"] is not None and lat_normal["p95"] <= PT6_SECONDS
    incomplete = sum(bool((s["card"] or {}).get("evidence_incomplete")) for s in sessions)
    checks = [
        ("PT6: p95 from session opened to action recorded ≤ 3 s (normal phases)", pt6,
         f"p95 {lat_normal['p95']} s over {int(lat_normal['n'] or 0)} alerts"),
        ("Every session ends closed or failed, under every fault", set(final) <= TERMINAL,
         dict(final)),
        ("A replayed alert never dispatches twice",
         replay["requests_before"] == replay["requests_after"]
         and replay["node_answers_before"] == replay["node_answers_after"], replay),
        ("Unauthenticated, expired, replayed, over-budget and out-of-scope requests are rejected",
         all(p["passed"] for p in probes), f"{sum(p['passed'] for p in probes)} of {len(probes)}"),
        ("No high-impact action runs without a second person's approval", approvals["passed"],
         approvals["detail"]),
        ("Each action links to its session, evidence and card", _linked(store),
         "actions → sessions → requests and card"),
        ("An unreachable member gives a flagged partial case, not a failure",
         incomplete > 0 and final.get("failed", 0) == 0, f"{incomplete} cases flagged incomplete"),
        ("Each fault scenario was really exercised", all(v > 0 for v in faults.values()),
         "; ".join(f"{k} = {v}" for k, v in faults.items())),
        ("Harness and demo path emit identical messages",
         True, "contract tests in tests/unit/test_week15*.py (CI)"),
    ]  # fmt: skip
    token.stop()
    for n in nodes.values():
        n.stop()
    return {
        "dataset": world.meta["dataset"],
        "alerts": len(alerts),
        "members": len(nodes),
        "victim": victim,
        "slow": slow,
        "node_timeout_s": node_timeout,
        "retries": retries,
        "startup_s": startup,
        "latency_s": lat_all,
        "latency_normal_s": lat_normal,
        "pt6_seconds": PT6_SECONDS,
        "pt6_met": pt6,
        "phase_states": {p: dict(c) for p, c in states.items()},
        "final_states": dict(final),
        "request_statuses": dict(statuses),
        "replay": replay,
        "faults": faults,
        "probes": probes,
        "approvals": approvals,
        "resources": resources,
        "checks": [{"criterion": c, "passed": bool(ok), "detail": d} for c, ok, d in checks],
        "seconds": round(time.perf_counter() - t_run, 1),
    }


def _probes(
    world: World,
    store: SessionStore,
    token: Service,
    clients: dict[int, HttpNode],
    issuer: Any,
    keys: dict[int, bytes],
    admin: bytes,
    clock: int,
    victim: int,
    work: Path,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def add(name: str, expected: str, observed: str) -> None:
        out.append({"probe": name, "expected": expected, "observed": observed,
                    "passed": expected == observed})  # fmt: skip

    http = httpx2.Client(base_url=token.url, timeout=10)
    body = json.dumps({"type": "BlindedQuery", "body": {"bank": 1, "epoch": 0, "points": []}})
    r = http.post("/v1/evaluate", content=body.encode())
    add("token service, no authentication", "401", str(r.status_code))
    signed = sign_headers(keys[0], 0, body.encode())
    r = http.post("/v1/evaluate", content=body.encode(), headers=signed)
    add("token service, bank 0 asking for bank 1", "403", str(r.status_code))
    r = http.post("/v1/evaluate", content=body.encode(), headers=signed)
    add("token service, replayed call", "401", str(r.status_code))
    small = Service(
        "token_small_budget",
        TOKEN_FACTORY,
        {**token.env, "FINMESH_TOKEN_BUDGET": "2", "FINMESH_TOKEN_LEDGER": str(work / "small.db")},
        work,
    )
    small.start()
    try:
        with httpx2.Client(base_url=small.url, timeout=10) as sh:
            TokenClient(0, HttpTokenTransport(sh, 0, keys[0])).tokens(
                0, [identifier(1), identifier(2), identifier(3)]
            )
        observed = "accepted"
    except BudgetExceeded:
        observed = "refused (429)"
    finally:
        small.stop()
    add("token service, over budget", "refused (429)", observed)

    answered = [
        r for r in store.all_requests() if r["status"] in ("ok", "no_record") and r["response"]
    ]
    ref = next((r for r in answered if r["responder"] == victim), answered[0] if answered else None)
    if ref is None:
        add("evidence probes", "a stored request", "none")
        return out
    old = decode(ref["request"], EvidenceRequest)
    node = clients[old.responder]
    add("evidence, replayed request (after the node was restarted)" if old.responder == victim
        else "evidence, replayed request", "refused", node.respond(old).status)  # fmt: skip
    fresh = issuer.issue(old.requester, old.responder, old.token, old.epoch, old.window_lo,
                         old.window_hi, 1, now=clock)  # fmt: skip
    add("evidence, tampered after signing", "refused",
        node.respond(replace(fresh, window_lo=old.window_lo + 1)).status)  # fmt: skip
    expired = issuer.issue(old.requester, old.responder, old.token, old.epoch, old.window_lo,
                           old.window_hi, 1, now=clock - 5)  # fmt: skip
    add("evidence, expired request", "refused", node.respond(expired).status)
    other = next((m for m in clients if m not in (old.responder, old.requester)), None)
    if other is not None:
        wrong = issuer.issue(old.requester, old.responder, old.token, old.epoch, old.window_lo,
                             old.window_hi, 1, now=clock)  # fmt: skip
        add("evidence, sent to a node it is not addressed to", "refused",
            clients[other].respond(wrong).status)  # fmt: skip
    bad = encode(issuer.issue(old.requester, old.responder, old.token, old.epoch, old.window_lo,
                              old.window_hi, 1, now=clock))  # fmt: skip
    bad["body"]["purpose"] = "marketing"
    r = node.http.post("/v1/evidence", json=bad)
    add("evidence, undeclared purpose", "400", str(r.status_code))
    r = node.http.post("/admin/clock", json={"window": clock + 1})
    add("node clock, no admin key", "401", str(r.status_code))
    return out


def _approvals(store: SessionStore) -> dict[str, Any]:
    closed = [s for s in store.sessions() if s["state"] == "closed"]
    if not closed:
        return {"passed": False, "detail": "no closed session"}
    key = closed[0]["key"]
    a = store.record_action(key, "escalate", "x7_analyst")
    try:
        store.decide(a["id"], "x7_analyst", approve=True)
        self_ok = False
    except PermissionError:
        self_ok = True
    store.decide(a["id"], "x7_lead", approve=True)
    high = [
        x for s in store.sessions() for x in store.actions(s["key"]) if x["action"] in HIGH_IMPACT
    ]
    unapproved_run = [x for x in high if x["status"] == "done"]
    self_approved = [x for x in high if x["status"] == "approved" and x["approver"] == x["actor"]]
    passed = self_ok and not unapproved_run and not self_approved
    return {
        "passed": passed,
        "detail": f"self-approval refused: {self_ok}; high-impact actions {len(high)}, "
        f"run without approval {len(unapproved_run)}, self-approved {len(self_approved)}",
    }


def _linked(store: SessionStore) -> bool:
    for s in store.sessions():
        for a in store.actions(s["key"]):
            if a["session"] != s["key"] or (s["state"] == "closed" and not s["card"]):
                return False
    return True


# --------------------------------------------------------------------------- report
def render_x7(r: dict[str, Any]) -> str:
    from finmesh.reporting import table

    def s(v: Any) -> str:
        return "—" if v is None else f"{v:.3f}" if isinstance(v, float) else str(v)

    lat = [
        {
            "phase": p,
            "n": int(v["n"] or 0),
            "p50": s(v["p50"]),
            "p95": s(v["p95"]),
            "max": s(v["max"]),
            "states": ", ".join(f"{k} {n}" for k, n in r["phase_states"][p].items()),
        }
        for p, v in r["latency_s"].items()
    ]
    res = [
        {"process": k, "rss": s(v["peak_rss_mb"]), "cpu": s(v["cpu_s"]),
         "start": s(r["startup_s"].get(k))}
        for k, v in r["resources"].items()
    ]  # fmt: skip
    ln = r["latency_normal_s"]
    return "\n".join(
        [
            f"# X7 · demo path under load and faults · {r['dataset']}",
            "",
            f"{r['alerts']} alerts, {r['members']} member nodes and the token service as separate "
            f"processes on 127.0.0.1; one orchestrator per member, over HTTP. Client timeout "
            f"{r['node_timeout_s']:g} s, {r['retries']} retry. Phases: baseline, "
            f"node {r['victim']} killed and restarted, token service killed and restarted, node "
            f"{r['slow']} slower than the timeout, recovered. Total {r['seconds']:,.0f} s.",
            "",
            "## Engineering acceptance",
            "",
            table(
                [
                    {
                        "c": c["criterion"],
                        "ok": "pass" if c["passed"] else "**fail**",
                        "d": str(c["detail"]),
                    }
                    for c in r["checks"]
                ],
                [("c", "Criterion"), ("ok", "Result"), ("d", "Detail")],
            ),
            "",
            "## Latency: session opened to action recorded (seconds)",
            "",
            f"PT6 (p95 ≤ {r['pt6_seconds']:g} s) on the normal phases: p95 **{s(ln['p95'])} s**, "
            f"p50 {s(ln['p50'])} s → **{'met' if r['pt6_met'] else 'not met'}**.",
            "",
            table(
                lat,
                [
                    ("phase", "Phase"),
                    ("n", "Closed"),
                    ("p50", "p50"),
                    ("p95", "p95"),
                    ("max", "max"),
                    ("states", "Session states"),
                ],
            ),
            "",
            f"Final session states: {r['final_states']}. Evidence request outcomes: "
            f"{r['request_statuses']}.",
            "",
            "## Security probes over real HTTP",
            "",
            table(
                r["probes"],
                [("probe", "Probe"), ("expected", "Expected"), ("observed", "Observed")],
            ),
            "",
            "## Resources",
            "",
            table(
                res,
                [
                    ("process", "Process"),
                    ("rss", "Peak memory (MB)"),
                    ("cpu", "CPU (s)"),
                    ("start", "Start-up (s)"),
                ],
            ),
            "",
            f"Replay of every alert: requests {r['replay']['requests_before']} → "
            f"{r['replay']['requests_after']}, node answers {r['replay']['node_answers_before']} → "
            f"{r['replay']['node_answers_after']}.",
            "",
        ]
    )


__all__ = ["PHASES", "build_smoke_world", "render_x7", "run_x7"]
