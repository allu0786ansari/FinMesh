"""Narrative page (week 14, A21): abstention, H3b grounding, latency, and example cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finmesh.attribution.narrative import UNATTRIBUTED
from finmesh.reporting import fmt, table


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{100 * v:.1f}%"


def _example(title: str, r: dict[str, Any]) -> list[str]:
    checks = r["first"]
    flags = ", ".join(
        f"{k} {'yes' if checks[k] else 'no'}" for k in ("json", "typology", "cited", "numeric")
    )
    cands = ", ".join(f"{c['id']} {c['confidence']:.2f}" for c in r["candidates"])
    return [
        f"### {title}",
        "",
        f"- Scheme {r['scheme_id']}: true pattern **{r['pattern']}**; shown to the analyst: "
        f"**{r['assigned']}** (top candidates: {cands}).",
        f"- First reply: {flags}; final text from **{r['final_source']}**; "
        f"{r['latency_total_s']:.1f} s.",
        f"- Cited fields: {', '.join(f'`{f}`' for f in checks['cited_fields']) or 'none'}.",
        "",
        f"> {r['narrative']}",
        "",
        "Review actions (from the catalogue, not the model):",
        "",
        *[f"1. {a}" for a in r["review_actions"]],
        "",
    ]


def _pick(cases: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    att = [c for c in cases if c["assigned"] != UNATTRIBUTED and c["final_source"] == "first"]
    good = [c for c in att if c["assigned"] == c["pattern"]]
    if good or att:
        out.append(("An attributed case", (good or att)[0]))
    una = [c for c in cases if c["assigned"] == UNATTRIBUTED]
    if una:
        out.append(("An unattributed case", una[0]))
    fixed = [c for c in cases if c["final_source"] != "first"]
    if fixed:
        out.append(("A case whose first reply failed the check", fixed[0]))
    return out


def render_narrative(r: dict[str, Any]) -> str:
    s = r["summary"]
    sel = r["selective"]
    h = s["H3b"]
    g = h["grounding"]
    fr = s["first_reply"]
    lat = s["latency_s"]
    tau = sel["tau"]
    at_tau = next((row for row in sel["grid"] if row["tau"] == tau), None)
    grid = [
        {
            "tau": f"{row['tau']:.2f}" + (" ← τ" if row["tau"] == tau else ""),
            "coverage": _pct(row["coverage"]),
            "acc": _pct(row["selective_accuracy"]),
            "kept": row["kept"],
        }
        for row in sel["grid"]
    ]
    pattern_rows = [
        {
            "pattern": p,
            "cases": v["cases"],
            "attributed": v["attributed"],
            "correct": v["correct"],
            "grounded": _pct(v["grounded"]),
        }
        for p, v in s["by_pattern"].items()
    ]
    examples: list[str] = []
    for title, case in _pick(r["cases"]):
        examples += _example(title, case)
    return "\n".join(
        [
            f"# Constrained case narrative (H3b) · {r['dataset']}",
            "",
            f"Level S2, seed {r['seed']}; {s['cases']} detected validation schemes sampled by "
            f"pattern (up to 25 each). Model `{r['model']}` on this machine, temperature 0; "
            f"{r['decoding']} (A21). The model writes the text only: the typology comes from the "
            "X6 attributor (shown only above τ), the evidence from a fixed template of what S2 "
            "reveals to the owner, and the review actions from the catalogue. "
            f"{r['seconds']['total']:,.0f} s in total ({r['seconds']['x6_s2']:,.0f} s for the S2 "
            f"attributor), peak memory {r['peak_anon_mb']:,.0f} MB.",
            "",
            "## H3b on validation",
            "",
            table(
                [
                    {
                        "item": "Grounded first replies [95% Wilson CI]",
                        "value": "—"
                        if g["estimate"] is None
                        else f"{fmt(g['estimate'])} [{fmt(g['low'])}, {fmt(g['high'])}]",
                    },
                    {"item": "Target", "value": fmt(h["target"])},
                    {"item": "Met on validation", "value": fmt(h["met_on_validation"])},
                ],
                [("item", "Item"), ("value", "Validation")],
            ),
            "",
            "Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every "
            "cited field present in the evidence. Judged on test.",
            "",
            "## Reply quality and latency",
            "",
            table(
                [
                    {"item": "First reply: valid JSON", "value": _pct(fr["json"])},
                    {"item": "First reply: typology as shown", "value": _pct(fr["typology"])},
                    {"item": "First reply: cited fields all real", "value": _pct(fr["cited"])},
                    {
                        "item": "First reply: cites at least one field",
                        "value": _pct(fr["cites_any"]),
                    },
                    {
                        "item": "First reply: every number appears in the prompt",
                        "value": _pct(fr["numeric"]),
                    },
                    {"item": "Retried (schema-constrained)", "value": _pct(s["retry_rate"])},
                    {"item": "Retry grounded", "value": _pct(s["retry_grounded"])},
                    {"item": "Template fallback", "value": _pct(s["fallback_rate"])},
                    {
                        "item": "Final text: numbers all from the prompt",
                        "value": _pct(s["final_numeric"]),
                    },
                    {"item": "Cases with a call error", "value": fmt(s["errors"])},
                    {
                        "item": "Latency per case, p50 / p95 / max",
                        "value": "—"
                        if lat["p50"] is None
                        else f"{lat['p50']:.1f} / {lat['p95']:.1f} / {lat['max']:.1f} s "
                        f"(target p95 ≤ {lat['target_p95']:.0f} s)",
                    },
                ],
                [("item", "Item"), ("value", "Value")],
            ),
            "",
            "## Abstention: when the attributor's label is shown",
            "",
            f"τ = **{'none' if tau is None else f'{tau:.2f}'}**: the smallest threshold whose "
            "selective accuracy on all detected validation schemes is at least 50% with coverage "
            f"at least 10% ({sel['detected_schemes']:,} detected of {sel['schemes']:,} schemes; "
            f"attributor accuracy without abstention {_pct(sel['accuracy_detected'])}). "
            + (
                f"At τ, {_pct(at_tau['coverage'])} of cases get a label, "
                f"{_pct(at_tau['selective_accuracy'])} of them correct."
                if at_tau
                else "No threshold qualifies: every case is UNATTRIBUTED with its top three "
                "candidates."
            ),
            "",
            table(
                grid,
                [
                    ("tau", "τ"),
                    ("coverage", "Coverage"),
                    ("acc", "Selective accuracy"),
                    ("kept", "Schemes labelled"),
                ],
            ),
            "",
            "## In the sample",
            "",
            f"- Labelled cases: {s['attributed']['cases']}, correct "
            f"{_pct(s['attributed']['accuracy'])}.",
            f"- Unattributed cases: {s['unattributed']['cases']}; the true pattern is among the "
            f"three candidates listed in {_pct(s['unattributed']['top3_contains_truth'])}.",
            "",
            table(
                pattern_rows,
                [
                    ("pattern", "Pattern"),
                    ("cases", "Cases"),
                    ("attributed", "Labelled"),
                    ("correct", "Labelled correctly"),
                    ("grounded", "Grounded first replies"),
                ],
            ),
            "",
            "## Example cases",
            "",
            *(examples or ["No cases."]),
            f"Every case (prompt size, raw replies, checks, final text) is in "
            f"`narrative_{r['dataset']}_cases.jsonl`.",
            "",
        ]
    )


def write_cases(r: dict[str, Any], path: Path) -> Path:
    """One compact JSON line per case, for review and for the paper's examples."""
    keep = (
        "scheme_id",
        "pattern",
        "assigned",
        "confidence",
        "candidates",
        "final_source",
        "narrative",
        "review_actions",
        "latency_total_s",
        "prompt_chars",
        "errors",
    )
    with path.open("w") as f:
        for c in r["cases"]:
            row = {k: c[k] for k in keep}
            row["evidence"] = {e["field"]: e["value"] for e in c["evidence"]}
            row["first"] = {k: v for k, v in c["first"].items() if k != "narrative"}
            row["retry_raw"] = c["retry"]["raw"] if c["retry"] else None
            f.write(json.dumps(row) + "\n")
    return path


__all__ = ["render_narrative", "write_cases"]
