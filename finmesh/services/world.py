"""The demo world (week 16): real validation data, served through the demo path.

``build_world`` reuses the demo slice's setup (each member's local detector and
calibration, primary-budget alerts, S2 evidence records, and sampled alerts that have
counterparties at other members) and saves it under ``data/demo/<dataset>/``:

* ``records_m<member>.parquet``: each member's evidence store (minimised records only);
* ``alerts.json``: the sampled alerts (member, own account, window, calibrated
  probability, counterparties from the member's own payment data, and the account's own
  features for the console's hint);
* ``meta.json``: dataset, members, level, windows, accounts per member, token budget;
* ``secrets.json`` (mode 0600): the token service's OPRF seed, the request issuer's
  signing key, each bank's key for the token service, and the nodes' admin key. The
  secrets never leave this machine and are never committed (``data/`` is ignored).

``run_world`` serves it: the token service (with its persistent budget ledger) and one
node per member as HTTP apps, and one orchestrator per member, so every message crosses
the wire format and every check. Sessions go to ``sessions.db``, budgets to
``budget.db``; the console and the privacy ledger read both.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from fastapi.testclient import TestClient

from finmesh.demo.slice import ATTRIBUTION_FEATURES, setup_slice
from finmesh.matching.tokens import TokenClient, TokenService, token_budget
from finmesh.paths import DatasetPaths
from finmesh.services.apps import node_app, token_app
from finmesh.services.client import HttpNode, HttpTokenTransport
from finmesh.services.enrich import case_summary
from finmesh.services.orchestrator import Alert, Orchestrator
from finmesh.services.store import BudgetLedger, SessionStore
from finmesh.sharing.node import BankNode
from finmesh.sharing.requests import RequestGuard, RequestIssuer

LEVEL = "S2"  # the frozen G2 headline level


@dataclass
class World:
    folder: Path
    meta: dict[str, Any]
    records: dict[int, pl.DataFrame]
    alerts: list[dict[str, Any]]
    secrets: dict[str, Any]

    def alert(self, a: dict[str, Any]) -> Alert:
        return Alert(
            a["member"],
            a["account"],
            a["window"],
            a["probability"],
            tuple((int(m), int(c)) for m, c in a["counterparties"]),
        )


def new_issuer_key() -> bytes:
    """A fresh Ed25519 signing key for the request issuer (orchestration side only: bank-side
    modules never handle key material, contract CC5)."""
    return Ed25519PrivateKey.generate().private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    )


def issuer_from(raw: bytes) -> RequestIssuer:
    """The request issuer for a stored key, so a restarted demo keeps the nodes' trust."""
    return RequestIssuer(Ed25519PrivateKey.from_private_bytes(raw))


def _write_secret(path: Path, data: dict[str, Any]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)


def build_world(
    paths: DatasetPaths, folder: Path, option: str = "B8", n_alerts: int = 200, seed: int = 0
) -> dict[str, Any]:
    t0 = time.perf_counter()
    w = setup_slice(paths, option, n_alerts, seed)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("records_m*.parquet"):
        old.unlink()
    for m, recs in w["records"].items():
        recs.write_parquet(folder / f"records_m{m}.parquet")
    sides, lookback = w["sides"], w["lookback"]
    alerts: list[dict[str, Any]] = []
    for m, acct, win, row in w["sessions"].select("member", "account", "window", "row").iter_rows():
        cps = (
            sides.filter(
                (pl.col("account") == acct)
                & (pl.col("own") == m)
                & (pl.col("window") <= win)
                & (pl.col("window") > win - lookback)
            )
            .select("cp_member", "cp")
            .unique()
            .sort("cp_member", "cp")
        )
        feats = w["feats_by_row"].get(row, {})
        alerts.append(
            {
                "member": int(m),
                "account": int(acct),
                "window": int(win),
                "probability": float(w["prob"][row]),
                "counterparties": [[int(a), int(b)] for a, b in cps.iter_rows()],
                "features": {k: feats.get(k) for k in ATTRIBUTION_FEATURES},
            }
        )
    alerts.sort(key=lambda a: (a["window"], a["member"], a["account"]))
    (folder / "alerts.json").write_text(json.dumps(alerts))
    apm = {int(m): int(a) for m, a in w["apm"].iter_rows()}
    meta = {
        "dataset": paths.name,
        "option": option,
        "level": LEVEL,
        "members": sorted(int(m) for m in w["records"]),
        "first_window": int(w["v0"]),
        "lookback": int(lookback),
        "accounts_per_member": apm,
        "token_budget": int(token_budget(paths.name)),
        "alerts": len(alerts),
        "seed": seed,
        "setup_seconds": round(time.perf_counter() - t0, 1),
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))
    members = sorted({int(m) for m in w["records"]} | {int(a["member"]) for a in alerts})
    _write_secret(
        folder / "secrets.json",
        {
            "token_seed": secrets.token_bytes(32).hex(),
            "issuer_key": new_issuer_key().hex(),
            "bank_keys": {str(m): secrets.token_bytes(32).hex() for m in members},
            "admin_key": secrets.token_bytes(32).hex(),
        },
    )
    for db in ("sessions.db", "budget.db"):  # a new world starts with an empty history
        for suffix in ("", "-wal", "-shm"):
            (folder / f"{db}{suffix}").unlink(missing_ok=True)
    return meta


