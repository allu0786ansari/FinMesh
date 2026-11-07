"""A25: the Large confirmation decided on its sealed tests, one page.

Reads the Large runs' artifacts (X1 main, artefact-free and stronger-detector tracks from
``data/artifacts/week18``; the narrative's N4 render and the budget replay from
``data/artifacts/a25``) and writes ``docs/eval/a25/RESULTS_LARGE.md``: per Large window,
each rule of ``docs/protocol/improvement_plan_A25.md`` with its estimate, interval and
verdict, then what the plan reports without a rule. Every rule is the frozen one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from finmesh.eval.provenance import read_artifact
from finmesh.eval.test_report import G1_MARGIN, H1B_TARGET, _ci, _yn, x1_rows

LARGE: tuple[str, ...] = ("HI-Large-W16", "LI-Large-W16")
H3B_TARGET = 0.95
Row = tuple[str, str, str, str]


def _load(path: Path) -> dict[str, Any] | None:
    return read_artifact(path)[1] if path.exists() else None


def main_rows(r: dict[str, Any]) -> list[Row]:
    """H1a-L, H1b-L, H1d-L (with S1 as the reference), and the week-18 rows reported."""
    names = {
        "H1a": "H1a-L",
        "H1b": "H1b-L",
        "H1d": "H1d-L",
        "H1c": "H1c (reported)",
        "H3a": "H3a (reported)",
    }
    out: list[Row] = []
    for name, result, rule, holds in x1_rows(r):
        out.append((names.get(name.split(" ")[0], name), result, rule, holds))
    s = r["summary"]
    for f, v in (s.get("flag_check") or {}).items():
        out.append(
            (
                f"Protected flag {f} (reported)",
                f"share of plain S1's gain {_ci(v['share_of_S1_gain'], 2)}; H1c margin "
                f"{_yn(v.get('within_margin'))}",
                "chosen on validation (P3); reported on test",
                "reported",
            )
        )
    cq = s.get("case_quality") or {}
    conf = cq.get("configurations") or {}
    if "S2/stacker" in conf and "S0" in conf:
        a, b = conf["S2/stacker"], conf["S0"]

        def num(x: float | None, d: int = 2) -> str:
            return "—" if x is None else f"{x:.{d}f}"

        diffs = "; ".join(
            f"{k.split(': ')[1]} {_ci(v)}"
            for k, v in (cq.get("comparisons") or {}).items()
            if k.startswith("S2/stacker - S0")
        )
        out.append(
            (
                "Case quality (P2, reported)",
                f"S2 vs S0: completeness {num(a['completeness'])} vs {num(b['completeness'])}, "
                f"fragmentation {num(a['fragmentation'])} vs {num(b['fragmentation'])}, time to "
                f"link (h, median) {num(a['time_to_link_h_median'], 1)} vs "
                f"{num(b['time_to_link_h_median'], 1)}, alerts per linked scheme "
                f"{num(a['workload_alerts_per_linked_scheme'], 1)} vs "
                f"{num(b['workload_alerts_per_linked_scheme'], 1)}"
                + (f"; differences {diffs}" if diffs else ""),
                "reported",
                "reported",
            )
        )
    return out


def _gain_row(r: dict[str, Any], label: str, s2: str, s0: str) -> Row | None:
    s = r["summary"]
    if s2 not in s or s0 not in s:
        return None
    g = s[s2]["linked_gain"]["difference"]
    return (
        label,
        f"{s2.split('/')[0]} {_ci(s[s2]['linked'])} vs {s0} {_ci(s[s0]['linked'])}; gain {_ci(g)}",
        "gain CI above 0",
        _yn(bool(g["low"] is not None and g["low"] > 0)),
    )


def _h1b_row(r: dict[str, Any], label: str) -> Row | None:
    s = r["summary"]
    orc = s.get("oracle-relational")
    h = (s.get("H1b", {}).get("oracle-relational") or {}).get("S2/stacker")
    if not orc or not h:
        return None
    gap = orc["linked_gain"]["difference"]
    eligible = bool(gap["low"] > 0 and gap["estimate"] >= G1_MARGIN)
    return (
        label,
        f"S2 recovers {_ci(h, 2)} of the relational oracle's gain (oracle − S0 {_ci(gap)})",
        f"≥ {H1B_TARGET:.2f}, if oracle − S0 meets the G1 criterion",
        _yn(bool(h["estimate"] is not None and h["estimate"] >= H1B_TARGET))
        if eligible
        else "not assessable",
    )


def noart_rows(r: dict[str, Any]) -> list[Row]:
    row = _gain_row(r, "H1a-L-noart", "S2/stacker", "S0")
    return [row] if row else []


def plus_rows(r: dict[str, Any]) -> list[Row]:
    rows = [_gain_row(r, "H1a-L+", "S2/stacker", "S0"), _h1b_row(r, "H1b-L+")]
    return [x for x in rows if x is not None]


def narrative_rows(r: dict[str, Any]) -> list[Row]:
    s = r["summary"]
    g = s["H3b"]["grounding"]
    return [
        (
            "H3b (N4, chosen)",
            f"grounding {_ci(g)} over {s['cases']} cases; strict (A25N) "
            f"{_ci(s.get('strict_grounding'))}",
            f"raw-reply grounding ≥ {H3B_TARGET:.2f}",
            _yn(bool(g["estimate"] is not None and g["estimate"] >= H3B_TARGET)),
        )
    ]


def replay_rows(r: dict[str, Any]) -> list[Row]:
    sm = r["summary"]
    pt2 = [
        (v.get("A1") or {}).get("adaptive", {}).get("ratio")
        for v in r["seeds"].values()
        if v.get("A1")
    ]
    pt2_txt = "—" if not pt2 or pt2[0] is None else f"{pt2[0]:.3g}"
    return [
        (
            "Adaptive budget (P4, reported)",
            f"refused, adaptive {sm['adaptive_share_refused_max']:.2%} vs frozen "
            f"{sm['frozen_share_refused_max']:.2%}; PT2 at the adaptive budget {pt2_txt}",
            "not adopted (7 Nov); reported as a design result",
            "reported",
        )
    ]


def write_a25_results(
    week18: Path, a25: Path, page: Path, datasets: tuple[str, ...] = LARGE
) -> Path:
    out = [
        "# Results on the Large sealed tests (A25)",
        "",
        "Every rule is the one fixed in `docs/protocol/improvement_plan_A25.md` before the "
        "frozen commit. Each run's full page is in `docs/eval/test/`; every opening is in "
        "`finmesh sealed-log`. A missed rule is a finding, reported in full.",
        "",
    ]
    for ds in datasets:
        rows: list[Row] = []
        sources = (
            (week18 / f"x1_test_{ds}.json", main_rows),
            (week18 / f"x1_test_{ds}_noart.json", noart_rows),
            (week18 / f"x1_test_{ds}_plus.json", plus_rows),
            (a25 / f"narrative_{ds}_test_qwen3-8b_N4.json", narrative_rows),
            (a25 / f"budget_replay_{ds}_cap4x.json", replay_rows),
        )
        for path, fn in sources:
            r = _raw(path) if path.name.startswith("narrative_") else _load(path)
            if r is not None:
                rows += fn(r)
        out += [f"## {ds}", ""]
        if not rows:
            out += ["Not run yet.", ""]
            continue
        out += ["| Rule | Test result | Criterion | Holds |", "| --- | --- | --- | --- |"]
        out += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
        out.append("")
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("\n".join(out))
    return page


def _raw(path: Path) -> dict[str, Any] | None:
    """The narrative render writes its result without a provenance stamp."""
    import json

    return json.loads(path.read_text()) if path.exists() else None


__all__ = ["LARGE", "main_rows", "narrative_rows", "noart_rows", "plus_rows", "write_a25_results"]
