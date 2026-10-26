"""X1 page and the first frontier figure (docs/eval/x1_<ds>.md, frontier_<ds>.png)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from finmesh.reporting import fmt, table

ORDER = (
    "S0",
    "S1/stacker",
    "S2/stacker",
    "S4/stacker",
    "propagation",
    "oracle",
)
SECONDARY = (
    "S1/noisy_or",
    "S1/kofn",
    "S2/noisy_or",
    "S2/kofn",
    "S4/noisy_or",
    "S4/kofn",
)
LABELS = {
    "S0": "S0 (no sharing)",
    "S1/stacker": "S1 tokens + alert flags",
    "S2/stacker": "S2 minimised records",
    "S4/stacker": "S4 records + embeddings",
    "propagation": "Score propagation (plaintext)",
    "oracle": "Oracle (pooled)",
}


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def frontier_figure(r: dict[str, Any], path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = r["summary"]
    names = [n for n in ORDER if n in s]
    est = [s[n]["linked"]["estimate"] for n in names]
    lo = [s[n]["linked"]["estimate"] - s[n]["linked"]["low"] for n in names]
    hi = [s[n]["linked"]["high"] - s[n]["linked"]["estimate"] for n in names]
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
    xs = list(range(len(names)))
    colours = ["#7a7a7a"] + ["#2b6cb0"] * 3 + ["#b7791f", "#2f855a"]
    ax.bar(xs, est, color=colours[: len(names)], width=0.62)
    ax.errorbar(xs, est, yerr=[lo, hi], fmt="none", ecolor="#1a202c", capsize=4, lw=1)
    rnd = (r.get("random") or {}).get("linked") or {}
    if rnd.get("estimate") is not None:
        ax.axhline(rnd["estimate"], color="#c53030", ls="--", lw=1, label="random alerts")
        ax.legend(frameon=False, loc="upper left")
    ax.set_xticks(
        xs, [LABELS[n].replace(" (", "\n(").replace(" + ", "\n+ ") for n in names], fontsize=8
    )
    ax.set_ylabel("Linked scheme detection")
    ax.set_ylim(0, 1)
    ax.set_title(
        f"{r['dataset']} validation · {r['primary_budget']} · seeds {r['seeds']}", fontsize=9
    )
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def render_x1(r: dict[str, Any], figure: str | None) -> str:
    s = r["summary"]
    main = []
    for name in ORDER:
        if name not in s:
            continue
        v = s[name]
        main.append(
            {
                "config": LABELS[name],
                "linked": _ci(v["linked"]),
                "cross": fmt(v["linked_cross_member"]["estimate"]),
                "detected": _ci(v["detected"]),
                "gain": _ci(v.get("linked_gain", {}).get("difference")),
                "p": v.get("linked_gain", {}).get("p"),
                "auprc": v["auprc_mean"],
            }
        )
    sec = [
        {
            "config": n,
            "linked": _ci(s[n]["linked"]),
            "detected": _ci(s[n]["detected"]),
            "gain": _ci(s[n]["linked_gain"]["difference"]),
            "auprc": s[n]["auprc_mean"],
        }
        for n in SECONDARY
        if n in s
    ]
    h1b = [{"level": k, "recovery": _ci(v)} for k, v in s["H1b"].items()]
    rnd = r.get("random") or {}
    proto = []
    for seed in r["per_seed"]:
        for level, p in seed["protocol"].items():
            resp = p.get("responses", {})
            proto.append(
                {
                    "seed": seed["seed"],
                    "level": level,
                    "requests": p.get("requests"),
                    "alert": sum(v for k, v in resp.items() if k.endswith("_alert")),
                    "record": resp.get("ok", 0),
                    "refused": resp.get("refused", 0),
                    "tokens": p.get("service_evaluations"),
                    "messages": p.get("messages"),
                    "seconds": p.get("seconds_total"),
                }
            )
    lines = [
        f"# X1 · sharing ladder on validation · {r['dataset']}",
        "",
        f"Seeds {r['seeds']}; primary budget {r['primary_budget']}; schemes detected within "
        f"{r['delay_windows']} windows; primary fusion **{r['primary_fusion']}** (amendment "
        "A13). Per-scheme outcomes are averaged over seeds before the scheme bootstrap. Total "
        f"{r['seconds']:,.0f} s, peak memory {r['peak_anon_mb']:,.0f} MB.",
        "",
    ]
    if figure:
        lines += [f"![Linked detection per sharing level]({figure})", ""]
    lines += [
        "## Linked detection per level (primary fusion)",
        "",
        table(
            main,
            [
                ("config", "Configuration"),
                ("linked", "Linked [95% CI]"),
                ("cross", "Across members"),
                ("detected", "Detected [95% CI]"),
                ("gain", "Gain over S0 [95% CI]"),
                ("p", "p"),
                ("auprc", "AUPRC (mean)"),
            ],
        ),
        "",
        "Random alerts at the same budget: detected "
        f"{fmt((rnd.get('detected') or {}).get('estimate'))}, "
        f"linked {fmt((rnd.get('linked') or {}).get('estimate'))}.",
        "",
        "## H1b on validation: share of the oracle gain recovered",
        "",
        "(level − S0) / (oracle − S0) in linked detection, scheme bootstrap. Preregistered "
        "target: at least 0.60 for S2, judged on test.",
        "",
        table(h1b, [("level", "Level"), ("recovery", "Recovery [95% CI]")]),
        "",
        "## Secondary fusion rules",
        "",
        table(
            sec,
            [
                ("config", "Level / rule"),
                ("linked", "Linked"),
                ("detected", "Detected"),
                ("gain", "Gain over S0"),
                ("auprc", "AUPRC (mean)"),
            ],
        ),
        "",
        "## Protocol per seed",
        "",
        table(
            proto,
            [
                ("seed", "Seed"),
                ("level", "Level"),
                ("requests", "Requests"),
                ("alert", "Answered: alert"),
                ("record", "Record, no alert"),
                ("refused", "Refused"),
                ("tokens", "Token evaluations"),
                ("messages", "Messages"),
                ("seconds", "Seconds"),
            ],
        ),
        "",
        "## Time per seed",
        "",
        table(
            [{"seed": x["seed"], **x["seconds"]} for x in r["per_seed"]],
            [("seed", "Seed")] + [(k, k) for k in r["per_seed"][0]["seconds"]],
        ),
        "",
    ]
    return "\n".join(lines)
