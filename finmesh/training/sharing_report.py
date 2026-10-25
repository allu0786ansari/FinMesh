"""Markdown page for the week-6 protocol run (docs/eval/sharing_<ds>.md)."""

from __future__ import annotations

from typing import Any

from finmesh.matching.tokens import QUERY_BUDGET
from finmesh.reporting import fmt, table


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def render_sharing(r: dict[str, Any]) -> str:
    primary = r["primary_budget"]
    proto_rows = []
    for level, p in r["protocol"].items():
        responses = p.get("responses", {})
        proto_rows.append(
            {
                "level": level,
                "requests": p.get("requests", 0),
                "alert": sum(v for k, v in responses.items() if k.endswith("_alert")),
                "no_record": responses.get("no_record", 0),
                "ok_no_alert": responses.get("ok", 0),
                "refused": responses.get("refused", 0),
                "reasons": ", ".join(f"{k} {v}" for k, v in p.get("refusals", {}).items()) or "—",
                "tokens": p.get("service_evaluations", 0),
                "max_bank": p.get("max_bank_epoch_queries", 0),
                "messages": sum(p.get("messages", {}).values()),
                "links": p.get("links", 0),
                "cross": p.get("cross_member_incidents", 0),
                "seconds": p.get("total_seconds"),
            }
        )
    det_rows = []
    for name, res in r["results"].items():
        b = next(x for x in res["budgets"] if x["budget"] == primary)
        comp = r["comparisons"].get(f"{name} - S0")
        det_rows.append(
            {
                "level": name,
                "linked": _ci(b["linked"]),
                "cross": fmt(b["linked_cross_member"]["estimate"])
                if b["linked_cross_member"]
                else "—",
                "detected": _ci(b["detected"]),
                "gain": _ci(comp["linked"]) if comp else "—",
                "p": comp["p"] if comp else None,
            }
        )
    return "\n".join(
        [
            f"# Sharing protocol run · {r['dataset']} (seed {r['seed']})",
            "",
            f"Validation windows {r['validation_windows'][0]}–{r['validation_windows'][1]}; "
            f"federation {r['option']}; every member runs S0 (local LightGBM, every feature), "
            "calibrated on the held-out end of training, and alerts at the primary budget "
            f"({r['alerts']:,} alerts). Requests cover the {r['lookback_windows']} windows before "
            "each alert; links use alert flags only (week 6 rule), so S1 and S2 link the same "
            f"alerts by design. Total {r.get('seconds', 0):,.0f} s, peak memory "
            f"{r.get('peak_anon_mb', 0):,.0f} MB.",
            "",
            "## Protocol",
            "",
            table(
                proto_rows,
                [
                    ("level", "Level"),
                    ("requests", "Requests"),
                    ("alert", "Answered: alert"),
                    ("ok_no_alert", "Answered: record, no alert"),
                    ("no_record", "No record"),
                    ("refused", "Refused"),
                    ("reasons", "Refusal reasons"),
                    ("tokens", "Token evaluations"),
                    ("max_bank", f"Max per bank-epoch (budget {QUERY_BUDGET:,})"),
                    ("messages", "Messages (all allowlisted)"),
                    ("links", "Cross-bank links"),
                    ("cross", "Cross-member incidents"),
                    ("seconds", "Seconds"),
                ],
            ),
            "",
            f"## Linked detection at the primary budget ({primary})",
            "",
            table(
                det_rows,
                [
                    ("level", "Level"),
                    ("linked", "Linked [95% CI]"),
                    ("cross", "Linked across members"),
                    ("detected", "Detected [95% CI]"),
                    ("gain", "Linked gain over S0 [95% CI]"),
                    ("p", "p"),
                ],
            ),
            "",
            "`S0+pooled-link` links S0's alerts with the pooled rule: the most any protocol can "
            "link without changing which account-windows are alerted.",
            "",
            "Peak memory by phase (MB): "
            + ", ".join(f"{k} {fmt(v)}" for k, v in r.get("peak_mb_by_phase", {}).items())
            + ".",
            "",
            "## Evidence stores",
            "",
            table(
                [
                    {"member": m, "records": n, **r["autoencoders"].get(m, {})}
                    for m, n in sorted(r["records"].items(), key=lambda kv: int(kv[0]))
                ],
                [
                    ("member", "Member"),
                    ("records", "Records"),
                    ("iterations", "Autoencoder iterations"),
                    ("train_mse", "Reconstruction MSE"),
                ],
            ),
            "",
        ]
    )
