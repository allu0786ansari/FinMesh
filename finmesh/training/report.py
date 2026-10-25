"""Markdown page for the week-5 baselines (docs/eval/baselines_<ds>.md)."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import fmt, table

ORDER = ("oracle", "S0-BG", "S0-B", "iforest", "pca", "activity", "random")
LABELS = {
    "oracle": "Oracle (pooled data, full graph)",
    "S0-BG": "S0 local GBDT, all features",
    "S0-B": "S0 local GBDT, behaviour only",
    "iforest": "Isolation Forest (local)",
    "pca": "PCA reconstruction (local)",
    "activity": "Activity (legs in window)",
    "random": "Random",
}


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def _budget(res: dict[str, Any], name: str) -> dict[str, Any]:
    return next(b for b in res["budgets"] if b["budget"] == name)


def render_baselines(r: dict[str, Any]) -> str:
    primary = r["primary_budget"]
    w = r["windows"]
    lines = [
        f"# Baselines · {r['dataset']} (seed {r['seed']})",
        "",
        f"Federation {r['option']}; validation windows {r['validation_windows'][0]}–"
        f"{r['validation_windows'][1]}. Training windows {w['burn_in']}–{w['train_last']} "
        f"(burn-in before {w['burn_in']}); windows {w['stop_from']}–{w['train_last']} held out "
        "for early stopping and FPR thresholds. Label: primary (amendment A9: incidental "
        f"positives masked). Primary operating point **{primary}** (A10); schemes count as "
        f"detected within {r['delay_windows']} windows of their first. S0 links alerts "
        "locally; the oracle links across members. Total "
        f"{r.get('seconds', 0):,.0f} s, peak memory {r.get('peak_anon_mb', 0):,.0f} MB.",
        "",
        f"## Validation at the primary budget ({primary})",
        "",
    ]
    rows = []
    for name in ORDER:
        if name not in r["results"]:
            continue
        res = r["results"][name]
        b = _budget(res, primary)
        rl = b.get("random_alert_linked")
        rows.append(
            {
                "scorer": LABELS[name],
                "auprc": _ci(res["window"].get("auprc")),
                "auroc": fmt(res["window"]["auroc"]["estimate"])
                if res["window"].get("auroc")
                else "—",
                "precision": b["precision"],
                "recall": b["window_recall"],
                "detected": _ci(b["detected"]),
                "rand_det": fmt(b["random_alert_detected"]["estimate"]),
                "linked": _ci(b["linked"]),
                "rand_link": fmt(rl["estimate"]) if rl else "—",
                "cross": fmt(b["linked_cross_member"]["estimate"])
                if b["linked_cross_member"]
                else "—",
                "ttd": b["median_time_to_detect_h"],
            }
        )
    lines.append(
        table(
            rows,
            [
                ("scorer", "Scorer"),
                ("auprc", "AUPRC [95% CI]"),
                ("auroc", "AUROC"),
                ("precision", "Precision"),
                ("recall", "Window recall"),
                ("detected", "Detected [95% CI]"),
                ("rand_det", "Random detected"),
                ("linked", "Linked [95% CI]"),
                ("rand_link", "Random linked"),
                ("cross", "Linked across members"),
                ("ttd", "Median TTD h"),
            ],
        )
    )
    prevalence = r["results"]["random"]["window"]["prevalence"]
    lines += [
        "",
        f"Validation prevalence {fmt(prevalence)}; schemes evaluated "
        f"{_budget(r['results']['random'], primary)['schemes']}.",
        "",
        "## Gate G1 and PT4b comparisons (paired, same schemes and accounts)",
        "",
    ]
    comp_rows = []
    for pair, c in r["comparisons"].items():
        comp_rows.append(
            {
                "pair": pair,
                "linked": _ci(c["linked"]["difference"]),
                "p_linked": c["linked"]["p_holm"],
                "detected": _ci(c["detected"]["difference"]),
                "p_detected": c["detected"]["p_holm"],
                "auprc": _ci(c["window"]["auprc_difference"]),
                "p_auprc": c["window"]["p"],
            }
        )
    lines.append(
        table(
            comp_rows,
            [
                ("pair", "Difference"),
                ("linked", "Linked detection"),
                ("p_linked", "p (Holm)"),
                ("detected", "Any-alert detection"),
                ("p_detected", "p (Holm)"),
                ("auprc", "AUPRC"),
                ("p_auprc", "p"),
            ],
        )
    )
    lines += [
        "",
        "## Secondary operating points (FPR budgets, thresholds from the held-out training "
        "windows)",
        "",
    ]
    sec = []
    for name in ORDER:
        if name not in r["results"]:
            continue
        for b in r["results"][name]["budgets"]:
            if b["budget"] == primary:
                continue
            sec.append(
                {
                    "scorer": name,
                    "budget": b["budget"],
                    "alerts": b["alerts"],
                    "false": b["false_alerts_per_1000_accounts_per_day"],
                    "maxfpr": b["max_member_fpr"],
                    "precision": b["precision"],
                    "detected": _ci(b["detected"]),
                    "linked": _ci(b["linked"]),
                }
            )
    lines.append(
        table(
            sec,
            [
                ("scorer", "Scorer"),
                ("budget", "Budget"),
                ("alerts", "Alerts"),
                ("false", "False alerts /1000 acc /day"),
                ("maxfpr", "Max member FPR"),
                ("precision", "Precision"),
                ("detected", "Detected"),
                ("linked", "Linked"),
            ],
        )
    )
    lines += ["", "## Sensitivity: original label (incidental positives counted)", ""]
    sens = []
    for name, res in r["sensitivity_touch_label"].items():
        b = _budget(res, primary)
        sens.append(
            {
                "scorer": name,
                "auprc": _ci(res["window"].get("auprc")),
                "precision": b["precision"],
                "detected": _ci(b["detected"]),
                "linked": _ci(b["linked"]),
            }
        )
    lines.append(
        table(
            sens,
            [
                ("scorer", "Scorer"),
                ("auprc", "AUPRC"),
                ("precision", "Precision"),
                ("detected", "Detected"),
                ("linked", "Linked"),
            ],
        )
    )
    lines += ["", "## Calibration (isotonic per member, two-fold cross-fitted on validation)", ""]
    lines.append(
        table(
            [
                {"scorer": k, **{m: v[m] for m in v if m != "calibrators"}}
                for k, v in r["calibration"].items()
            ],
            [
                ("scorer", "Scorer"),
                ("brier_raw", "Brier (raw)"),
                ("brier_calibrated_crossfit", "Brier (calibrated)"),
                ("ece_raw", "ECE (raw)"),
                ("ece_calibrated_crossfit", "ECE (calibrated)"),
                ("prevalence", "Prevalence"),
            ],
        )
    )
    lines += ["", "## Most important features (share of total gain)", ""]
    for name in ("S0-BG", "oracle"):
        imp = sorted(r["importance"].get(name, {}).items(), key=lambda kv: -kv[1])[:10]
        lines.append(f"- **{name}:** " + ", ".join(f"`{k}` {v:.2f}" for k, v in imp))
    lines += ["", "## Time per configuration", ""]
    lines.append(
        table(
            [
                {"name": k, "train": v["seconds"], "evaluate": v.get("evaluate_seconds")}
                for k, v in r["configurations"].items()
            ],
            [("name", "Configuration"), ("train", "Train and score s"), ("evaluate", "Evaluate s")],
        )
    )
    return "\n".join(lines) + "\n"
