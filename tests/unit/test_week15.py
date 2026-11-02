"""Week 15: the demo path's wire format, authentication and services, and the contract test
that the HTTP path and the in-process harness emit identical messages for the same inputs."""

from __future__ import annotations

import json
from dataclasses import replace

import httpx
import polars as pl
import pytest
from fastapi.testclient import TestClient

from finmesh.matching.tokens import BudgetExceeded, TokenClient, TokenService, identifier
from finmesh.services.apps import node_app, token_app
from finmesh.services.auth import AuthError, Verifier, sign_headers
from finmesh.services.client import HttpNode, HttpTokenTransport, ServiceError
from finmesh.services.wire import decode, encode
from finmesh.sharing.evidence import WIRE_FIELDS
from finmesh.sharing.messages import (
    BlindedAnswer,
    BlindedQuery,
    EvidenceRecordWire,
    EvidenceRequest,
    EvidenceResponse,
    MessageRejected,
)
from finmesh.sharing.node import BankNode
from finmesh.sharing.requests import RequestGuard, RequestIssuer

KEYS = {0: b"k0" * 16, 1: b"k1" * 16}
ADMIN = b"admin-key-0123456789abcdef"


# --------------------------------------------------------------------------- wire
def test_wire_round_trips_every_allowlisted_message() -> None:
    issuer = RequestIssuer()
    req = issuer.issue(0, 1, b"\x01" * 16, 3, 10, 14, 2, now=14)
    for msg, cls in (
        (BlindedQuery(0, 3, (b"\x02" * 32, b"\x03" * 32)), BlindedQuery),
        (BlindedAnswer((b"\x04" * 32,)), BlindedAnswer),
        (req, EvidenceRequest),
        (EvidenceResponse(1, 1, "S1", "ok", True, 12), EvidenceResponse),
        (
            EvidenceResponse(1, 1, "S2", "ok", True, 12, EvidenceRecordWire(b"t", (1, 2))),
            EvidenceResponse,
        ),
        (EvidenceResponse(2, 1, "S2", "refused"), EvidenceResponse),
    ):
        data = json.loads(json.dumps(encode(msg)))  # through real JSON
        assert decode(data, cls) == msg


def test_wire_rejects_anything_outside_the_contract() -> None:
    good = encode(EvidenceResponse(1, 1, "S2", "ok", True, 12, EvidenceRecordWire(b"t", (1, 2))))
    without_level = {k: v for k, v in good["body"].items() if k != "level"}
    bad_cases = [
        {"type": "EvidenceRequest", "body": good["body"]},  # wrong type for the endpoint
        {"type": "EvidenceResponse", "body": {**good["body"], "account": 7}},  # extra field
        {"type": "EvidenceResponse", "body": without_level},  # missing field
        {"type": "EvidenceResponse", "body": {**good["body"], "request_id": 1.5}},  # float
        {"type": "EvidenceResponse", "body": {**good["body"], "request_id": True}},  # bool as int
        {"type": "EvidenceResponse", "body": {**good["body"], "level": "S0"}},  # policy: S0 silent
        {"type": "EvidenceResponse", "body": {**good["body"], "level": "S1"}},  # S1 has no record
        {"type": "EvidenceResponse",
         "body": {**good["body"], "record": {"token": "zz", "values": [1]}}},  # not hex
        {"type": "EvidenceResponse", "extra": 1, "body": good["body"]},
    ]  # fmt: skip
    for case in bad_cases:
        with pytest.raises(MessageRejected):
            decode(case, EvidenceResponse)
    with pytest.raises(MessageRejected):
        encode(object())  # not allowlisted


