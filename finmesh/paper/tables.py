"""The paper's tables as IEEEtran LaTeX (caption above, \\hline rules, footnotesize).

Each file is a complete ``table`` / ``table*`` float with a label ``tab:<name>``. The
numbers come from :mod:`finmesh.paper.sources`; the related-work table is curated text
(``docs/paper/related_work.md`` records the sources).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from finmesh.paper import sources as S

YES, NO = r"\cmark", r"\xmark"


def _tex(s: str) -> str:
    for a, b in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("$", r"\$"),
    ):
        s = s.replace(a, b)
    return s


def _r(x: float, d: int) -> str:
    """Round half up, as tables conventionally do (0.955 -> 0.96)."""
    q = Decimal(repr(x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    return f"{q:.{d}f}"


def _n(x: float, d: int) -> str:
    t = _r(x, d)
    return ("$-$" + t[1:]) if t.startswith("-") and float(t) != 0 else t.lstrip("-")


def _ci(ci: S.CI, d: int = 2) -> str:
    if ci.lo is None or ci.hi is None:
        return _n(ci.est, d)
    return f"{_n(ci.est, d)} [{_n(ci.lo, d)}, {_n(ci.hi, d)}]"


def _mark(v: bool | None) -> str:
    return "" if v is None else (" " + (YES if v else NO))


def _float(env: str, label: str, caption: str, spec: str, rows: list[str], notes: str = "") -> str:
    body = "\n".join(rows)
    note = f"\n\\par\\smallskip\\parbox{{\\linewidth}}{{\\scriptsize {notes}}}" if notes else ""
    return (
        f"\\begin{{{env}}}[!t]\n\\centering\n\\caption{{{caption}}}\n\\label{{tab:{label}}}\n"
        f"\\footnotesize\n\\setlength{{\\tabcolsep}}{{4pt}}\n"
        f"\\begin{{tabular}}{{{spec}}}\n\\hline\n{body}\n\\hline\n\\end{{tabular}}{note}\n"
        f"\\end{{{env}}}\n"
    )


# --------------------------------------------------------------------------- Table I
def datasets() -> tuple[str, dict[str, Any]]:
    rows = [
        r"Test set & Transactions & Laundering & Schemes & Cross-member \\",
        r" & (millions) & rows & & test schemes \\",
        r"\hline",
    ]
    used = {}
    for ds in S.DATASETS:
        st = S.dataset_stats(ds)
        used[ds] = st.__dict__
        rows.append(
            f"{S.LABEL[ds]} & {_r(st.transactions / 1e6, 1)} & {st.laundering:,} & "
            f"{st.schemes:,} & {st.test_multi_member:,} \\\\"
        )
    notes = (
        "Each set is a 16-day dense window of AMLworld, split by 6-h window 60/20/20 into train, "
        "validation and test with one-window gaps; eight institutions (federation B8) hold every "
        "account. Cross-member test schemes: laundering schemes in the test partition that touch "
        "two or more institutions. Medium: the primary tests; Large: the replication tests."
    )
    return _float("table", "datasets", "Test sets", "lrrrr", rows, notes), used


# --------------------------------------------------------------------------- Table II
def results() -> tuple[str, dict[str, Any]]:
    cols = " & ".join(S.LABEL[d] for d in S.DATASETS)
    rows = [f"Pre-registered claim & {cols} \\\\", r"\hline"]
    used: dict[str, Any] = {}

    def line(name: str, cells: list[str]) -> None:
        rows.append(f"{name} & " + " & ".join(cells) + r" \\")

    g = {ds: S.gain(ds) for ds in S.DATASETS}
    line(
        r"H1a: S2 $-$ S0 linked detection",
        [_ci(g[d]) + _mark(S.verdict(d, _h(d, "H1a"))) for d in S.DATASETS],
    )
    r = {ds: S.recovery(ds) for ds in S.DATASETS}
    line(
        r"H1b: share of oracle gain ($\geq$0.60)",
        [_ci(r[d]) + _mark(S.verdict(d, _h(d, "H1b"))) for d in S.DATASETS],
    )
    adv = {ds: S.attack_advantage(ds) for ds in S.DATASETS}
    line(
        r"H1c: plain flag, fan-in advantage",
        [_ci(adv[d]["S1"], 3) + _mark(S.verdict(d, "H1c")) for d in S.DATASETS],
    )
    line(
        r"\quad gated flag (A25)",
        ["---" for _ in S.MEDIUM]
        + [_ci(adv[d]["S1F[gate=2]"], 3) + _mark(S.flag_within(d)) for d in S.LARGE],
    )
    best = {ds: S.h1d_best(ds) for ds in S.DATASETS}
    line(
        r"H1d: PD gain share, least disclosure",
        [
            (f"{_r(b[1].est, 2)} at {'$<$0.01' if b[2] < 0.005 else _r(b[2], 2)}" if b else "---")
            + _mark(b is not None)
            for b in (best[d] for d in S.DATASETS)
        ],
    )
    line("H3a: attribution above baselines", [_mark(S.h3a(d)).strip() for d in S.DATASETS])
    h3b = {ds: S.h3b(ds) for ds in S.DATASETS}
    line(
        r"H3b: narrative grounding ($\geq$0.95)",
        [_ci(h3b[d]) + _mark(h3b[d].est >= 0.95) for d in S.DATASETS],
    )
    p = {ds: S.pt2(ds) for ds in S.DATASETS}
    line(
        r"PT2: hashing $\div$ OPRF re-id. ($\geq$10)",
        [_r(p[d], 1) + _mark(p[d] >= 10) for d in S.DATASETS],
    )
    used = {
        "gain": g,
        "recovery": r,
        "h1d": best,
        "h3b": h3b,
        "pt2": p,
        "advantage": {
            d: {"S1": adv[d]["S1"], "S1F": adv[d].get("S1F[gate=2]")} for d in S.DATASETS
        },
    }
    notes = (
        r"Sealed tests; 95\% intervals from a scheme bootstrap. H1c: upper 95\% bound of "
        r"(attack $-$ prior) TPR at 1\% FPR at most 0.05 on every attack target (A2, A3); the "
        r"value shown is the binding target, A3 fan-in, and the mark is the verdict over all "
        r"targets and, for the plain flag, the S3 levels with $\varepsilon\leq 2$. "
        r"H1d: PD configuration reaching $\geq$0.80 of S2's gain with the "
        r"smallest share of S2's disclosed accounts. H3b on Medium: free-text narratives; "
        r"on Large: select-then-template (N4). Medium columns: primary tests; "
        r"Large: replication tests. H2 (a federated DP scorer, a supporting track) "
        r"is reported in Section~\ref{sec:limits}."
    )
    return _float(
        "table*", "results", "Pre-registered claims on the sealed tests", "lcccc", rows, notes
    ), {k: _plain(v) for k, v in used.items()}


def _h(ds: str, rule: str) -> str:
    return f"{rule}-L" if ds in S.LARGE else rule


def _plain(v: Any) -> Any:
    if isinstance(v, S.CI):
        return v.__dict__
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, tuple):
        return [_plain(x) for x in v]
    return v


# --------------------------------------------------------------------------- Table III
def case_quality() -> tuple[str, dict[str, Any]]:
    rows = [
        r"Measure & \multicolumn{2}{c}{HI-Large} & \multicolumn{2}{c}{LI-Large} \\",
        r" & S0 & S2 & S0 & S2 \\",
        r"\hline",
    ]
    used = {}
    data = {ds: S.case_quality(ds) for ds in S.LARGE}
    for key, name, fmt in (
        ("completeness", "Scheme accounts in the case", 2),
        ("fragmentation", "Cases per linked scheme", 2),
        ("alerts", "Alerts per linked scheme", 0),
    ):
        cells = []
        for ds in S.LARGE:
            s2, s0 = data[ds][key]
            cells += [f"{int(_r(v, 0)):,}" if fmt == 0 else _r(v, fmt) for v in (s0, s2)]
        rows.append(f"{name} & " + " & ".join(cells) + r" \\")
    used = {ds: data[ds] for ds in S.LARGE}
    notes = (
        "Per detected scheme, seed-averaged: share of the scheme's accounts in its largest case "
        "(completeness), number of cases it is split into (fragmentation), and alerts raised per "
        "scheme linked (analyst workload). Replication tests, seeds 0--4."
    )
    return _float(
        "table", "casequality", "Case quality and analyst workload", "lrrrr", rows, notes
    ), used


# --------------------------------------------------------------------------- Table IV
def benchmark() -> tuple[str, dict[str, Any]]:
    b = S.benchmark()
    rename = {
        "A · our pooled detector": "Ours, account-window detector",
        "B · transaction LightGBM + our features": "Ours, transaction model",
        "LightGBM + graph features (published)": "LightGBM + graph features [egressy2024]",
        "XGBoost + graph features (published)": "XGBoost + graph features [egressy2024]",
        "Multi-PNA + EU (published)": "Multi-PNA + EU [egressy2024]",
    }
    order = ("HI-Small", "LI-Small", "HI-Medium", "LI-Medium")
    cols = [c for c in order if any(c in v for v in b.values())]

    def mean(text: str) -> float | None:
        try:
            return float(text.split("±")[0])
        except ValueError:
            return None

    best = {
        c: max((m for v in b.values() if (m := mean(v.get(c, ""))) is not None), default=None)
        for c in cols
    }
    rows = ["Model & " + " & ".join(cols) + r" \\", r"\hline"]
    for k, v in b.items():
        name = _tex(rename.get(k, k)).replace("[egressy2024]", r"\cite{egressy2024}")
        cells = []
        for c in cols:
            text = v.get(c, "---")
            cell = text.replace("±", r"$\pm$")
            if mean(text) is not None and mean(text) == best[c]:
                cell = r"\textbf{" + cell + "}"
            cells.append(cell)
        rows.append(f"{name} & " + " & ".join(cells) + r" \\")
    notes = (
        "Minority-class F1 (\\%) on AMLworld's published split (all transactions, by day "
        "60/20/20), threshold chosen on validation; ours: mean $\\pm$ s.d. over 5 seeds; best "
        "per column in bold. Pooled data in every row (the published models see all banks)."
    )
    spec = "l" + "c" * len(cols)
    env = "table*" if len(cols) > 2 else "table"
    return _float(env, "benchmark", "Detector against published results", spec, rows, notes), b


# --------------------------------------------------------------------------- Table V
def narrative() -> tuple[str, dict[str, Any]]:
    cands = (
        ("N0", "llama3.2:3b", "llama3.2-3b"),
        ("N1", "qwen2.5:7b", "qwen2.5-7b"),
        ("N2", "llama3.1:8b", "llama3.1-8b"),
        ("N3", "qwen3:8b", "qwen3-8b"),
    )
    judge = S.judge()
    rows = [
        r"Design & Grounding & Strict & Faithful \\",
        r"\hline",
        r"\multicolumn{4}{l}{\emph{HI-Medium validation, 200 cases (judge: 30)}} \\",
    ]
    used: dict[str, Any] = {}
    for nid, model, tag in cands:
        g, st = S.narrative_page(f"narrative_HI-Medium_val_{tag}")
        f = judge.get(f"{nid} {model}", (0, 30))
        used[nid] = {"grounding": g.__dict__, "strict": st.__dict__, "faithful": f}
        rows.append(
            f"{nid}: \\texttt{{{model}}}, free text & {_r(g.est, 2)} & {_r(st.est, 2)} & "
            f"{f[0]}/{f[1]} \\\\"
        )
    g, st = S.narrative_page("narrative_HI-Medium_val_qwen3-8b_N4")
    f = judge.get("N4 on N3 (chosen)", (0, 30))
    used["N4"] = {"grounding": g.__dict__, "strict": st.__dict__, "faithful": f}
    rows.append(
        f"N4: select-then-template (N3) & {_r(g.est, 2)} & {_r(st.est, 2)} & {f[0]}/{f[1]} \\\\"
    )
    rows.append(r"\hline")
    rows.append(r"\multicolumn{4}{l}{\emph{N4 on the replication tests}} \\")
    for ds in S.LARGE:
        g, st = S.narrative_page(f"narrative_{ds}_test_qwen3-8b_N4")
        used[f"N4 {ds}"] = {"grounding": g.__dict__, "strict": st.__dict__}
        rows.append(f"{S.LABEL[ds]} & {_r(g.est, 2)} & {_r(st.est, 2)} & --- \\\\")
    notes = (
        "Grounding (H3b): first reply is valid, keeps the attributed typology and cites only "
        "evidence fields. Strict: also 1--4 fields, every number from the evidence, claim "
        "consistency and scope. Faithful: automated judge (one rater, not blind) on the 30-case "
        "sheet; delivered text after retry and template fallback."
    )
    return _float(
        "table",
        "narrative",
        "Case narratives: local models and select-then-template",
        "lccc",
        rows,
        notes,
    ), used


def build(out: Path, related: Path | None = None) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    numbers: dict[str, Any] = {}
    for fn in (datasets, results, case_quality, benchmark, narrative):
        tex, used = fn()
        (out / f"tab_{fn.__name__}.tex").write_text(tex)
        numbers[fn.__name__] = _plain(used)
    if related is not None and related.exists():
        (out / "tab_related.tex").write_text(related.read_text())
    return numbers


__all__ = ["build"]
