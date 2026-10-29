"""Gate G2 evidence: the sharing study on validation (end of week 9).

The proposal ties G2 to the headline (X1–X3 and the audit on validation) and to
three risks: LDP noise destroying the fusion signal, OPRF integration, and
attacks too weak to be credible. This page gathers, per dataset, each
hypothesis's status on validation and each risk check from the X1 artifacts.
Test decides the hypotheses; nothing here opens it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir
from finmesh.reporting import fmt, table

DATASETS = ("HI-Medium", "LI-Medium")
WEEKS = ("week09", "week08")


def load(dataset: str) -> tuple[str, dict[str, Any]] | None:
    for week in WEEKS:
        path = artifacts_dir() / week / f"x1_{dataset}.json"
        if path.exists():
            prov, r = read_artifact(path)
            if not prov["fixture"]:
                return week, r
    return None


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def _yn(v: bool | None) -> str:
    return "—" if v is None else ("yes" if v else "no")


def summarise(dataset: str, week: str, r: dict[str, Any]) -> dict[str, Any]:
    s = r["summary"]
    a = r.get("audit") or {}
    h1c = a.get("H1c") or {}
    a1 = a.get("A1") or {}
    s2 = s["S2/stacker"]
    rnd = (r.get("random") or {}).get("linked") or {}
    gain = s2["linked_gain"]["difference"]
    ratio = a1.get("ratio_hash_to_oprf_protocol", a1.get("ratio_hash_to_oprf_deployed"))
    rec = s["H1b"].get("oracle-relational", {}).get("S2/stacker") or {}
    s3_2 = s.get("S3[eps=2]/stacker", {}).get("linked", {}).get("estimate")
    a4 = a.get("A4") or {}
    s4_above = h1c.get("S4_above_S2") or {}
    return {
        "dataset": dataset,
        "week": week,
        "h1a": (
            f"S2 − S0 {_ci(gain)}, p {fmt(s2['linked_gain']['p'])}; "
            f"S2 {fmt(s2['linked']['estimate'])} vs random {fmt(rnd.get('estimate'))}"
        ),
        "h1a_met": bool(
            (gain.get("low") or 0) > 0 and s2["linked"]["estimate"] > (rnd.get("estimate") or 0)
        ),
        "h1b": "; ".join(
            f"vs {c} {_ci((s['H1b'].get(c) or {}).get('S2/stacker'))}"
            for c in ("oracle-relational", "strongest-pooled", "oracle")
            if c in s["H1b"]
        ),
        "h1b_met": bool((rec.get("estimate") or 0) >= 0.6),
        "h1c": (
            f"S1 and S3 (ε ≤ 2) within margin: {_yn(h1c.get('S1_and_S3_le2_within'))}; "
            f"S4 above S2 on {sum(bool(v) for v in s4_above.values())} of {len(s4_above)} targets"
        ),
        "h1c_met": h1c.get("S1_and_S3_le2_within"),
        "h1d": "; ".join(
            f"τ={k.split('=')[1].rstrip(']')}: "
            f"{fmt((v.get('gain_share_of_S2') or {}).get('estimate'))} of S2's gain, "
            f"{fmt(v.get('disclosure_share_of_S2'))} of its disclosures"
            for k, v in (s.get("H1d") or {}).items()
            if k.startswith("PD[")
        )
        + f" (S1 alone: {_ci(((s.get('H1d') or {}).get('S1') or {}).get('gain_share_of_S2'))})",
        "pt2": f"hashing ÷ OPRF at the protocol budget: {fmt(ratio)}",
        "pt2_met": bool(ratio is not None and ratio >= 10),
        "risk_ldp": (
            f"S3 (ε = 2) {fmt(s3_2)} against S2 {fmt(s2['linked']['estimate'])}"
            if s3_2 is not None
            else "—"
        ),
        "risk_ldp_ok": bool(s3_2 is not None and s3_2 >= s2["linked"]["estimate"] - 0.05),
        "risk_oprf": f"mechanism check {a1.get('mechanism_check')}; token refusals "
        + str(
            sum(
                p.get("service_refused", 0)
                for seed in r["per_seed"]
                for p in seed["protocol"].values()
            )
        ),
        "risk_oprf_ok": bool(
            (a1.get("mechanism_check") or {}).get("oprf_matches")
            == (a1.get("mechanism_check") or {}).get("checked")
            and all(
                p.get("service_refused", 0) == 0
                for seed in r["per_seed"]
                for p in seed["protocol"].values()
            )
        ),
        "risk_attacks": (
            f"hashing re-identifies {fmt((a1.get('pooled') or {}).get('hash'))}; "
            f"S4 above S2 on {sum(bool(v) for v in s4_above.values())} targets; "
            f"A4 S2 hit@1 {fmt((a4.get('S2') or {}).get('hit1'))} vs chance "
            f"{fmt((a4.get('S2') or {}).get('chance_hit1'))}"
        ),
        "risk_attacks_ok": bool(
            ((a1.get("pooled") or {}).get("hash") or 0) > 0.1 and any(s4_above.values())
        ),
    }


def render_g2(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "# Gate G2 evidence\n\nNo HI-Medium or LI-Medium X1 artifact yet.\n"
    items = [
        ("H1a: S2 beats S0 and random", "h1a", "h1a_met"),
        ("H1b: S2 recovers ≥ 0.60 of the ceiling's gain (A14)", "h1b", "h1b_met"),
        ("H1c: S1 and S3 (ε ≤ 2) within the 0.05 margin; S4 above S2", "h1c", "h1c_met"),
        ("H1d: PD (reported with the S1 reference)", "h1d", None),
        ("PT2: OPRF at least 10× below hashing (A16 budget)", "pt2", "pt2_met"),
        ("Risk: LDP noise destroys the fusion signal", "risk_ldp", "risk_ldp_ok"),
        ("Risk: OPRF integration", "risk_oprf", "risk_oprf_ok"),
        ("Risk: attacks too weak (positive controls)", "risk_attacks", "risk_attacks_ok"),
    ]
    lines = [
        "# Gate G2 evidence · sharing study on validation",
        "",
        "Generated by `finmesh g2` from the X1 artifacts (week 9, or week 8 where week 9 is "
        "absent). Hypotheses are judged on test in week 18; this is validation. Each row says "
        "whether the validation result points the way the hypothesis or risk check wants.",
        "",
    ]
    for r in rows:
        tab = [
            {"item": label, "value": r[key], "ok": _yn(r[ok]) if ok else "—"}
            for label, key, ok in items
        ]
        lines += [
            f"## {r['dataset']} (artifacts {r['week']})",
            "",
            table(tab, [("item", "Item"), ("value", "Validation"), ("ok", "Points the right way")]),
            "",
        ]
    return "\n".join(lines)


def run_g2(out: Path) -> Path | None:
    """Write the page; without any real-data artifact (CI), leave an existing page alone."""
    rows = []
    for ds in DATASETS:
        got = load(ds)
        if got is not None:
            rows.append(summarise(ds, *got))
    if not rows:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_g2(rows))
    return out


__all__ = ["render_g2", "run_g2", "summarise"]
