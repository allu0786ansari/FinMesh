"""Markdown rendering of a harness-check result."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import fmt, table


def _ci(d: dict[str, Any] | None) -> str:
    if not d:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def render_harness_check(result: dict[str, Any]) -> str:
    lines = [
        f"# Harness check · {result['dataset']}",
        "",
        f"Federation {result['option']}, {result['window_hours']} h windows. Thresholds fitted on "
        f"{result['fit_on']}, metrics on {result['evaluated_on']}. Both scorers are label-free "
        "references, not detectors: the **random** scorer must sit on its analytic baseline "
        "(AUPRC near the prevalence, AUROC near 0.5, detection inside the random-alert "
        "interval); **activity** (transaction count) shows the harness registers a weak signal.",
        "",
    ]
    for name, rep in result["scorers"].items():
        w = rep["window"]
        lines += [
            f"## Scorer: {name}",
            "",
            f"{fmt(w['account_windows'])} account-windows, {fmt(w['positives'])} positive "
            f"(prevalence {fmt(w['prevalence'])}); "
            f"unscored {fmt(rep['unscored_account_windows'])}.",
            "",
            f"AUPRC {_ci(w.get('auprc'))}; AUROC {_ci(w.get('auroc'))}; "
            f"precision at 100 {fmt(w.get('precision_at_100'))}, at 1,000 "
            f"{fmt(w.get('precision_at_1000'))}.",
            "",
            table(
                [
                    {
                        **b,
                        "det": _ci(b["detected"]),
                        "rand": _ci(b["random_alert_detected"]),
                        "linked_ci": _ci(b["linked"]),
                    }
                    for b in rep["budgets"]
                ],
                [
                    ("budget", "Budget"),
                    ("alerts", "Alerts"),
                    ("alerts_per_1000_accounts_per_day", "Alerts /1000 acc /day"),
                    ("false_alerts_per_1000_accounts_per_day", "False /1000 acc /day"),
                    ("precision", "Precision"),
                    ("window_recall", "Window recall"),
                    ("max_member_fpr", "Max member FPR"),
                    ("schemes", "Schemes"),
                    ("det", "Detected [95% CI]"),
                    ("rand", "Random-alert [95%]"),
                    ("linked_ci", "Linked"),
                    ("median_time_to_detect_h", "Median TTD h"),
                ],
            ),
            "",
        ]
    lines += [
        "Linked detection is 0 by construction until fusion exists (week 7): without incidents "
        "every alert is its own incident.",
        "",
    ]
    return "\n".join(lines)