def load_world(folder: Path) -> World:
    meta = json.loads((folder / "meta.json").read_text())
    meta["accounts_per_member"] = {int(k): v for k, v in meta["accounts_per_member"].items()}
    records = {
        int(p.stem.removeprefix("records_m")): pl.read_parquet(p)
        for p in sorted(folder.glob("records_m*.parquet"))
    }
    alerts = json.loads((folder / "alerts.json").read_text())
    sec = json.loads((folder / "secrets.json").read_text())
    return World(folder, meta, records, alerts, sec)


def run_world(world: World, limit: int | None = None) -> dict[str, Any]:
    """Every alert through the HTTP services and one orchestrator per member."""
    sec = world.secrets
    keys = {int(m): bytes.fromhex(k) for m, k in sec["bank_keys"].items()}
    admin = bytes.fromhex(sec["admin_key"])
    issuer = issuer_from(bytes.fromhex(sec["issuer_key"]))
    service = TokenService(seed=bytes.fromhex(sec["token_seed"]), budget=world.meta["token_budget"])
    budget = BudgetLedger(world.folder / "budget.db")
    token_http = TestClient(token_app(service, keys, budget))

    def tokens(member: int) -> TokenClient:
        return TokenClient(member, HttpTokenTransport(token_http, member, keys[member]))

    alerts = world.alerts[:limit] if limit else world.alerts
    start = min((a["window"] for a in alerts), default=0)
    nodes: dict[int, HttpNode] = {}
    for m, recs in world.records.items():
        node = BankNode(m, world.meta["level"], tokens(m), RequestGuard(m, issuer.public_key), recs)
        node.build_index()
        nodes[m] = HttpNode(TestClient(node_app(node, admin, clock=start)))
    store = SessionStore(world.folder / "sessions.db")
    feats = {(a["member"], a["account"], a["window"]): a["features"] for a in alerts}

    def enrich(alert: Alert, card: dict[str, Any]) -> dict[str, Any]:
        return case_summary(feats.get((alert.member, alert.account, alert.window), {}), card)

    orchestrators = {
        m: Orchestrator(
            m,
            tokens(m),
            issuer,
            {r: n for r, n in nodes.items() if r != m},
            store,
            first_window=world.meta["first_window"],
            lookback=world.meta["lookback"],
            enrich=enrich,
        )
        for m in sorted({a["member"] for a in alerts})
    }
    latencies, states = [], {"closed": 0, "failed": 0, "other": 0}
    clock = start
    for a in alerts:
        if a["window"] > clock:  # orchestration advances every node's clock, never back
            clock = a["window"]
            for http_node in nodes.values():
                http_node.set_clock(admin, clock)
        t0 = time.perf_counter()
        s = orchestrators[a["member"]].handle(world.alert(a))
        latencies.append(time.perf_counter() - t0)
        states[s["state"] if s["state"] in states else "other"] += 1
    lat = sorted(latencies)
    n = len(lat)
    return {
        "sessions": n,
        "states": states,
        "latency_s": {
            "p50": lat[n // 2] if n else None,
            "p95": lat[min(n - 1, int(0.95 * n))] if n else None,
            "max": lat[-1] if n else None,
        },
    }


__all__ = [
    "LEVEL",
    "World",
    "build_world",
    "issuer_from",
    "load_world",
    "new_issuer_key",
    "run_world",
]
