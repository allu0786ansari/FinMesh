"""Process entry points for the demo path's services (uvicorn factories).

The token service reads its configuration from the environment, so its secret seed and
the banks' keys never appear on a command line (where other users could read them):

* ``FINMESH_TOKEN_SEED``: 64 hex characters, the OPRF key seed;
* ``FINMESH_BANK_KEYS``: JSON object ``{"<bank>": "<hex key>"}``;
* ``FINMESH_TOKEN_BUDGET`` (optional): evaluations per bank and epoch;
* ``FINMESH_TOKEN_LEDGER`` (optional): SQLite file that keeps the budgets across restarts.

Run it with ``uvicorn --factory finmesh.services.run:token_app_from_env``.

A bank node (``node_app_from_env``) reads a demo world (week 16) and its own member id:

* ``FINMESH_WORLD``: the world folder (records, meta, secrets);
* ``FINMESH_MEMBER``: this node's member id;
* ``FINMESH_TOKEN_URL``: the token service, used to build the node's token index;
* ``FINMESH_NODE_STATE`` (optional): SQLite file for the nonces the node has answered, so a
  restarted node still refuses a replayed request;
* ``FINMESH_NODE_CLOCK`` (optional): the starting window; ``FINMESH_NODE_DELAY`` (optional,
  X7 slow-node scenario only): seconds before each answer.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI

from finmesh.matching.tokens import QUERY_BUDGET, TokenClient, TokenService
from finmesh.services.apps import node_app, token_app
from finmesh.services.store import BudgetLedger


def token_app_from_env() -> FastAPI:
    seed_hex = os.environ.get("FINMESH_TOKEN_SEED", "")
    if len(seed_hex) != 64:
        raise RuntimeError("FINMESH_TOKEN_SEED must be 64 hex characters")
    keys = {
        int(b): bytes.fromhex(k) for b, k in json.loads(os.environ["FINMESH_BANK_KEYS"]).items()
    }
    budget = int(os.environ.get("FINMESH_TOKEN_BUDGET", QUERY_BUDGET))
    ledger_path = os.environ.get("FINMESH_TOKEN_LEDGER")
    ledger = BudgetLedger(ledger_path) if ledger_path else None
    return token_app(TokenService(seed=bytes.fromhex(seed_hex), budget=budget), keys, ledger)


def node_app_from_env() -> FastAPI:
    import httpx2

    from finmesh.services.client import HttpTokenTransport
    from finmesh.services.nonces import PersistentNonces
    from finmesh.services.world import issuer_from, load_world
    from finmesh.sharing.node import BankNode
    from finmesh.sharing.requests import RequestGuard

    world = load_world(Path(os.environ["FINMESH_WORLD"]))
    member = int(os.environ["FINMESH_MEMBER"])
    sec = world.secrets
    key = bytes.fromhex(sec["bank_keys"][str(member)])
    http = httpx2.Client(base_url=os.environ["FINMESH_TOKEN_URL"], timeout=60)
    tokens = TokenClient(member, HttpTokenTransport(http, member, key))
    issuer_public = issuer_from(bytes.fromhex(sec["issuer_key"])).public_key
    guard = RequestGuard(member, issuer_public)
    state = os.environ.get("FINMESH_NODE_STATE")
    if state:
        guard.seen = PersistentNonces(state)  # type: ignore[assignment]
    node = BankNode(member, world.meta["level"], tokens, guard, world.records[member])
    node.build_index()
    return node_app(
        node,
        bytes.fromhex(sec["admin_key"]),
        clock=int(os.environ.get("FINMESH_NODE_CLOCK", "0")),
        delay=float(os.environ.get("FINMESH_NODE_DELAY", "0")),
    )


__all__ = ["node_app_from_env", "token_app_from_env"]
