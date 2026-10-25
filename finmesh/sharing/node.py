"""A bank node: its evidence store, token index and response policy.

The node answers an :class:`EvidenceRequest` at its sharing level:

* **S0**: sharing off; the node never answers (and never asks).
* **S1**: alert flag and time bucket only: whether the token's account had an
  alert in the requested windows, and the latest such window.
* **S2**: the full minimised record of the latest account-window in range
  (alerted or above the evidence floor), plus the alert flag.

The token index maps (epoch, token) to the node's own records; it is built by
tokenising the node's own accounts through the token service. The account
never appears in a message.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import polars as pl

from finmesh.matching.tokens import EPOCH_WINDOWS, TokenClient, epoch_of, identifier
from finmesh.sharing.evidence import WIRE_FIELDS
from finmesh.sharing.messages import EvidenceRecordWire, EvidenceRequest, EvidenceResponse
from finmesh.sharing.requests import ReceivedStore, RequestGuard


@dataclass
class BankNode:
    member: int
    level: str
    tokens: TokenClient
    guard: RequestGuard
    records: pl.DataFrame
    received: ReceivedStore = field(default_factory=ReceivedStore)
    index: dict[tuple[int, bytes], list[int]] = field(default_factory=dict)
    _win: Any = None
    _alert_arr: Any = None
    _acct: Any = None
    _wire: Any = None

    def build_index(self) -> int:
        """Tokenise the node's record accounts per epoch; returns tokens queried."""
        before = self.tokens.queries
        recs = self.records.with_row_index("row").with_columns(
            (pl.col("window") // EPOCH_WINDOWS).alias("epoch")
        )
        self._win = self.records["window"].to_numpy()
        self._alert_arr = self.records["alert"].to_numpy()
        self._acct = self.records["account"].to_numpy()
        self._wire = self.records.select(WIRE_FIELDS).cast(pl.Int64).to_numpy()
        index: dict[tuple[int, bytes], list[int]] = defaultdict(list)
        for (epoch,), part in recs.sort("window").group_by(["epoch"], maintain_order=True):
            accounts = part["account"].to_list()
            toks = self.tokens.tokens(int(epoch), [identifier(a) for a in accounts])
            for row, tok in zip(part["row"].to_list(), toks, strict=True):
                index[(int(epoch), tok)].append(int(row))
        self.index = dict(index)
        return self.tokens.queries - before

    def respond(self, request: EvidenceRequest, now: int) -> EvidenceResponse:
        reason = self.guard.refuse_reason(request, now)
        if reason is not None:
            return EvidenceResponse(request.request_id, self.member, self.level, "refused")
        rows = [
            r
            for r in self.index.get((request.epoch, request.token), [])
            if request.window_lo <= self._window(r) <= request.window_hi
        ]
        alerted = [r for r in rows if self._alert(r)]
        alert_window = max((self._window(r) for r in alerted), default=-1)
        if self.level == "S1":
            status = "ok" if alerted else "no_record"
            return EvidenceResponse(
                request.request_id, self.member, "S1", status, bool(alerted), alert_window
            )
        if not rows:
            return EvidenceResponse(request.request_id, self.member, "S2", "no_record")
        latest = max(rows, key=self._window)
        values = tuple(int(v) for v in self._wire[latest])
        return EvidenceResponse(
            request.request_id,
            self.member,
            "S2",
            "ok",
            bool(alerted),
            alert_window,
            EvidenceRecordWire(request.token, values),
        )

    def _window(self, row: int) -> int:
        return int(self._win[row])

    def _alert(self, row: int) -> bool:
        return bool(self._alert_arr[row])

    def subject(self, request: EvidenceRequest, window: int) -> int | None:
        """The node's own account behind a token, for the harness's evaluation only."""
        for r in self.index.get((request.epoch, request.token), []):
            if self._window(r) == window:
                return int(self._acct[r])
        return None


def request_epochs(window: int, first_allowed: int, lookback: int) -> list[tuple[int, int, int]]:
    """(epoch, window_lo, window_hi) ranges covering [window - lookback + 1, window]."""
    lo = max(first_allowed, window - lookback + 1)
    out = []
    for e in sorted({epoch_of(lo), epoch_of(window)}):
        e_lo, e_hi = e * EPOCH_WINDOWS, (e + 1) * EPOCH_WINDOWS - 1
        out.append((e, max(lo, e_lo), min(window, e_hi)))
    return out
