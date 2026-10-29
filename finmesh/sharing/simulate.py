"""In-process run of the sharing protocol on one partition (week 6).

For every alert at member A in window w, A looks at the alerted account's
counterparties held at other members within the lookback (A sees those
transactions: they touch its own account). For each such counterparty b at
member B, A tokenises b through the token service and sends B a signed
evidence request for the windows [w - lookback + 1, w], split by epoch. B's
guard checks the request; B answers at its level from its own evidence store.
A positive alert flag links A's alert to B's alert on b (week 6 linking rule;
week 7 adds fusion and triage).

Every message travels over a :class:`~finmesh.sharing.messages.Bus` that
enforces the allowlist. The returned ``links`` name accounts on both sides
for the harness's evaluation only; no node ever receives the other side's
account.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import polars as pl

from finmesh.matching.tokens import TokenClient, TokenService, identifier
from finmesh.sharing.ldp import LdpReleaser
from finmesh.sharing.messages import BlindedAnswer, BlindedQuery, Bus
from finmesh.sharing.node import BankNode, request_epochs
from finmesh.sharing.requests import RequestGuard, RequestIssuer

LINK_SCHEMA = {
    "member_a": pl.Int32,
    "account_a": pl.UInt64,
    "window_a": pl.Int32,
    "member_b": pl.Int32,
    "account_b": pl.UInt64,
    "window_b": pl.Int32,
}


@dataclass
class TokenEnv:
    """One token service and one client per bank, shared by several protocol runs.

    Runs of different levels on the same candidates tokenise the same accounts;
    sharing the clients' caches does the OPRF work once (about half the protocol
    time). Token statistics then belong to the first run that needed them.
    """

    service: TokenService
    bus: Bus
    clients: dict[int, TokenClient]

    @classmethod
    def new(cls) -> TokenEnv:
        return cls(TokenService(), Bus(), {})

    def client(self, bank: int) -> TokenClient:
        if bank not in self.clients:

            def transport(b: int, epoch: int, points: list[bytes]) -> list[bytes]:
                self.bus.send(BlindedQuery(b, epoch, tuple(points)))
                answer = self.service.evaluate(b, epoch, points)
                self.bus.send(BlindedAnswer(tuple(answer)))
                return answer

            self.clients[bank] = TokenClient(bank, transport)
        return self.clients[bank]


@dataclass
class ShareRun:
    level: str
    links: pl.DataFrame
    stats: dict[str, Any]
    # One row per informative answer (alert, record or refusal): requester member,
    # window, its accounts (list), responder member, status, alert flag, record
    # values (list or null).
    # ``cp`` is the counterparty account, kept for the harness's evaluation only.
    responses: pl.DataFrame | None = None
    # Per responder: its own record rows a peer asked about, with requester buckets.
    inbound: pl.DataFrame | None = None
    # Per request group: requester member, window, its accounts, the number of
    # requests sent (one per epoch the lookback spans) and the counterparty asked
    # about (``cp``: harness only, for the audit's ground truth). Includes "no record".
    asked: pl.DataFrame | None = None


def counterparty_requests(alerts: pl.DataFrame, edges: pl.DataFrame, lookback: int) -> pl.DataFrame:
    """One row per (requester, window, counterparty, its member) with the alerted accounts.

    Edges are cut to those touching an alerted account before anything else, so
    the full edge table is never expanded (32 M rows at HI-Medium scale).
    """
    alerted = alerts.select(pl.col("account").unique())
    out_e = edges.join(alerted, left_on="src", right_on="account", how="semi").select(
        pl.col("src").alias("account"),
        pl.col("dst").alias("cp"),
        pl.col("window").alias("w_edge"),
        pl.col("src_member").alias("own"),
        pl.col("dst_member").alias("cp_member"),
    )
    in_e = edges.join(alerted, left_on="dst", right_on="account", how="semi").select(
        pl.col("dst").alias("account"),
        pl.col("src").alias("cp"),
        pl.col("window").alias("w_edge"),
        pl.col("dst_member").alias("own"),
        pl.col("src_member").alias("cp_member"),
    )
    sides = pl.concat([out_e, in_e]).filter(
        pl.col("cp_member").is_not_null() & (pl.col("cp_member") != pl.col("own"))
    )
    return (
        alerts.join(sides, left_on=["account", "member"], right_on=["account", "own"])
        .filter(
            (pl.col("w_edge") <= pl.col("window"))
            & (pl.col("w_edge") > pl.col("window") - lookback)
        )
        .group_by("member", "window", "cp", "cp_member")
        .agg(pl.col("account").unique().sort(), pl.col("prob_bucket").max())
        .sort("member", "window", "cp_member", "cp")
    )


def simulate(
    level: str,
    requesters: pl.DataFrame,
    records: dict[int, pl.DataFrame],
    edges: pl.DataFrame,
    first_window: int,
    lookback: int,
    *,
    epsilon: float | None = None,
    tau: int | None = None,
    n_features: int | None = None,
    ldp_seed: int = 0,
    tokens: TokenEnv | None = None,
) -> ShareRun:
    """Run one sharing level.

    ``requesters``: member, account, window, prob_bucket: the account-windows
    that ask about their counterparties (week 6: alerts; week 7: every
    account-window with an evidence record). S3 needs ``epsilon`` and
    ``n_features`` (the deviation-index domain); PD needs ``tau``.
    """
    alerts = requesters
    t0 = time.perf_counter()
    bus = Bus()
    env = tokens if tokens is not None else TokenEnv.new()
    service = env.service
    evaluated_before = sum(e.evaluated for e in service.log)
    token_messages_before = Counter(env.bus.counts)
    refused_before = sum(e.refused for e in service.log)
    if level == "S3" and (epsilon is None or n_features is None):
        raise ValueError("S3 needs epsilon and n_features")
    if level == "PD" and tau is None:
        raise ValueError("PD needs tau")

    issuer = RequestIssuer()

    def make_node(m: int, recs: pl.DataFrame) -> BankNode:
        ldp = (
            LdpReleaser(float(epsilon), int(n_features), seed=ldp_seed * 1009 + m)  # type: ignore[arg-type]
            if level == "S3"
            else None
        )
        return BankNode(
            m,
            level,
            env.client(m),
            RequestGuard(m, issuer.public_key),
            recs,
            ldp=ldp,
            tau=tau,
        )

    nodes = {m: make_node(m, recs) for m, recs in records.items()}
    empty = pl.DataFrame(schema=LINK_SCHEMA)
    if level == "S0":
        return ShareRun(level, empty, {"level": level, "requests": 0})

    plan = counterparty_requests(alerts, edges, lookback)
    # A member without records (none above the floor) still answers: "no_record".
    if records:
        blank = next(iter(records.values())).clear()
        for m in set(plan["cp_member"].to_list()) | set(plan["member"].to_list()):
            if int(m) not in nodes:
                nodes[int(m)] = make_node(int(m), blank)
    index_tokens = {m: node.build_index() for m, node in nodes.items()}

    # Requests run in time order, so rate limits and retention act as they would live.
    plan = plan.sort("window", "member", "cp_member", "cp")

    # Requesters tokenise counterparties in one batch per (member, epoch).
    needed: dict[tuple[int, int], set[int]] = defaultdict(set)
    for m, w, cp in plan.select("member", "window", "cp").iter_rows():
        for epoch, _, _ in request_epochs(int(w), first_window, lookback):
            needed[(int(m), epoch)].add(int(cp))
    request_tokens = 0
    tok: dict[tuple[int, int], dict[int, bytes]] = {}
    for (m, epoch), cps in needed.items():
        ordered = sorted(cps)
        before = nodes[m].tokens.queries
        tok[(m, epoch)] = dict(
            zip(
                ordered,
                nodes[m].tokens.tokens(epoch, [identifier(c) for c in ordered]),
                strict=True,
            )
        )
        request_tokens += nodes[m].tokens.queries - before
    del needed

    links: list[tuple[int, int, int, int, int, int]] = []
    status: Counter[str] = Counter()
    # Only informative answers are kept row by row; "no record" answers are counted
    # per request group in ``asked`` below.
    answered: list[tuple[Any, ...]] = []
    n_requests = 0
    current = None
    purged = 0
    for m, w, cp, cp_m, accts, bucket in plan.iter_rows():
        m, w, cp, cp_m = int(m), int(w), int(cp), int(cp_m)
        if w != current:
            purged += sum(node.received.purge(w) for node in nodes.values())
            current = w
        for epoch, lo, hi in request_epochs(w, first_window, lookback):
            n_requests += 1
            request = bus.send(
                issuer.issue(m, cp_m, tok[(m, epoch)][cp], epoch, lo, hi, int(bucket), now=w)
            )
            response = bus.send(nodes[cp_m].respond(request, now=w))
            nodes[m].received.add(w, response)
            status[f"{response.status}{'_alert' if response.alert else ''}"] += 1
            if response.status == "no_record" and not response.alert:
                continue
            record = list(response.record.values) if response.record is not None else None
            answered.append((m, w, accts, cp_m, cp, response.status, response.alert, record))
            if response.alert:
                links.extend((m, a, w, cp_m, cp, response.alert_window) for a in accts)
    del tok
    asked = (
        plan.with_columns(
            pl.col("window")
            .map_elements(
                lambda w: len(request_epochs(int(w), first_window, lookback)),
                return_dtype=pl.Int32,
            )
            .alias("n")
        ).select(
            "member",
            "window",
            pl.col("account").alias("accounts"),
            "n",
            "cp_member",
            "cp",
            pl.col("prob_bucket").alias("bucket"),
        )
        if plan.height
        else pl.DataFrame(
            schema={
                "member": pl.Int32,
                "window": pl.Int32,
                "accounts": pl.List(pl.UInt64),
                "n": pl.Int32,
                "cp_member": pl.Int32,
                "cp": pl.UInt64,
                "bucket": pl.Int8,
            }
        )
    )
    last = int(alerts["window"].cast(pl.Int64).max() or 0) if alerts.height else 0  # type: ignore[arg-type]
    purged += sum(node.received.purge(last) for node in nodes.values())
    refusals: Counter[str] = Counter()
    for node in nodes.values():
        refusals.update(node.guard.refusals)
    link_frame = pl.DataFrame(links, schema=LINK_SCHEMA, orient="row").unique() if links else empty
    stats = {
        "level": level,
        "alerts": alerts.height,
        "request_groups": plan.height,
        "requests": n_requests,
        "responses": dict(status),
        "refusals": dict(refusals),
        "tokens_index": sum(index_tokens.values()),
        "tokens_requests": request_tokens,
        "service_evaluations": int(sum(e.evaluated for e in service.log) - evaluated_before),
        "service_refused": int(sum(e.refused for e in service.log) - refused_before),
        "max_bank_epoch_queries": max(service.used.values(), default=0),
        "messages": dict(bus.counts + (Counter(env.bus.counts) - token_messages_before)),
        "links": link_frame.height,
        "received_purged": purged,
        "records_disclosed": sum(len(n.disclosed) for n in nodes.values()),
        "accounts_disclosed": sum(
            len({int(n._acct[r]) for r in n.disclosed}) for n in nodes.values()
        ),
        "ldp_withheld": sum(n.ldp.withheld for n in nodes.values() if n.ldp is not None),
        "ldp_max_account_epsilon": max(
            (n.ldp.max_account_epsilon for n in nodes.values() if n.ldp is not None),
            default=0.0,
        ),
        "epsilon": epsilon,
        "tau": tau,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    responses = pl.DataFrame(
        answered,
        schema={
            "member": pl.Int32,
            "window": pl.Int32,
            "accounts": pl.List(pl.UInt64),
            "cp_member": pl.Int32,
            "cp": pl.UInt64,
            "status": pl.String,
            "alert": pl.Boolean,
            "record": pl.List(pl.Int64),
        },
        orient="row",
    )
    inbound_rows = [
        (m, int(node._acct[row]), int(node._win[row]), b)
        for m, node in nodes.items()
        for row, b in node.inbound
    ]
    inbound = pl.DataFrame(
        inbound_rows,
        schema={"member": pl.Int32, "account": pl.UInt64, "window": pl.Int32, "bucket": pl.Int8},
        orient="row",
    )
    return ShareRun(level, link_frame, stats, responses, inbound, asked)
