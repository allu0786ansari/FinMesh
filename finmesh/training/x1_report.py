"""Pages and figures for X1-X3 on validation (weeks 7-8).

* ``x1_<ds>.md`` and ``ladder_<ds>.png``: linked detection per sharing level, the
  oracles, H1b against both ceilings (A14), secondary fusion rules, protocol.
* ``x3_<ds>.md`` and ``x3_<ds>.png``: S3 recall versus ε, PD recall versus
  disclosure volume, H1d.
* ``audit_<ds>.md`` and ``frontier_<ds>.png``: attacks A1-A3 and the
  utility-leakage frontier (linked detection against the strongest excess
  attack success per level).
"""

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
    "oracle+propagation",
    "oracle-relational",
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
    "oracle": "Oracle (pooled, preregistered)",
    "oracle+propagation": "Oracle + propagation (pooled)",
    "oracle-relational": "Relational oracle (pooled, A14 ceiling)",
}
COLOURS = {
    "S0": "#7a7a7a",
    "S1/stacker": "#2b6cb0",
    "S2/stacker": "#2b6cb0",
    "S4/stacker": "#2b6cb0",
    "propagation": "#b7791f",
    "oracle": "#2f855a",
    "oracle+propagation": "#2f855a",
    "oracle-relational": "#22543d",
}
ATTACK_LABELS = {
    "A2_third_party": "A2 third-member relationship",
    "A3_amount_top": "A3 amount in top decile",
    "A3_fan_in_top": "A3 fan-in in top decile",
    "A3_pass_through": "A3 pass-through account",
}


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def _yes_no(v: bool | None) -> str:
    return "—" if v is None else ("yes" if v else "no")


def _short(name: str) -> str:
    return name.split("/")[0].replace("[eps=", " ε=").replace("[tau=", " τ=").rstrip("]")


def _est(d: dict[str, Any] | None) -> float | None:
    return None if not d else d.get("estimate")


def _plt() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _title(r: dict[str, Any]) -> str:
    return f"{r['dataset']} validation · {r['primary_budget']} · seeds {r['seeds']}"


