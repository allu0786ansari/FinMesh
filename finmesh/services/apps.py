"""HTTP services of the demo path: the token service and a bank node (FastAPI).

Both wrap the objects the research harness uses (:class:`TokenService`,
:class:`BankNode`), so the two paths share the protocol logic and differ only in
transport. Every message crossing HTTP is encoded and decoded by
:mod:`finmesh.services.wire`, which applies the allowlist on both sides.

* Token service: ``POST /v1/evaluate`` (BlindedQuery -> BlindedAnswer), authenticated
  per bank (:mod:`finmesh.services.auth`); over budget -> 429.
* Bank node: ``POST /v1/evidence`` (EvidenceRequest -> EvidenceResponse). Requests carry
  the issuer's Ed25519 signature, checked by the node's guard; a refused request is a
  normal ``refused`` response, exactly as in the harness. The node's clock (the current
  6-hour window of the replayed data) is set by orchestration through ``POST
  /admin/clock`` with an admin key, never by the requester.
"""

from __future__ import annotations

import hmac
import json
import threading
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from finmesh.matching.tokens import BudgetExceeded, TokenService
from finmesh.services.auth import AuthError, Verifier
from finmesh.services.store import BudgetLedger
from finmesh.services.wire import decode, encode
from finmesh.sharing.messages import (
    BlindedAnswer,
    BlindedQuery,
    EvidenceRequest,
    MessageRejected,
)
from finmesh.sharing.node import BankNode


async def _json(request: Request) -> tuple[bytes, Any]:
    body = await request.body()
    try:
        return body, json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "body is not JSON") from exc


def token_app(
    service: TokenService, bank_keys: dict[int, bytes], ledger: BudgetLedger | None = None
) -> FastAPI:
    """``ledger`` keeps the per-bank budgets across restarts (week 15 part 2)."""
    app = FastAPI(title="FinMesh token service", docs_url=None, redoc_url=None)
    verifier = Verifier(bank_keys)
    lock = threading.Lock()  # budgets and the nonce cache are shared state

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        return {"service": "token", "status": "ok", "budget": service.budget}

    @app.post("/v1/evaluate")
    async def evaluate(request: Request) -> JSONResponse:
        body, data = await _json(request)
        with lock:
            try:
                bank = verifier.verify(dict(request.headers), body)
            except AuthError as exc:
                raise HTTPException(401, str(exc)) from exc
            try:
                query = decode(data, BlindedQuery)
            except MessageRejected as exc:
                raise HTTPException(400, str(exc)) from exc
            if query.bank != bank:
                raise HTTPException(403, "authenticated bank differs from the query's bank")
            n = len(query.points)
            if ledger is not None:  # the durable count is the truth, not process memory
                service.used[(query.bank, query.epoch)] = ledger.used(query.bank, query.epoch)
            try:
                points = service.evaluate(query.bank, query.epoch, list(query.points))
            except BudgetExceeded as exc:
                if ledger is not None:
                    ledger.record(query.bank, query.epoch, 0, n)
                raise HTTPException(429, str(exc)) from exc
            except ValueError as exc:  # an invalid curve point
                raise HTTPException(400, "invalid blinded point") from exc
            if ledger is not None:
                ledger.record(query.bank, query.epoch, n, 0)
        return JSONResponse(encode(BlindedAnswer(tuple(points))))

    return app


def node_app(node: BankNode, admin_key: bytes, clock: int = 0) -> FastAPI:
    app = FastAPI(title=f"FinMesh bank node {node.member}", docs_url=None, redoc_url=None)
    state = {"now": clock}
    lock = threading.Lock()  # the guard, rate counters and LDP budgets are shared state

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        return {"service": "node", "member": node.member, "level": node.level, "status": "ok"}

    @app.post("/admin/clock")
    async def set_clock(request: Request) -> dict[str, int]:
        given = request.headers.get("x-finmesh-admin", "")
        if not hmac.compare_digest(given.encode(), admin_key.hex().encode()):
            raise HTTPException(401, "admin key required")
        _, data = await _json(request)
        window = data.get("window") if isinstance(data, dict) else None
        if isinstance(window, bool) or not isinstance(window, int) or window < state["now"]:
            raise HTTPException(400, "window must be an integer and must not go back in time")
        state["now"] = window
        return {"now": window}

    @app.post("/v1/evidence")
    async def evidence(request: Request) -> JSONResponse:
        _, data = await _json(request)
        try:
            req = decode(data, EvidenceRequest)
        except MessageRejected as exc:
            raise HTTPException(400, str(exc)) from exc
        with lock:
            response = node.respond(req, now=state["now"])
        return JSONResponse(encode(response))

    return app


__all__ = ["node_app", "token_app"]
