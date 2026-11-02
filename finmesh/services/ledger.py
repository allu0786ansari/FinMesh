"""The privacy ledger (week 16): what was shared, by whom, and against which budget.

It reads only durable records: the session store (every evidence request and its
response), the token service's budget ledger (every OPRF call) and the world's metadata.
Four sections, as the proposal lists them:

* **model**: no shared model is trained on the demo path. Gate G3 kept each member's
  detector local (the DP federated scorer added nothing on HI-Medium), so no model ε is
  spent; the per-client DP accounting of X4/X5 is reported on those pages;
* **evidence**: per responding member, requests received, answered with a record, alert
  flags revealed and refusals; per requesting member, requests sent. At S2 the records
  are minimised but not differentially private, so the ledger counts disclosures rather
  than ε (S3's per-account ε budget applies only when a node runs at S3);
* **tokens**: OPRF evaluations per bank and epoch against the budget, and refusals;
* **requests**: every request (session, requester, responder, epoch, status, whether a
  record was released), for audit.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from finmesh.services.store import BudgetLedger, SessionStore


def privacy_ledger(
    store: SessionStore, budget: BudgetLedger | None, meta: dict[str, Any]
) -> dict[str, Any]:
    level = meta.get("level", "S2")
    received: dict[int, dict[str, int]] = defaultdict(
        lambda: {
            "requests": 0,
            "records_released": 0,
            "alert_flags": 0,
            "refused": 0,
            "no_record": 0,
            "unavailable": 0,
        }
    )
    sent: dict[int, int] = defaultdict(int)
    audit = []
    for r in store.all_requests():
        body = (r["response"] or {}).get("body", {})
        record = bool(body.get("record"))
        flag = bool(body.get("alert"))
        x = received[r["responder"]]
        x["requests"] += 1
        x["records_released"] += int(record)
        x["alert_flags"] += int(flag)
        x["refused"] += int(r["status"] == "refused")
        x["no_record"] += int(r["status"] == "no_record")
        x["unavailable"] += int(r["status"] == "unavailable")
        sent[r["requester"]] += 1
        audit.append(
            {
                "session": r["session"],
                "requester": r["requester"],
                "responder": r["responder"],
                "epoch": r["epoch"],
                "status": r["status"],
                "record_released": record,
                "alert_flag": flag,
            }
        )
    tokens: list[dict[str, Any]] = []
    if budget is not None:
        per: dict[tuple[int, int], dict[str, int]] = defaultdict(
            lambda: {"evaluated": 0, "refused": 0, "calls": 0}
        )
        for c in budget.calls():
            p = per[(c["bank"], c["epoch"])]
            p["evaluated"] += c["evaluated"]
            p["refused"] += c["refused"]
            p["calls"] += 1
        cap = int(meta.get("token_budget", 0))
        for (bank, epoch), p in sorted(per.items()):
            tokens.append(
                {
                    "bank": bank,
                    "epoch": epoch,
                    **p,
                    "budget": cap,
                    "share_used": (p["evaluated"] / cap) if cap else None,
                }
            )
    members = sorted(set(meta.get("members", [])) | set(received) | set(sent))
    return {
        "level": level,
        "model": {
            "shared_model": False,
            "epsilon": None,
            "note": "No shared model on the demo path: Gate G3 kept each member's detector "
            "local, so no model privacy budget is spent.",
        },
        "evidence": {
            "differentially_private": level == "S3",
            "note": "S2 records are minimised (bucketed counters, no identifiers) but not "
            "differentially private; disclosures are counted."
            if level != "S3"
            else "S3 records are released through local DP; see each node's ε budget.",
            "by_member": [
                {
                    "member": m,
                    "requests_sent": sent.get(m, 0),
                    **received.get(
                        m,
                        {
                            "requests": 0,
                            "records_released": 0,
                            "alert_flags": 0,
                            "refused": 0,
                            "no_record": 0,
                            "unavailable": 0,
                        },
                    ),
                }
                for m in members
            ],
        },
        "tokens": tokens,
        "requests": audit,
    }


__all__ = ["privacy_ledger"]