def ladder_figure(r: dict[str, Any], path: Path) -> Path:
    plt = _plt()
    s = r["summary"]
    names = [n for n in ORDER if n in s]
    est = [s[n]["linked"]["estimate"] for n in names]
    lo = [s[n]["linked"]["estimate"] - s[n]["linked"]["low"] for n in names]
    hi = [s[n]["linked"]["high"] - s[n]["linked"]["estimate"] for n in names]
    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=150)
    xs = list(range(len(names)))
    ax.bar(xs, est, color=[COLOURS[n] for n in names], width=0.62)
    ax.errorbar(xs, est, yerr=[lo, hi], fmt="none", ecolor="#1a202c", capsize=4, lw=1)
    rnd = (r.get("random") or {}).get("linked") or {}
    if rnd.get("estimate") is not None:
        ax.axhline(rnd["estimate"], color="#c53030", ls="--", lw=1, label="random alerts")
        ax.legend(frameon=False, loc="upper left")
    ax.set_xticks(
        xs,
        [LABELS[n].replace(" (", "\n(").replace(" + ", "\n+ ") for n in names],
        fontsize=7,
    )
    ax.set_ylabel("Linked scheme detection")
    ax.set_ylim(0, 1)
    ax.set_title(_title(r), fontsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


# Backwards-compatible name (week 7).
frontier_bars = ladder_figure


def _sweep_names(s: dict[str, Any], prefix: str) -> list[tuple[float, str]]:
    out = []
    for n in s:
        if n.startswith(prefix) and n.endswith("/stacker"):
            out.append((float(n.split("=")[1].split("]")[0]), n))
    return sorted(out)


def x3_figure(r: dict[str, Any], path: Path) -> Path | None:
    s = r["summary"]
    s3 = _sweep_names(s, "S3[")
    pd_ = _sweep_names(s, "PD[")
    if not s3 and not pd_:
        return None
    plt = _plt()
    fig, (a, b) = plt.subplots(1, 2, figsize=(9, 3.8), dpi=150)
    for ax in (a, b):
        for name, style in (("S1/stacker", ":"), ("S2/stacker", "--"), ("S0", "-.")):
            if name in s:
                ax.axhline(
                    s[name]["linked"]["estimate"],
                    color="#4a5568",
                    ls=style,
                    lw=1,
                    label=name.split("/")[0],
                )
        ax.set_ylim(0, 1)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    if s3:
        eps = [e for e, _ in s3]
        v = [s[n]["linked"] for _, n in s3]
        a.errorbar(
            eps,
            [x["estimate"] for x in v],
            yerr=[
                [x["estimate"] - x["low"] for x in v],
                [x["high"] - x["estimate"] for x in v],
            ],
            marker="o",
            color="#2b6cb0",
            capsize=3,
            label="S3",
        )
        a.set_xscale("log", base=2)
        a.set_xticks(eps, [f"{e:g}" for e in eps])
        a.set_xlabel("Evidence ε per record")
        a.set_ylabel("Linked scheme detection")
        a.set_title("S3: recall versus ε", fontsize=9)
        a.legend(frameon=False, fontsize=7, loc="lower right")
    if pd_:
        h1d = s.get("H1d", {})
        xs, ys, labels = [], [], []
        for tau, n in pd_:
            key = n.split("/")[0]
            if key in h1d:
                xs.append(h1d[key]["disclosure_share_of_S2"])
                ys.append(s[n]["linked"]["estimate"])
                labels.append(f"τ={tau:g}")
        b.plot(xs, ys, marker="o", color="#b7791f", label="PD")
        for x, y, lab in zip(xs, ys, labels, strict=True):
            b.annotate(lab, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=7)
        b.axvline(0.5, color="#c53030", ls="--", lw=0.8)
        b.set_xlim(-0.02, 1.05)
        b.set_xlabel("Accounts with records disclosed (share of S2)")
        b.set_title("PD: recall versus disclosure volume", fontsize=9)
        b.legend(frameon=False, fontsize=7, loc="lower right")
    fig.suptitle(_title(r), fontsize=9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def _excess(audit: dict[str, Any], name: str) -> float | None:
    """Strongest excess attack success of a level: max over A2/A3 of attack - prior TPR@1%."""
    vals = []
    for res in audit.get("attacks", {}).values():
        d = res.get(name, {}).get("diff_tpr_0.01", {})
        if d.get("estimate") is not None:
            vals.append(d["estimate"])
    return max(vals) if vals else None


def frontier_figure(r: dict[str, Any], path: Path) -> Path | None:
    """Utility-leakage frontier: linked detection against the strongest excess attack."""
    audit = r.get("audit") or {}
    if not audit.get("attacks"):
        return ladder_figure(r, path)
    s = r["summary"]
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    points = [("S0", 0.0)]
    for name in audit["levels"]:
        x = _excess(audit, name)
        if x is not None and f"{name}/stacker" in s:
            points.append((f"{name}/stacker", x))
    for key, x in points:
        y = s[key]["linked"]["estimate"]
        base = key.split("/")[0]
        colour = (
            "#7a7a7a"
            if base == "S0"
            else "#2b6cb0"
            if base.startswith("S3")
            else "#b7791f"
            if base.startswith("PD")
            else "#1a365d"
        )
        ax.scatter([x], [y], color=colour, s=28, zorder=3)
        ax.annotate(_short(base), (x, y), textcoords="offset points", xytext=(4, 3), fontsize=7)
    for name, style in (("oracle", "--"), ("oracle-relational", "-")):
        if name in s:
            ax.axhline(
                s[name]["linked"]["estimate"], color="#2f855a", ls=style, lw=1, label=LABELS[name]
            )
    ax.axvline(audit.get("margin", 0.05), color="#c53030", ls=":", lw=1, label="H1c margin")
    ax.set_xlabel("Excess attack success: max over A2/A3 of (attack − prior) TPR at 1% FPR")
    ax.set_ylabel("Linked scheme detection")
    ax.set_ylim(0, 1)
    ax.set_title("Utility–leakage frontier · " + _title(r), fontsize=9)
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def _protocol_rows(r: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for seed in r["per_seed"]:
        for level, p in seed["protocol"].items():
            resp = p.get("responses", {})
            rows.append(
                {
                    "seed": seed["seed"],
                    "level": level,
                    "requests": p.get("requests"),
                    "alert": sum(v for k, v in resp.items() if k.endswith("_alert")),
                    "record": resp.get("ok", 0),
                    "refused": resp.get("refused", 0),
                    "accounts": p.get("accounts_disclosed"),
                    "withheld": p.get("ldp_withheld"),
                    "max_eps": p.get("ldp_max_account_epsilon"),
                    "tokens": p.get("service_evaluations"),
                    "seconds": p.get("seconds_total"),
                }
            )
    return rows


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
    h1b_rows = []
    ceilings = s.get("H1b", {})
    primary = ("S1/stacker", "S2/stacker", "S4/stacker")
    for level in primary:
        row: dict[str, Any] = {"level": level.split("/")[0]}
        for ceiling, per in ceilings.items():
            row[ceiling] = _ci(per.get(level))
        h1b_rows.append(row)
    rnd = r.get("random") or {}
    lines = [
        f"# X1 · sharing ladder on validation · {r['dataset']}",
        "",
        f"Seeds {r['seeds']}; primary budget {r['primary_budget']}; schemes detected within "
        f"{r['delay_windows']} windows; primary fusion **{r['primary_fusion']}** (A13); H1b "
        f"ceiling **{r.get('h1b_ceiling', 'oracle')}** (A14). Per-scheme outcomes are averaged "
        f"over seeds before the scheme bootstrap. Total {r['seconds']:,.0f} s, peak memory "
        f"{r['peak_anon_mb']:,.0f} MB. S3 and PD sweeps: `x3_{r['dataset']}.md`; leakage "
        f"audit: `audit_{r['dataset']}.md`.",
        "",
    ]
    if figure:
        lines += [f"![Linked detection per configuration]({figure})", ""]
    lines += [
        "## Linked detection per configuration (primary fusion)",
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
        "## H1b on validation: share of the ceiling's gain recovered",
        "",
        "(level − S0) / (ceiling − S0) in linked detection, scheme bootstrap. The relational "
        "oracle (pooled data with the same re-ranking, plaintext) is the ceiling from A14; the "
        "preregistered oracle is kept for comparison. Target: at least 0.60 for S2, judged on "
        "test.",
        "",
        table(
            h1b_rows,
            [("level", "Level")] + [(c, f"Against {c} [95% CI]") for c in ceilings],
        ),
        "",
        "## Secondary fusion rules",
        "",
        "k-of-n uses only alert flags and noisy-OR only flags and the probability bucket, so "
        "their S2 and S4 rows coincide by construction.",
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
        "Token evaluations are counted by the first level that needs them; later levels reuse "
        "the same tokens.",
        "",
        table(
            _protocol_rows(r),
            [
                ("seed", "Seed"),
                ("level", "Level"),
                ("requests", "Requests"),
                ("alert", "Answered: alert"),
                ("record", "Record, no alert"),
                ("refused", "Refused"),
                ("accounts", "Accounts disclosed"),
                ("withheld", "LDP withheld"),
                ("max_eps", "Max ε per account"),
                ("tokens", "Token evaluations"),
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


def render_x3(r: dict[str, Any], figure: str | None) -> str:
    s = r["summary"]
    h1d = s.get("H1d", {})
    s3_rows = []
    for eps, n in _sweep_names(s, "S3["):
        key = n.split("/")[0]
        prot = [seed["protocol"].get(key, {}) for seed in r["per_seed"]]
        s3_rows.append(
            {
                "eps": eps,
                "linked": _ci(s[n]["linked"]),
                "gain": _ci(s[n]["linked_gain"]["difference"]),
                "share": _ci((s.get("H1b", {}).get("oracle-relational") or {}).get(n)),
                "withheld": sum(p.get("ldp_withheld", 0) for p in prot) / max(len(prot), 1),
                "max_eps": max((p.get("ldp_max_account_epsilon", 0) for p in prot), default=0),
            }
        )
    pd_rows = []
    for tau, n in _sweep_names(s, "PD["):
        key = n.split("/")[0]
        d = h1d.get(key, {})
        pd_rows.append(
            {
                "tau": tau,
                "linked": _ci(s[n]["linked"]),
                "gain_share": _ci(d.get("gain_share_of_S2")),
                "disclosure": d.get("disclosure_share_of_S2"),
                "accounts": d.get("accounts_disclosed_mean"),
                "met": d.get("met_on_validation"),
            }
        )
    s1_ref = (h1d.get("S1") or {}).get("gain_share_of_S2")
    lines = [
        f"# X3 · evidence-channel privacy on validation · {r['dataset']}",
        "",
        f"Seeds {r['seeds']}; primary budget {r['primary_budget']}; primary fusion stacker, "
        "fitted on evidence released through the same mechanism. S3: every record field but "
        "the time bucket and alert flag through k-ary randomised response at ε / 20 per field, "
        "memoised per record, at most ε = 8 per account and epoch (over budget: the S1 answer). "
        "PD: the S1 answer, plus the S2 record when the requester's score bucket is at least τ.",
        "",
    ]
    if figure:
        lines += [f"![S3 and PD sweeps]({figure})", ""]
    lines += [
        "## S3: recall versus ε",
        "",
        table(
            s3_rows,
            [
                ("eps", "ε per record"),
                ("linked", "Linked [95% CI]"),
                ("gain", "Gain over S0"),
                ("share", "Share of relational-oracle gain"),
                ("withheld", "Records withheld (budget), mean per seed"),
                ("max_eps", "Max ε spent on one account"),
            ],
        ),
        "",
        "## PD: recall versus disclosure volume (H1d)",
        "",
        "H1d: at least 0.80 of S2's gain over S0 with records disclosed on fewer than half as "
        "many accounts as S2. Judged on test; validation shown here.",
        "",
        table(
            pd_rows,
            [
                ("tau", "τ (requester bucket)"),
                ("linked", "Linked [95% CI]"),
                ("gain_share", "Share of S2 gain [95% CI]"),
                ("disclosure", "Accounts disclosed, share of S2"),
                ("accounts", "Accounts disclosed (mean)"),
                ("met", "H1d met on validation"),
            ],
        ),
        "",
        f"Reference: S1, which discloses no record, reaches {_ci(s1_ref)} of S2's gain. When "
        "this is itself at least 0.80, H1d holds for any τ and says little about disclosure; "
        "the informative comparison is then PD against S1.",
        "",
    ]
    return "\n".join(lines)


def render_audit(r: dict[str, Any], figure: str | None) -> str:
    a = r.get("audit") or {}
    lines = [
        f"# Leakage audit A1–A3 on validation · {r['dataset']}",
        "",
        f"Seed {a.get('seed')}. An honest-but-curious peer attacks everything it receives. "
        "A2 and A3 use a strong adversary: a gradient-boosted classifier trained on the true "
        "attributes of half the queried accounts (split by account), tested on the other half, "
        "against a prior-only attack that sees what the adversary knew before asking (its own "
        "accounts in the request, its score bucket, the window and the two banks). Intervals "
        "bootstrap the queried accounts. H1c margin (A15): upper 95% bound of (attack − prior) "
        f"TPR at 1% FPR at most {a.get('margin')}.",
        "",
    ]
    if figure:
        lines += [f"![Utility-leakage frontier]({figure})", ""]
    t = a.get("targets", {})
    if t:
        lines += [
            f"Targets: {t['n']:,} (adversary, counterparty, window) triples; test half "
            f"{t['test']:,}. Prevalence: "
            + "; ".join(f"{ATTACK_LABELS[k]} {v:.3f}" for k, v in t["prevalence"].items())
            + ".",
            "",
        ]
    for target, res in a.get("attacks", {}).items():
        rows = []
        for name, m in res.items():
            if not isinstance(m, dict) or "auc" not in m:
                continue
            rows.append(
                {
                    "level": name,
                    "tpr_001": _ci(m.get("tpr_0.001")),
                    "tpr_01": _ci(m.get("tpr_0.01")),
                    "auc": _ci(m.get("auc")),
                    "diff": _ci(m.get("diff_tpr_0.01")),
                    "within": _yes_no(
                        ((a.get("H1c", {}).get("within_by_target") or {}).get(name) or {}).get(
                            target
                        )
                    ),
                }
            )
        lines += [
            f"## {ATTACK_LABELS.get(target, target)}",
            "",
            table(
                rows,
                [
                    ("level", "Level"),
                    ("tpr_001", "TPR at 0.1% FPR"),
                    ("tpr_01", "TPR at 1% FPR"),
                    ("auc", "AUC"),
                    ("diff", "Attack − prior, TPR at 1%"),
                    ("within", "Within margin"),
                ],
            ),
            "",
        ]
        if "S4_minus_S2_tpr_0.01" in res:
            lines += [f"S4 − S2, TPR at 1% FPR: {_ci(res['S4_minus_S2_tpr_0.01'])}.", ""]
    h = a.get("H1c", {})
    if h:
        lines += [
            "## H1c on validation",
            "",
            "- S1 and S3 (ε ≤ 2) within the margin on every assessable A2/A3 target: "
            f"**{_yes_no(h.get('S1_and_S3_le2_within'))}**",
            "- Per level (all assessable targets within): "
            + ", ".join(f"{_short(k)} {_yes_no(v)}" for k, v in h.get("within_margin", {}).items()),
            f"- Targets without enough positives in the test half to assess: "
            f"{', '.join(ATTACK_LABELS.get(t, t) for t in h.get('not_assessable', [])) or 'none'}",
            f"- S4 above S2 (CI of the difference above 0), per target: {h.get('S4_above_S2')}",
            "- S3 TPR at 1% FPR by ε (monotone expected): "
            + "; ".join(
                f"{ATTACK_LABELS.get(k, k)}: " + ", ".join(f"{e:g}→{fmt(v)}" for e, v in vals)
                for k, vals in (h.get("S3_tpr_by_epsilon") or {}).items()
            ),
            "",
        ]
    a1 = a.get("A1")
    if a1:
        rows = [
            {
                **x,
                "hash": fmt(x["hash"]),
                "oprf_deployed": fmt(x["oprf_deployed"]),
                "oprf_sized": fmt(x["oprf_sized"]),
            }
            for x in a1["per_adversary"]
        ]
        p = a1["pooled"]
        lines += [
            "## A1 token re-identification",
            "",
            "Targets: the tokens of every other member's evidence records. Candidates: every "
            "account at another member that the adversary's customers traded with up to the end "
            "of validation. Hashing: all candidates tokenised offline, unmetered. OPRF: "
            "candidates tokenised within the spare per-epoch budget (deployed "
            f"{a1['deployed_budget']:,}; sized to twice the largest legitimate use, "
            f"{a1['sized_budget']:,}), every query logged. Expected re-identification with "
            "candidates queried in random order.",
            "",
            table(
                rows,
                [
                    ("adversary", "Adversary"),
                    ("targets", "Target tokens"),
                    ("candidates", "Candidates"),
                    ("legit_queries", "Legitimate queries"),
                    ("hash", "Hashing"),
                    ("oprf_deployed", "OPRF, deployed budget"),
                    ("oprf_sized", "OPRF, sized budget"),
                    ("oprf_sized_attack_queries", "Attack queries (sized)"),
                ],
            ),
            "",
            f"Pooled: hashing {fmt(p['hash'])}, OPRF deployed {fmt(p['oprf_deployed'])}, OPRF "
            f"sized {fmt(p['oprf_sized'])}. Hashing ÷ OPRF (sized): "
            f"{fmt(a1['ratio_hash_to_oprf_sized'])} (PT2 asks for at least 10).",
            "",
            f"Mechanism check on real tokens: {a1['mechanism_check']}.",
            "",
        ]
    return "\n".join(lines)
