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
class ShareRun:
    level: str
    links: pl.DataFrame
    stats: dict[str, Any]


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
    alerts: pl.DataFrame,
    records: dict[int, pl.DataFrame],
    edges: pl.DataFrame,
    first_window: int,
    lookback: int,
) -> ShareRun:
    """Run one sharing level. ``alerts``: member, account, window, prob_bucket."""
    t0 = time.perf_counter()
    bus = Bus()
    service = TokenService()

    def transport(bank: int, epoch: int, points: list[bytes]) -> list[bytes]:
        bus.send(BlindedQuery(bank, epoch, tuple(points)))
        answer = service.evaluate(bank, epoch, points)
        bus.send(BlindedAnswer(tuple(answer)))
        return answer

    issuer = RequestIssuer()
    nodes = {
        m: BankNode(m, level, TokenClient(m, transport), RequestGuard(m, issuer.public_key), recs)
        for m, recs in records.items()
    }
    empty = pl.DataFrame(schema=LINK_SCHEMA)
    if level == "S0":
        return ShareRun(level, empty, {"level": level, "requests": 0})

    index_tokens = {m: node.build_index() for m, node in nodes.items()}
    plan = counterparty_requests(alerts, edges, lookback)

    # Requesters tokenise counterparties in one batch per (member, epoch).
    needed: dict[tuple[int, int], set[int]] = defaultdict(set)
    jobs = []
    for m, w, cp, cp_m, accts, bucket in plan.iter_rows():
        for epoch, lo, hi in request_epochs(int(w), first_window, lookback):
            needed[(int(m), epoch)].add(int(cp))
            jobs.append((int(m), int(w), int(cp), int(cp_m), accts, int(bucket), epoch, lo, hi))
    request_tokens = 0
    tok: dict[tuple[int, int, int], bytes] = {}
    for (m, epoch), cps in needed.items():
        ordered = sorted(cps)
        before = nodes[m].tokens.queries
        for cp, t in zip(
            ordered, nodes[m].tokens.tokens(epoch, [identifier(c) for c in ordered]), strict=True
        ):
            tok[(m, epoch, cp)] = t
        request_tokens += nodes[m].tokens.queries - before

    links: list[tuple[int, int, int, int, int, int]] = []
    status: Counter[str] = Counter()
    for m, w, cp, cp_m, accts, bucket, epoch, lo, hi in jobs:
        request = bus.send(issuer.issue(m, cp_m, tok[(m, epoch, cp)], epoch, lo, hi, bucket, now=w))
        response = bus.send(nodes[cp_m].respond(request, now=w))
        nodes[m].received.add(w, response)
        status[f"{response.status}{'_alert' if response.alert else ''}"] += 1
        if response.alert:
            links.extend((m, a, w, cp_m, cp, response.alert_window) for a in accts)
    last = int(alerts["window"].cast(pl.Int64).max() or 0) if alerts.height else 0  # type: ignore[arg-type]
    purged = sum(node.received.purge(last) for node in nodes.values())
    refusals: Counter[str] = Counter()
    for node in nodes.values():
        refusals.update(node.guard.refusals)
    link_frame = pl.DataFrame(links, schema=LINK_SCHEMA, orient="row").unique() if links else empty
    stats = {
        "level": level,
        "alerts": alerts.height,
        "request_groups": plan.height,
        "requests": len(jobs),
        "responses": dict(status),
        "refusals": dict(refusals),
        "tokens_index": sum(index_tokens.values()),
        "tokens_requests": request_tokens,
        "service_evaluations": int(sum(e.evaluated for e in service.log)),
        "service_refused": int(sum(e.refused for e in service.log)),
        "max_bank_epoch_queries": max(service.used.values(), default=0),
        "messages": dict(bus.counts),
        "links": link_frame.height,
        "received_purged": purged,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    return ShareRun(level, link_frame, stats)
