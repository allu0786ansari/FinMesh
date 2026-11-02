"""Week 18: the pre-registered hypotheses decided on the sealed test, one page.

Reads the week-18 artifacts (``data/artifacts/week18``) and writes
``docs/eval/test/RESULTS.md``: per dataset, each hypothesis with its estimate, interval,
the rule from ``docs/protocol/preregistration.md`` and the verdict. A missing run shows
as "not run". Every rule here is the frozen one; nothing is chosen after the fact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from finmesh.data.schema import FIXTURE_DATASET
from finmesh.eval.provenance import read_artifact

DATASETS: tuple[str, ...] = ("HI-Medium", "LI-Medium", "HI-Small", "LI-Small")
H1B_TARGET = 0.60
H1D_GAIN, H1D_DISCLOSURE = 0.80, 0.5
H2A_SHARE = 0.70
G1_MARGIN = 0.05


def _ci(d: dict[str, Any] | None, digits: int = 3) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    f = f"{{:.{digits}f}}"
    if d.get("low") is None:
        return f.format(d["estimate"])
    return f"{f.format(d['estimate'])} [{f.format(d['low'])}, {f.format(d['high'])}]"


def _yn(v: bool | None) -> str:
    return "—" if v is None else ("**yes**" if v else "**no**")


def _load(folder: Path, stem: str) -> dict[str, Any] | None:
    path = folder / f"{stem}.json"
    return read_artifact(path)[1] if path.exists() else None


def _random_linked(r: dict[str, Any]) -> float | None:
    v = (r.get("random") or {}).get("linked")
    if isinstance(v, dict):
        v = v.get("estimate")
    return None if v is None else float(v)


def x1_rows(r: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    s = r["summary"]
    rows: list[tuple[str, str, str, str]] = []
    s2, s0 = s.get("S2/stacker"), s.get("S0")
    if s2 and s0:
        g = s2["linked_gain"]
        p = g.get("p_holm", g["p"])
        rand = _random_linked(r)
        above = rand is None or s2["linked"]["estimate"] > rand
        met = bool(g["difference"]["low"] > 0 and p < 0.05 and above)
        rand_txt = "—" if rand is None else f"{rand:.3f}"
        rows.append(
            (
                "H1a (primary on HI-Medium)",
                f"S2 {_ci(s2['linked'])} vs S0 {_ci(s0['linked'])}; gain "
                f"{_ci(g['difference'])}, Holm p {p:.4g}; random-alert linked {rand_txt}",
                "gain CI excludes 0 (Holm across sharing configurations) and S2 above random",
                _yn(met),
            )
        )
    orc = s.get("oracle-relational")
    h = (s.get("H1b", {}).get("oracle-relational") or {}).get("S2/stacker")
    if orc and h:
        gap = orc["linked_gain"]["difference"]
        eligible = bool(gap["low"] > 0 and gap["estimate"] >= G1_MARGIN)
        rows.append(
            (
                "H1b",
                f"S2 recovers {_ci(h, 2)} of the relational oracle's gain (oracle − S0 {_ci(gap)})",
                f"≥ {H1B_TARGET:.2f}; reported only if oracle − S0 meets the G1 criterion",
                _yn(bool(h["estimate"] is not None and h["estimate"] >= H1B_TARGET))
                if eligible
                else "not assessable",
            )
        )
    h1c = (r.get("audit") or {}).get("H1c")
    if h1c:
        rows.append(
            (
                "H1c",
                "S1 and S3 (ε ≤ 2) attacks within the margin of the prior on every "
                "assessable target; not assessable: "
                + (", ".join(h1c["not_assessable"]) or "none"),
                "upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05",
                _yn(h1c.get("S1_and_S3_le2_within")),
            )
        )
    h1d = s.get("H1d") or {}
    pds = {k: v for k, v in h1d.items() if k.startswith("PD[")}
    if pds:
        parts, met_at = [], []
        for k, v in pds.items():
            g = v["gain_share_of_S2"]
            parts.append(f"{k}: gain {_ci(g, 2)}, disclosure {v['disclosure_share_of_S2']:.2f}")
            if v["met_on_validation"]:
                met_at.append(k)
        rows.append(
            (
                "H1d",
                "; ".join(parts),
                f"gain share ≥ {H1D_GAIN:.2f} with disclosure < {H1D_DISCLOSURE} of S2's",
                f"{_yn(bool(met_at))}" + (f" ({', '.join(met_at)})" if met_at else ""),
            )
        )
    x6 = (r.get("x6") or {}).get("summary")
    if x6:
        h = x6["H3a"]
        rows.append(
            (
                "H3a",
                f"S2 − S0 attributor {_ci(h['S2_minus_S0'])}; S2 − majority "
                f"{_ci(h['S2_above_majority'])}; S2 − rules {_ci(h['S2_above_rules'])}",
                "all three CIs above 0",
                _yn(h["met"]),
            )
        )
    return rows


def x5_rows(r: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    s = r["summary"]
    a = [
        f"ε {e}: share {_ci(v['share_of_centralised'], 2)}, − local {_ci(v['minus_local'], 4)}"
        for e, v in s["H2a"].items()
    ]
    met_a = [e for e, v in s["H2a"].items() if v["met_on_validation"]]
    b = [
        f"ε {e}: window − account {_ci(v['window_minus_account'], 4)}" for e, v in s["H2b"].items()
    ]
    met_b = [e for e, v in s["H2b"].items() if v["met_on_validation"]]
    return [
        (
            "H2a",
            "; ".join(a),
            f"≥ {H2A_SHARE:.2f} of centralised AUPRC and above local-only, at ε ≤ 10",
            _yn(bool(met_a)) + (f" (ε {', '.join(met_a)})" if met_a else ""),
        ),
        (
            "H2b",
            "; ".join(b),
            "window − account AUPRC CI above 0 at the same ε",
            _yn(bool(met_b)) + (f" (ε {', '.join(met_b)})" if met_b else ""),
        ),
    ]


def baseline_rows(r: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    c = r["comparisons"]
    w = c["S0-BG - S0-B"]["window"]["auprc_difference"]
    gap = c["oracle - S0-BG"]["linked"]["difference"]
    noart = c["oracle-noart - S0-BG-noart"]["linked"]["difference"]
    return [
        ("PT4b", f"S0-BG − S0-B AUPRC {_ci(w, 4)}", "CI excludes 0", _yn(bool(w["low"] > 0))),
        (
            "Artefact ablation",
            f"oracle − S0 linked {_ci(gap)} with the artefact features, {_ci(noart)} without",
            "reported (section 8)",
            "reported",
        ),
    ]


def narrative_rows(r: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    s = r["summary"]
    g = s["H3b"]["grounding"]
    st = s.get("strict_grounding") or {}
    top = ((r.get("topk") or {}).get("levels") or {}).get("S2", {})
    return [
        (
            "H3b",
            f"grounding {_ci(g)} over {s['cases']} cases; strict (A23) {_ci(st)}; "
            f"S2 top-3 {_ci(top.get('top3'))}",
            f"raw-reply grounding ≥ {s['H3b']['target']:.2f}",
            _yn(bool(g["estimate"] is not None and g["estimate"] >= s["H3b"]["target"])),
        )
    ]


def ensemble_rows(r: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    s = r["summary"]
    gains = "; ".join(f"{k} {_ci(v, 4)}" for k, v in s["gain_over_local"].items())
    q = s["smallest_qualifying_epsilon"]
    return [
        (
            "Ensemble (G3 rule, reported)",
            gains,
            "smallest ε ≤ 10 with gain CI above 0",
            "none" if q is None else f"ε = {q:g}",
        )
    ]


def write_results(folder: Path, page: Path, fixture: bool = False) -> Path:
    names = list(DATASETS) + ([FIXTURE_DATASET] if fixture else [])
    out = [
        "# Results on the sealed test (week 18)",
        "",
        "Every rule below is the pre-registered one (`docs/protocol/preregistration.md`, "
        "amendments in `docs/proposal/CHANGES.md`), and the run order and openings are those of "
        "`docs/protocol/test_plan.md`. Each run's full page is next to this one; every opening "
        "is in `finmesh sealed-log`. A missed target is a finding, reported in full.",
        "",
    ]
    any_run = False
    for ds in names:
        rows: list[tuple[str, str, str, str]] = []
        for stem, fn in (
            (f"x1_test_{ds}", x1_rows),
            (f"baselines_test_{ds}", baseline_rows),
            (f"x5_test_{ds}", x5_rows),
            (f"ensemble_test_{ds}", ensemble_rows),
            (f"narrative_test_{ds}_A23", narrative_rows),
        ):
            r = _load(folder, stem)
            if r is not None:
                rows += fn(r)
        out += [f"## {ds}", ""]
        if not rows:
            out += ["Not run yet.", ""]
            continue
        any_run = True
        out += ["| Hypothesis | Test result | Rule | Holds |", "| --- | --- | --- | --- |"]
        out += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
        out.append("")
    if not any_run:
        out += ["No test run yet: the seal is closed.", ""]
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("\n".join(out))
    return page


__all__ = ["write_results"]