# --------------------------------------------------------------------------- auth
def test_token_service_authentication() -> None:
    v = Verifier(KEYS)
    body = b'{"x": 1}'
    h = sign_headers(KEYS[0], 0, body, now=1000)
    assert v.verify(h, body, now=1010) == 0
    with pytest.raises(AuthError, match="replayed"):
        v.verify(h, body, now=1010)
    for headers, now, msg in (
        (sign_headers(KEYS[0], 0, body, now=1000), 1500, "stale"),
        (sign_headers(KEYS[1], 0, body, now=1000), 1000, "bad signature"),  # wrong key
        (sign_headers(KEYS[0], 9, body, now=1000), 1000, "unknown bank"),
        ({}, 1000, "missing"),
    ):
        with pytest.raises(AuthError, match=msg):
            v.verify(headers, body, now=now)
    tampered = sign_headers(KEYS[0], 0, body, now=1000)
    with pytest.raises(AuthError, match="bad signature"):
        v.verify(tampered, b'{"x": 2}', now=1000)  # body changed after signing


# --------------------------------------------------------------------------- token service
def _token_http(service: TokenService, bank: int) -> tuple[TokenClient, TestClient]:
    http = TestClient(token_app(service, KEYS))
    return TokenClient(bank, HttpTokenTransport(http, bank, KEYS[bank])), http


def test_http_tokens_equal_in_process_tokens() -> None:
    idents = [identifier(a) for a in (20, 21, 22)]
    local = TokenClient(0, TokenService(seed=b"\x05" * 32).evaluate).tokens(4, idents)
    remote, _ = _token_http(TokenService(seed=b"\x05" * 32), 0)
    assert remote.tokens(4, idents) == local  # contract: same seed, same tokens


def test_token_service_refuses_over_budget_unauthenticated_and_impersonating_calls() -> None:
    service = TokenService(seed=b"\x06" * 32, budget=2)
    remote, http = _token_http(service, 0)
    remote.tokens(0, [identifier(1), identifier(2)])
    with pytest.raises(BudgetExceeded):
        remote.tokens(0, [identifier(3)])
    body = json.dumps(encode(BlindedQuery(1, 0, (b"\x02" * 32,)))).encode()
    assert http.post("/v1/evaluate", content=body).status_code == 401  # no authentication
    as_bank0 = sign_headers(KEYS[0], 0, body)  # bank 0 asking on behalf of bank 1
    assert http.post("/v1/evaluate", content=body, headers=as_bank0).status_code == 403
    assert http.post("/v1/evaluate", content=body, headers=as_bank0).status_code == 401  # replay
    garbage = json.dumps(encode(BlindedQuery(0, 1, (b"\x00" * 32,)))).encode()
    r = http.post("/v1/evaluate", content=garbage, headers=sign_headers(KEYS[0], 0, garbage))
    assert r.status_code == 400  # not a valid curve point
    assert http.get("/v1/health").json()["status"] == "ok"


# --------------------------------------------------------------------------- bank node
def _node(level: str, service: TokenService, issuer: RequestIssuer) -> BankNode:
    recs = pl.DataFrame(
        {
            "member": [1, 1, 1],
            "account": [20, 20, 21],
            "window": [5, 9, 7],
            "alert": [True, False, False],
            **{f: [1, 2, 3] for f in WIRE_FIELDS if f not in ("window", "alert")},
        },
        schema_overrides={"account": pl.UInt64},
    )
    node = BankNode(1, level, TokenClient(1, service.evaluate), RequestGuard(1, issuer.public_key),
                    recs)  # fmt: skip
    node.build_index()
    return node


