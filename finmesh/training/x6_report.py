"""X6 page (week 13): pattern attribution by sharing level."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import fmt, table
from finmesh.training.x6 import LEVELS, METHODS

LEVEL_LABELS = {
    "S0": "S0 · own data only",
    "S1": "S1 · + cross-bank structure",
    "S2": "S2 · + other banks' records",
    "S3": "S3 (ε = 2) · + noisy records",
    "oracle": "Oracle · all data pooled",
}
METHOD_LABELS = {
    "attributor": "Attributor (GBDT)",
    "majority": "Majority class",
    "rules": "Rule-based shape",
    "catalogue": "Catalogue matching",
}


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def render_x6(r: dict[str, Any]) -> str:
    s = r["summary"]
    lv = s["levels"]
    main = []
    for name in LEVELS:
        row: dict[str, Any] = {"level": LEVEL_LABELS[name], "detected": lv[name]["detected_share"]}
        for m in METHODS:
            row[m] = _ci(lv[name][m]["accuracy"])
        main.append(row)
    secondary = [
        {
            "level": LEVEL_LABELS[name],
            "acc": lv[name]["attributor"]["accuracy_detected"],
            "f1": lv[name]["attributor"]["macro_f1_detected"],
        }
        for name in LEVELS
    ]
    classes = s["classes"]
    recall = [
        {"pattern": c, **{name: lv[name]["attributor"]["recall_by_pattern"][c] for name in LEVELS}}
        for c in classes
    ]
    comps = [{"comparison": k, "diff": _ci(v)} for k, v in s["comparisons"].items()]
    h = s["H3a"]
    stage = s["stages"]
    return "\n".join(
        [
            f"# X6 · pattern attribution by sharing level · {r['dataset']}"
            + (f" ({r['option']})" if r["option"] != "B8" else ""),
            "",
            f"Seeds {r['seeds']}; {s['schemes']} pattern-labelled validation schemes, "
            f"{len(classes)} patterns. Each level uses its frozen G2 fusion and linking rule; a "
            "scheme is attributed through the incident holding most of its alerted accounts "
            "within 72 h, using only what the level reveals to the incident's owner "
            "(`docs/protocol/attribution_mapping.md`). Attributor: multinomial LightGBM "
            "cross-fitted on the two time halves of validation. Accuracy is end to end "
            "(undetected schemes count as wrong), averaged over seeds, with a 1,000-replicate "
            f"scheme bootstrap. {r['seconds']:,.0f} s, peak memory {r['peak_anon_mb']:,.0f} MB.",
            "",
            "## Pattern accuracy, end to end [95% CI]",
            "",
            table(
                main,
                [
                    ("level", "Level"),
                    ("detected", "Schemes detected"),
                    *[(m, METHOD_LABELS[m]) for m in METHODS],
                ],
            ),
            "",
            "## H3a on validation",
            "",
            "S2 − S0 attributor accuracy has a 95% CI above 0, and S2's attributor beats the "
            "majority and rule baselines. Judged on test.",
            "",
            table(
                [
                    {"item": "S2 − S0 (attributor)", "value": _ci(h["S2_minus_S0"])},
                    {"item": "S2 attributor − majority", "value": _ci(h["S2_above_majority"])},
                    {"item": "S2 attributor − rules", "value": _ci(h["S2_above_rules"])},
                    {
                        "item": "Met on validation",
                        "value": "yes" if h["met_on_validation"] else "no",
                    },
                ],
                [("item", "Item"), ("value", "Validation")],
            ),
            "",
            "## Attributor on detected schemes",
            "",
            table(
                secondary,
                [
                    ("level", "Level"),
                    ("acc", "Accuracy (detected schemes)"),
                    ("f1", "Macro-F1 (detected schemes)"),
                ],
            ),
            "",
            "## Attributor recall by pattern (end to end)",
            "",
            table(recall, [("pattern", "Pattern"), *[(n, n) for n in LEVELS]]),
            "",
            "## All paired comparisons",
            "",
            table(comps, [("comparison", "Comparison"), ("diff", "Accuracy difference [95% CI]")]),
            "",
            "Stage-level accuracy: "
            + (
                "reported separately."
                if stage["reported"]
                else f"not reported: the stage distribution is degenerate ({stage['counts']})."
            ),
            "",
        ]
    )


__all__ = ["render_x6"]
