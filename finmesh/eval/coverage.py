"""Coverage curve (A21, week 14): how the sharing gain grows with the federation's reach.

Secondary and descriptive; it decides no hypothesis. Each point is an X1 run (S0–S4,
propagation, oracle, relational oracle; seeds 0–2; no sweeps or audit) on a federation
``B8c{p}``: banks added largest first until they hold p% of accounts, grouped into eight
members. B8 (every bank) and A64 (the 64 largest banks as members) are the end points.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finmesh.reporting import fmt, table

COVERAGE_POINTS = (10, 25, 50, 75, 90)
LEVELS = (
    ("S0", "S0"),
    ("S1/stacker", "S1"),
    ("S2/stacker", "S2"),
    ("S4/stacker", "S4"),
    ("propagation", "Propagation"),
    ("oracle-relational", "Relational oracle"),
)


def coverage_options() -> list[str]:
    """Every federation on the curve, from least to most coverage (A64 is placed by its share)."""
    return ["A64", *[f"B8c{p}" for p in COVERAGE_POINTS], "B8"]


def _tag(dataset: str, option: str) -> str:
    return dataset if option == "B8" else f"{dataset}_{option}"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    d: dict[str, Any] = json.loads(path.read_text())
    out: dict[str, Any] = d.get("result", d)
    return out


def collect(dataset: str, artifacts: Path, parquet: Path) -> list[dict[str, Any]]:
    """One row per federation with an X1 artifact; missing points are skipped, not invented.

    ``artifacts`` holds ``x1_<tag>.json``; ``parquet`` is the dataset's parquet folder, whose
    ``eval_w6_<option>/meta.json`` gives the validation accounts and schemes per federation.
    """
    full = _load(parquet / "eval_w6_B8" / "meta.json")
    full_accounts = (full or {}).get("counts", {}).get("val", {}).get("accounts")
    rows = []
    for option in coverage_options():
        x1 = _load(artifacts / f"x1_{_tag(dataset, option)}.json")
        counts = _load(parquet / f"eval_w6_{option}" / "meta.json")
        if x1 is None or counts is None:
            continue
        val = counts["counts"]["val"]
        s = x1["summary"]
        row: dict[str, Any] = {
            "option": option,
            "target": 100
            if option == "B8"
            else (int(option.split("c")[1]) if "c" in option else None),
            "account_share": (val["accounts"] / full_accounts) if full_accounts else None,
            "schemes": val["schemes"],
            "multi_member": val["multi_member_schemes"],
        }
        for key, short in LEVELS:
            row[short] = (s.get(key) or {}).get("linked")
        row["S2-S0"] = ((s.get("S2/stacker") or {}).get("linked_gain") or {}).get("difference")
        row["S2 share"] = ((s.get("H1b") or {}).get("oracle-relational") or {}).get("S2/stacker")
        rows.append(row)
    return sorted(rows, key=lambda r: (r["account_share"] is None, r["account_share"] or 0.0))


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def coverage_figure(rows: list[dict[str, Any]], dataset: str, path: Path) -> Path | None:
    pts = [r for r in rows if r["account_share"] is not None]
    if len(pts) < 2:
        return None
    from finmesh.training.x1_report import _plt

    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=150)
    xs = [100 * r["account_share"] for r in pts]
    styles = {
        "S0": ("#718096", "o", "-"),
        "S1": ("#4299e1", "s", "-"),
        "S2": ("#2b6cb0", "D", "-"),
        "Relational oracle": ("#c05621", "^", "--"),
    }
    for name, (colour, marker, ls) in styles.items():
        est = [(r[name] or {}).get("estimate") for r in pts]
        if any(e is None for e in est):
            continue
        lo = [e - r[name]["low"] for e, r in zip(est, pts, strict=True)]
        hi = [r[name]["high"] - e for e, r in zip(est, pts, strict=True)]
        ax.errorbar(xs, est, yerr=[lo, hi], color=colour, marker=marker, ls=ls, lw=1.4,
                    capsize=3, ms=5, label=name)  # fmt: skip
    for x, r in zip(xs, pts, strict=True):
        ax.annotate(r["option"], (x, 0), xytext=(0, 4), textcoords="offset points",
                    fontsize=6, ha="center", color="#4a5568")  # fmt: skip
    ax.set_xlabel("Validation accounts held by federation members (%)")
    ax.set_ylabel("Linked scheme detection")
    ax.set_xlim(0, 103)
    ax.set_ylim(0, 1)
    ax.set_title(f"Coverage curve · {dataset} · validation (A21, secondary)", fontsize=9)
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def render_coverage(rows: list[dict[str, Any]], dataset: str, figure: str | None) -> str:
    missing = [o for o in coverage_options() if o not in {r["option"] for r in rows}]
    main = [
        {
            "option": r["option"],
            "target": f"{r['target']}%" if r["target"] is not None else "64 banks",
            "share": None if r["account_share"] is None else f"{100 * r['account_share']:.1f}%",
            "schemes": f"{r['multi_member']:,} of {r['schemes']:,}",
            **{short: _ci(r[short]) for _, short in LEVELS},
        }
        for r in rows
    ]
    gains = [
        {"option": r["option"], "diff": _ci(r["S2-S0"]), "share": _ci(r["S2 share"])} for r in rows
    ]
    return "\n".join(
        [
            f"# Coverage curve · {dataset} · validation",
            "",
            "**Secondary analysis (A21); decides no hypothesis.** Each row is X1 on one federation "
            "(S0–S4, propagation, pooled oracles; seeds 0–2; no sweeps or audit). `B8c{p}`: banks "
            "added largest first, as real partnerships recruit, until they hold p% of accounts, "
            "then grouped into 8 members; accounts at other banks are outside the federation. "
            "B8 (every bank) and A64 (64 largest banks, one member each) are the end points. The "
            "scheme denominator is the same in every row (all validation schemes), so detection "
            "is end to end.",
            "",
            *([f"![Coverage curve]({figure})", ""] if figure else []),
            "## Linked detection by coverage [95% CI]",
            "",
            table(
                main,
                [
                    ("option", "Federation"),
                    ("target", "Target"),
                    ("share", "Validation accounts covered"),
                    ("schemes", "Multi-member schemes"),
                    *[(short, short) for _, short in LEVELS],
                ],
            ),
            "",
            "## The sharing gain by coverage",
            "",
            table(
                gains,
                [
                    ("option", "Federation"),
                    ("diff", "S2 − S0 linked [95% CI]"),
                    ("share", "S2 share of the relational-oracle gain [95% CI]"),
                ],
            ),
            "",
            (
                f"Not yet run: {', '.join(missing)}."
                if missing
                else "Every point on the pre-registered curve is present."
            ),
            "",
        ]
    )


__all__ = ["COVERAGE_POINTS", "collect", "coverage_figure", "coverage_options", "render_coverage"]