@pytest.mark.parametrize("level", ["S1", "S2", "PD"])
def test_http_node_answers_exactly_as_the_in_process_node(level: str) -> None:
    service = TokenService(seed=b"\x07" * 32)
    issuer = RequestIssuer()
    local = _node(level, service, issuer)
    remote_node = _node(level, service, issuer)
    if level == "PD":
        local.tau = remote_node.tau = 3
    remote = HttpNode(TestClient(node_app(remote_node, ADMIN, clock=9)))
    asker = TokenClient(0, service.evaluate)
    t20, t21, t99 = asker.tokens(0, [identifier(20), identifier(21), identifier(99)])
    requests = [
        issuer.issue(0, 1, t20, 0, 0, 9, 3, now=9),
        issuer.issue(0, 1, t20, 0, 0, 9, 1, now=9),  # PD: below tau
        issuer.issue(0, 1, t21, 0, 0, 9, 3, now=9),
        issuer.issue(0, 1, t99, 0, 0, 9, 3, now=9),  # no record
        issuer.issue(0, 1, t20, 0, 6, 9, 3, now=9),  # alert outside the range
    ]
    requests.append(requests[0])  # replay
    requests.append(replace(requests[2], window_lo=1))  # forged after signing
    requests.append(RequestIssuer().issue(0, 1, t20, 0, 0, 9, 3, now=9))  # unknown issuer
    requests.append(issuer.issue(0, 2, t20, 0, 0, 9, 3, now=9))  # wrong responder
    for req in requests:
        assert remote.respond(req) == local.respond(req, now=9), req.request_id
    assert remote_node.guard.refusals == local.guard.refusals
    assert remote_node.disclosed == local.disclosed and remote_node.inbound == local.inbound


def test_node_clock_is_set_by_orchestration_only_and_never_goes_back() -> None:
    service = TokenService(seed=b"\x08" * 32)
    issuer = RequestIssuer()
    remote_node = _node("S1", service, issuer)
    http = TestClient(node_app(remote_node, ADMIN, clock=9))
    remote = HttpNode(http)
    token = TokenClient(0, service.evaluate).tokens(0, [identifier(20)])[0]
    req = issuer.issue(0, 1, token, 0, 0, 9, 3, now=9)  # expires after window 10
    with pytest.raises(ServiceError, match="401"):
        remote.set_clock(b"wrong", 20)
    remote.set_clock(ADMIN, 20)
    assert remote.respond(req).status == "refused"  # expired by the node's own clock
    assert remote_node.guard.refusals["expired"] == 1
    with pytest.raises(ServiceError, match="400"):
        remote.set_clock(ADMIN, 5)  # time never goes back
    assert http.post("/v1/evidence", content=b"not json").status_code == 400
    bad = encode(req)
    bad["body"]["purpose"] = "marketing"
    assert http.post("/v1/evidence", json=bad).status_code == 400  # undeclared purpose
    assert http.get("/v1/health").json() == {"service": "node", "member": 1, "level": "S1",
                                            "status": "ok"}  # fmt: skip


def test_http_client_reports_service_errors() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "down"})

    node = HttpNode(httpx.Client(transport=httpx.MockTransport(broken), base_url="http://n"))
    with pytest.raises(ServiceError, match="503"):
        node.respond(RequestIssuer().issue(0, 1, b"t" * 16, 0, 0, 9, 3, now=9))


def test_token_service_runs_as_a_separate_process() -> None:
    """The demo path: a real uvicorn process, real HTTP, same tokens as in-process."""
    import os
    import socket
    import subprocess
    import sys
    import time

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {
        **os.environ,
        "FINMESH_TOKEN_SEED": "09" * 32,
        "FINMESH_BANK_KEYS": json.dumps({str(b): k.hex() for b, k in KEYS.items()}),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "--factory", "finmesh.services.run:token_app_from_env",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )  # fmt: skip
    try:
        http = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5)
        deadline = time.monotonic() + 30
        while True:
            try:
                if http.get("/v1/health").status_code == 200:
                    break
            except httpx.TransportError:
                pass
            assert time.monotonic() < deadline, "token service did not start"
            time.sleep(0.2)
        idents = [identifier(a) for a in (1, 2, 3)]
        remote = TokenClient(1, HttpTokenTransport(http, 1, KEYS[1])).tokens(2, idents)
        local = TokenClient(1, TokenService(seed=b"\x09" * 32).evaluate).tokens(2, idents)
        assert remote == local
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    with pytest.raises(httpx.TransportError):  # a stopped service fails loudly, never silently
        TokenClient(1, HttpTokenTransport(http, 1, KEYS[1])).tokens(3, [identifier(4)])
