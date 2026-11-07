"""Narrative page (week 14, A21/A22): abstention, H3b and strict grounding, top-3 typology
accuracy, latency, example cases, and the owner's blind review sheet."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any

from finmesh.attribution.claims import claim_check, reading
from finmesh.attribution.narrative import UNATTRIBUTED, template_narrative
from finmesh.reporting import fmt, table


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{100 * v:.1f}%"


def _example(title: str, r: dict[str, Any]) -> list[str]:
    checks = r["first"]
    keys = ["json", "typology", "cited", "numeric"]
    if "strict" in checks and r.get("protocol") in ("A22", "A23", "A25N"):
        keys += ["cites_ok", "mentions_ok"]
        if r.get("protocol") in ("A23", "A25N"):
            keys += ["consistent"]
        keys += ["strict"]
    flags = ", ".join(f"{k} {'yes' if checks.get(k) else 'no'}" for k in keys)
    cands = ", ".join(f"{c['id']} {c['confidence']:.2f}" for c in r["candidates"])
    return [
        f"### {title}",
        "",
        f"- Scheme {r['scheme_id']}: true pattern **{r['pattern']}**; shown to the analyst: "
        f"**{r['assigned']}** (top candidates: {cands}).",
        f"- First reply: {flags}; final text from **{r['final_source']}**; "
        f"{r['latency_total_s']:.1f} s.",
        f"- Cited fields: {', '.join(f'`{f}`' for f in checks['cited_fields']) or 'none'}.",
        "",
        f"> {r['narrative']}",
        "",
        "Review actions (from the catalogue, not the model):",
        "",
        *[f"1. {a}" for a in r["review_actions"]],
        "",
    ]


def _pick(cases: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    att = [c for c in cases if c["assigned"] != UNATTRIBUTED and c["final_source"] == "first"]
    good = [c for c in att if c["assigned"] == c["pattern"]]
    if good or att:
        out.append(("An attributed case", (good or att)[0]))
    una = [c for c in cases if c["assigned"] == UNATTRIBUTED]
    written = [c for c in una if c["final_source"] == "first"]
    if written or una:
        out.append(("An unattributed case written by the model", (written or una)[0]))
    used = {c["scheme_id"] for _, c in out}
    fixed = [c for c in cases if c["final_source"] != "first" and c["scheme_id"] not in used]
    if fixed:
        out.append(("A case whose first reply failed the check", fixed[0]))
    return out


def _cil(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def rescored_consistency(r: dict[str, Any]) -> float | None:
    """Share of delivered narratives the A23 claim check accepts (any protocol's run)."""
    cases = r.get("cases") or []
    if not cases:
        return None
    ok = [
        claim_check(c["narrative"], {e["field"]: e["value"] for e in c["evidence"]})["consistent"]
        for c in cases
    ]
    return float(sum(ok) / len(ok))


def _claim_section(r: dict[str, Any]) -> list[str]:
    s = r["summary"]
    fams = sorted(set(s["first_unsupported"]) | set(s["final_unsupported"]))
    return [
        "## Claim consistency (A23)",
        "",
        "Per-sentence rules tie the claims small models make most often to the evidence that "
        "would support them (pass-through, many payers or payees, cycles, gathering, splitting, "
        "layering); hedged sentences are skipped. Part of strict grounding in A23.",
        "",
        table(
            [
                {"item": "First replies claim-consistent", "value": _pct(s["first_consistent"])},
                {"item": "Delivered text claim-consistent", "value": _pct(s["final_consistent"])},
            ],
            [("item", "Item"), ("value", "Validation")],
        ),
        "",
        table(
            [
                {
                    "family": f,
                    "first": s["first_unsupported"].get(f, 0),
                    "final": s["final_unsupported"].get(f, 0),
                }
                for f in fams
            ]
            or [{"family": "none", "first": 0, "final": 0}],
            [
                ("family", "Unsupported claim"),
                ("first", "First replies"),
                ("final", "Delivered text"),
            ],
        ),
        "",
    ]


def _a22_sections(r: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    s = r["summary"]
    st = s["strict_grounding"]
    fs = s["first_reply_strict"]
    lines = [
        f"## Strict grounding ({r.get('protocol', 'A22')})",
        "",
        "Strict = H3b, plus 1 to 4 cited fields, every number in the narrative taken from the "
        "evidence or confidence lines, and no typology named outside the candidates"
        + (
            "; A23 adds claim consistency, number words and no copied placeholders"
            if r.get("protocol") in ("A23", "A25N")
            else ""
        )
        + ". The retry and the template are triggered by strict failure, so the analyst only "
        "sees strictly checked text.",
        "",
        table(
            [
                {"item": "Strictly grounded first replies [95% Wilson CI]", "value": _cil(st)},
                {"item": "First reply cites 1 to 4 fields", "value": _pct(fs["cites_ok"])},
                {"item": "First reply names no outside typology", "value": _pct(fs["mentions_ok"])},
                {
                    "item": "Replies that arrived (no timeout or error)",
                    "value": f"{s['answered']} of {s['cases']}",
                },
                {
                    "item": "H3b among replies that arrived",
                    "value": _pct(s["grounded_when_answered"]),
                },
                {
                    "item": "Strict among replies that arrived",
                    "value": _pct(s["strict_when_answered"]),
                },
                {
                    "item": "Delivered text names no outside typology",
                    "value": _pct(s["final_mentions_ok"]),
                },
            ],
            [("item", "Item"), ("value", "Validation")],
        ),
        "",
    ]
    if r.get("protocol") in ("A23", "A25N"):
        lines += _claim_section(r)
    if previous:
        ps = previous["summary"]
        prev_name = previous.get("protocol", "A21")
        this_name = r.get("protocol", "A22")
        rows = [
            ("H3b: grounded first replies", ps["H3b"]["grounding"]["estimate"],
             s["H3b"]["grounding"]["estimate"]),
            ("Valid JSON", ps["first_reply"]["json"], s["first_reply"]["json"]),
            ("Cited fields all real", ps["first_reply"]["cited"], s["first_reply"]["cited"]),
            ("Template fallback", ps["fallback_rate"], s["fallback_rate"]),
            ("Cases with a call error", ps["errors"] / max(ps["cases"], 1),
             s["errors"] / max(s["cases"], 1)),
            ("Delivered text claim-consistent (A23 rules)", rescored_consistency(previous),
             rescored_consistency(r)),
        ]  # fmt: skip
        if "strict_grounding" in ps:
            rows.insert(
                1,
                ("Strict grounding (rules of each run)",
                 ps["strict_grounding"]["estimate"], s["strict_grounding"]["estimate"]),
            )  # fmt: skip
        lines += [
            f"## {prev_name} → {this_name} on the same sample",
            "",
            table(
                [{"item": a, "prev": _pct(b), "this": _pct(c)} for a, b, c in rows],
                [("item", "Item"), ("prev", prev_name), ("this", this_name)],
            ),
            "",
        ]
    tk = r.get("topk")
    if tk:
        lv = tk["levels"]
        rows2 = []
        for name, label in (("S0", "S0 · own data only"), ("S2", "S2 · + shared evidence")):
            if name in lv:
                v = lv[name]
                rows2.append(
                    {
                        "level": label,
                        "top1": _cil(v["top1"]),
                        "top3": _cil(v["top3"]),
                        "top3d": _pct(v["top3_detected"]),
                    }
                )
        s2 = lv.get("S2", {})
        if s2.get("frequency_top3"):
            rows2.append(
                {
                    "level": "Baseline · 3 most frequent patterns",
                    "top1": "—",
                    "top3": _cil(s2["frequency_top3"]),
                    "top3d": _pct(s2["frequency_top3_detected"]),
                }
            )
            rows2.append(
                {
                    "level": "Baseline · chance",
                    "top1": "—",
                    "top3": "—",
                    "top3d": _pct(s2["chance_top3_detected"]),
                }
            )
        lines += [
            "## What the analyst sees: the top three candidates (secondary)",
            "",
            f"Cross-fitted attributor, seed 0, all {tk['schemes']} pattern-labelled validation "
            "schemes; end to end counts undetected schemes as misses; 1,000-replicate scheme "
            "bootstrap.",
            "",
            table(
                rows2,
                [
                    ("level", "Level"),
                    ("top1", "Top 1, end to end [95% CI]"),
                    ("top3", "Top 3, end to end [95% CI]"),
                    ("top3d", "Top 3, detected schemes"),
                ],
            ),
            "",
            table(
                [{"c": k, "v": _cil(v)} for k, v in tk["comparisons"].items()],
                [("c", "Comparison"), ("v", "Difference [95% CI]")],
            ),
            "",
        ]
    return lines


def _run_cost(r: dict[str, Any]) -> str:
    """Time and memory, for a validation run (the attributor runs here) or a test run (its
    tables come from `finmesh test-x1`, attributor fitted on validation)."""
    sec = r.get("seconds") or {}
    out = f"{sec.get('total', 0):,.0f} s in total"
    if sec.get("x6_s2") is not None:
        out += f" ({sec['x6_s2']:,.0f} s for the attributor)"
    elif r.get("split") == "test":
        out += " (attribution tables from `finmesh test-x1`, attributor fitted on validation)"
    if r.get("peak_anon_mb") is not None:
        out += f", peak memory {r['peak_anon_mb']:,.0f} MB"
    return out + "."


def render_narrative(r: dict[str, Any], previous: dict[str, Any] | None = None) -> str:
    s = r["summary"]
    sel = r["selective"]
    h = s["H3b"]
    g = h["grounding"]
    fr = s["first_reply"]
    lat = s["latency_s"]
    tau = sel["tau"]
    at_tau = next((row for row in sel["grid"] if row["tau"] == tau), None)
    grid = [
        {
            "tau": f"{row['tau']:.2f}" + (" ← τ" if row["tau"] == tau else ""),
            "coverage": _pct(row["coverage"]),
            "acc": _pct(row["selective_accuracy"]),
            "kept": row["kept"],
        }
        for row in sel["grid"]
    ]
    pattern_rows = [
        {
            "pattern": p,
            "cases": v["cases"],
            "attributed": v["attributed"],
            "correct": v["correct"],
            "grounded": _pct(v["grounded"]),
        }
        for p, v in s["by_pattern"].items()
    ]
    examples: list[str] = []
    for title, case in _pick(r["cases"]):
        examples += _example(title, case)
    return "\n".join(
        [
            f"# Constrained case narrative (H3b) · {r['dataset']}"
            + (
                f" · protocol {r.get('protocol')}"
                if r.get("protocol") in ("A22", "A23", "A25N")
                else ""
            ),
            "",
            f"Level S2, seed {r['seed']}; {s['cases']} detected "
            f"{'test' if r.get('split') == 'test' else 'validation'} schemes sampled by "
            f"pattern (up to 25 each). Model `{r['model']}` on this machine, temperature 0; "
            f"{r['decoding']} ({r.get('protocol', 'A21')}). The model writes the text only: "
            "the typology comes from the "
            "X6 attributor (shown only above τ), the evidence from a fixed template of what S2 "
            "reveals to the owner, and the review actions from the catalogue. " + _run_cost(r),
            "",
            "## H3b on validation",
            "",
            table(
                [
                    {
                        "item": "Grounded first replies [95% Wilson CI]",
                        "value": "—"
                        if g["estimate"] is None
                        else f"{fmt(g['estimate'])} [{fmt(g['low'])}, {fmt(g['high'])}]",
                    },
                    {"item": "Target", "value": fmt(h["target"])},
                    {"item": "Met on validation", "value": fmt(h["met_on_validation"])},
                ],
                [("item", "Item"), ("value", "Validation")],
            ),
            "",
            "Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every "
            "cited field present in the evidence. Judged on test.",
            "",
            *(_a22_sections(r, previous) if r.get("protocol") in ("A22", "A23", "A25N") else []),
            "## Reply quality and latency",
            "",
            table(
                [
                    {"item": "First reply: valid JSON", "value": _pct(fr["json"])},
                    {"item": "First reply: typology as shown", "value": _pct(fr["typology"])},
                    {"item": "First reply: cited fields all real", "value": _pct(fr["cited"])},
                    {
                        "item": "First reply: cites at least one field",
                        "value": _pct(fr["cites_any"]),
                    },
                    {
                        "item": "First reply: every number appears in the prompt",
                        "value": _pct(fr["numeric"]),
                    },
                    {"item": "Retried (schema-constrained)", "value": _pct(s["retry_rate"])},
                    {"item": "Retry grounded", "value": _pct(s["retry_grounded"])},
                    {"item": "Template fallback", "value": _pct(s["fallback_rate"])},
                    {
                        "item": "Final text: numbers all from the prompt",
                        "value": _pct(s["final_numeric"]),
                    },
                    {"item": "Cases with a call error", "value": fmt(s["errors"])},
                    {
                        "item": "Latency per case, p50 / p95 / max",
                        "value": "—"
                        if lat["p50"] is None
                        else f"{lat['p50']:.1f} / {lat['p95']:.1f} / {lat['max']:.1f} s "
                        f"(target p95 ≤ {lat['target_p95']:.0f} s)",
                    },
                ],
                [("item", "Item"), ("value", "Value")],
            ),
            "",
            "## Abstention: when the attributor's label is shown",
            "",
            f"τ = **{'none' if tau is None else f'{tau:.2f}'}**: the smallest threshold whose "
            "selective accuracy on all detected validation schemes is at least 50% with coverage "
            f"at least 10% ({sel['detected_schemes']:,} detected of {sel['schemes']:,} schemes; "
            f"attributor accuracy without abstention {_pct(sel['accuracy_detected'])}). "
            + (
                f"At τ, {_pct(at_tau['coverage'])} of cases get a label, "
                f"{_pct(at_tau['selective_accuracy'])} of them correct."
                if at_tau
                else "No threshold qualifies: every case is UNATTRIBUTED with its top three "
                "candidates."
            ),
            "",
            table(
                grid,
                [
                    ("tau", "τ"),
                    ("coverage", "Coverage"),
                    ("acc", "Selective accuracy"),
                    ("kept", "Schemes labelled"),
                ],
            ),
            "",
            "## In the sample",
            "",
            f"- Labelled cases: {s['attributed']['cases']}, correct "
            f"{_pct(s['attributed']['accuracy'])}.",
            f"- Unattributed cases: {s['unattributed']['cases']}; the true pattern is among the "
            f"three candidates listed in {_pct(s['unattributed']['top3_contains_truth'])}.",
            "",
            table(
                pattern_rows,
                [
                    ("pattern", "Pattern"),
                    ("cases", "Cases"),
                    ("attributed", "Labelled"),
                    ("correct", "Labelled correctly"),
                    ("grounded", "Grounded first replies"),
                ],
            ),
            "",
            "## Example cases",
            "",
            *(examples or ["No cases."]),
            f"Every case (prompt size, raw replies, checks, final text) is in "
            f"`narrative_{r['dataset']}{_suffix(r)}_cases.jsonl`.",
            "",
        ]
    )


def _suffix(r: dict[str, Any]) -> str:
    p = r.get("protocol", "A21")
    return "" if p == "A21" else f"_{p}"


REVIEW_N = 30
REVIEW_SEED = 0


def write_review(r: dict[str, Any], path: Path, n: int = REVIEW_N) -> Path:
    """The owner's blind review sheet (A22): random cases, no true pattern, blank ratings."""
    cases = list(r["cases"])
    picked = random.Random(REVIEW_SEED).sample(cases, min(n, len(cases)))
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "case",
                "evidence",
                "candidates",
                "narrative",
                "faithful (yes/partly/no)",
                "useful (1-3)",
                "notes",
            ]
        )
        for i, c in enumerate(picked, 1):
            ev = "; ".join(
                f"{e['field']} = {e['value']}"
                for e in c["evidence"]
                if e["value"] not in ("not available", "no record from another member")
            )
            cands = ", ".join(f"{x['id']} {x['confidence']:.2f}" for x in c["candidates"])
            w.writerow([i, ev, cands, c["narrative"], "", "", ""])
    return path


AB_COLUMNS = [
    "case",
    "evidence",
    "candidates",
    "narrative A",
    "narrative B",
    "faithful A (yes/partly/no)",
    "useful A (1-3)",
    "faithful B (yes/partly/no)",
    "useful B (1-3)",
    "prefer (A/B/same)",
    "notes",
]


def write_review_ab(r: dict[str, Any], path: Path, key: Path, n: int = REVIEW_N) -> Path:
    """A23 blind review: the delivered narrative and the template, in seeded random order.
    The key (which is which, and the claim check's verdict) goes to a separate file."""
    rng = random.Random(REVIEW_SEED)
    picked = rng.sample(list(r["cases"]), min(n, len(r["cases"])))
    with path.open("w", newline="") as f, key.open("w", newline="") as k:
        w, wk = csv.writer(f), csv.writer(k)
        w.writerow(AB_COLUMNS)
        wk.writerow(["case", "scheme_id", "A", "B", "model_source", "model_claim_consistent"])
        for i, c in enumerate(picked, 1):
            model = c["narrative"]
            tmpl = template_narrative(c, "A23")
            order = ["model", "template"]
            rng.shuffle(order)
            texts = {"model": model, "template": tmpl}
            ev = "; ".join(
                f"{e['field']} = {e['value']}"
                + (
                    f" ({reading(e['field'], e['value'])})"
                    if reading(e["field"], e["value"])
                    else ""
                )
                for e in c["evidence"]
                if e["value"] not in ("not available", "no record from another member")
            )
            cands = ", ".join(f"{x['id']} {x['confidence']:.2f}" for x in c["candidates"])
            w.writerow([i, ev, cands, texts[order[0]], texts[order[1]], "", "", "", "", "", ""])
            consistent = claim_check(model, {e["field"]: e["value"] for e in c["evidence"]})
            wk.writerow(
                [i, c["scheme_id"], order[0], order[1], c["final_source"], consistent["consistent"]]
            )
    return path


def _kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def score_review(rated: Path, key: Path) -> dict[str, Any]:
    """Faithfulness, usefulness and preference per source, and the claim check's agreement
    with the owner's faithful = yes on the model narratives (Cohen's kappa)."""
    with rated.open(newline="") as f:
        rows = {int(x["case"]): x for x in csv.DictReader(f)}
    with key.open(newline="") as f:
        keys = {int(x["case"]): x for x in csv.DictReader(f)}
    per: dict[str, dict[str, list[Any]]] = {
        s: {"faithful": [], "useful": []} for s in ("model", "template")
    }
    prefer = {"model": 0, "template": 0, "same": 0}
    checker, human = [], []
    rated_n = 0
    for case, k in keys.items():
        row = rows.get(case)
        if not row:
            continue
        cells = {
            side: (
                row[f"faithful {side} (yes/partly/no)"].strip().lower(),
                row[f"useful {side} (1-3)"].strip(),
            )
            for side in ("A", "B")
        }
        if not all(fa and us for fa, us in cells.values()):
            continue
        rated_n += 1
        for side in ("A", "B"):
            src = k[side]
            fa, us = cells[side]
            per[src]["faithful"].append(fa)
            per[src]["useful"].append(float(us))
            if src == "model":
                human.append(fa == "yes")
                checker.append(k["model_claim_consistent"].strip().lower() == "true")
        p = row["prefer (A/B/same)"].strip().upper()
        if p in ("A", "B"):
            prefer[k[p]] += 1
        elif p:
            prefer["same"] += 1
    out: dict[str, Any] = {"rated": rated_n, "prefer": prefer, "sources": {}}
    for src, v in per.items():
        n = len(v["faithful"])
        out["sources"][src] = {
            "faithful_yes": (v["faithful"].count("yes") / n) if n else None,
            "faithful_partly": (v["faithful"].count("partly") / n) if n else None,
            "faithful_no": (v["faithful"].count("no") / n) if n else None,
            "useful_mean": (sum(v["useful"]) / n) if n else None,
        }
    agree = sum(a == b for a, b in zip(checker, human, strict=True))
    out["checker"] = {
        "agreement": (agree / len(human)) if human else None,
        "kappa": _kappa(checker, human),
        "checker_consistent": sum(checker),
        "human_faithful": sum(human),
    }
    return out


FAITHFUL = ("no", "partly", "yes")  # ordered
USEFUL = ("1", "2", "3")
PREFER = ("model", "same", "template")


def cohen_kappa(
    a: list[str], b: list[str], categories: tuple[str, ...], weights: str | None = None
) -> float | None:
    """Cohen's kappa between two raters; ``weights`` "linear" for ordered categories."""
    n = len(a)
    if not n:
        return None
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        obs[idx[x]][idx[y]] += 1 / n
    ra = [sum(row) for row in obs]
    rb = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i: int, j: int) -> float:
        if weights == "linear":
            return abs(i - j) / (k - 1)
        return 0.0 if i == j else 1.0

    do = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    de = sum(w(i, j) * ra[i] * rb[j] for i in range(k) for j in range(k))
    return None if de == 0 else 1 - do / de


def _ratings(rated: Path, key: Path) -> dict[tuple[int, str], dict[str, str]]:
    """(case, source) -> faithful, useful, prefer (as a source), for fully rated cases."""
    with rated.open(newline="") as f:
        rows = {int(x["case"]): x for x in csv.DictReader(f)}
    with key.open(newline="") as f:
        keys = {int(x["case"]): x for x in csv.DictReader(f)}
    out: dict[tuple[int, str], dict[str, str]] = {}
    for case, k in keys.items():
        row = rows.get(case)
        if not row:
            continue
        cells = {
            side: (
                row[f"faithful {side} (yes/partly/no)"].strip().lower(),
                row[f"useful {side} (1-3)"].strip(),
            )
            for side in ("A", "B")
        }
        if not all(fa in FAITHFUL and us in USEFUL for fa, us in cells.values()):
            continue
        p = row["prefer (A/B/same)"].strip().upper()
        pref = k[p] if p in ("A", "B") else ("same" if p else "")
        for side in ("A", "B"):
            out[(case, k[side])] = {
                "faithful": cells[side][0],
                "useful": cells[side][1],
                "prefer": pref,
                "checker": k["model_claim_consistent"].strip().lower(),
            }
    return out


def score_two_raters(sheets: dict[str, Path], key: Path) -> dict[str, Any]:
    """Each rater scored alone (:func:`score_review`), their agreement (Cohen's kappa:
    linear-weighted for faithfulness and usefulness, unweighted for preference), and the
    claim check against their consensus (model narratives both rate faithful = yes)."""
    names = sorted(sheets)
    per = {n: score_review(sheets[n], key) for n in names}
    out: dict[str, Any] = {"raters": names, "per_rater": per}
    if len(names) != 2:
        return out
    ra, rb = (_ratings(sheets[n], key) for n in names)
    both = sorted(set(ra) & set(rb))
    fa = [ra[i]["faithful"] for i in both], [rb[i]["faithful"] for i in both]
    us = [ra[i]["useful"] for i in both], [rb[i]["useful"] for i in both]
    cases = sorted({c for c, src in both if src == "model"})
    pa = [ra[(c, "model")]["prefer"] for c in cases]
    pb = [rb[(c, "model")]["prefer"] for c in cases]
    pref = [(x, y) for x, y in zip(pa, pb, strict=True) if x and y]
    model = [i for i in both if i[1] == "model"]
    consensus = [ra[i]["faithful"] == "yes" and rb[i]["faithful"] == "yes" for i in model]
    checker = [ra[i]["checker"] == "true" for i in model]
    out["agreement"] = {
        "cases": len(cases),
        "faithful_exact": (sum(x == y for x, y in zip(*fa, strict=True)) / len(both))
        if both
        else None,
        "faithful_kappa": cohen_kappa(fa[0], fa[1], FAITHFUL, "linear"),
        "useful_kappa": cohen_kappa(us[0], us[1], USEFUL, "linear"),
        "prefer_kappa": cohen_kappa([x for x, _ in pref], [y for _, y in pref], PREFER),
    }
    out["checker_vs_consensus"] = {
        "agreement": (sum(a == b for a, b in zip(checker, consensus, strict=True)) / len(model))
        if model
        else None,
        "kappa": _kappa(checker, consensus),
        "consensus_faithful": sum(consensus),
        "checker_consistent": sum(checker),
    }
    return out


def render_two_raters(s: dict[str, Any], dataset: str) -> str:
    def f(v: float | None, pct: bool = True) -> str:
        if v is None:
            return "—"
        return f"{100 * v:.0f}%" if pct else f"{v:.2f}"

    rows = []
    for name in s["raters"]:
        r = s["per_rater"][name]
        for key, label in (("model", "model"), ("template", "template")):
            v = r["sources"][key]
            rows.append(
                {
                    "rater": name,
                    "source": label,
                    "n": r["rated"],
                    "yes": f(v["faithful_yes"]),
                    "partly": f(v["faithful_partly"]),
                    "no": f(v["faithful_no"]),
                    "useful": f(v["useful_mean"], pct=False),
                    "prefer": r["prefer"][key],
                }
            )
    out = [
        f"# Blind review of the narratives (A23), two raters · {dataset}",
        "",
        "Each rater filled a separate copy of the same sheet, blind to which text is the "
        "model's and which is the template, to the true pattern, and to the other rater.",
        "",
        table(
            rows,
            [
                ("rater", "Rater"),
                ("source", "Narrative"),
                ("n", "Cases"),
                ("yes", "Faithful: yes"),
                ("partly", "Partly"),
                ("no", "No"),
                ("useful", "Useful (1-3)"),
                ("prefer", "Preferred"),
            ],
        ),
        "",
    ]
    ag = s.get("agreement")
    if ag:
        ck = s["checker_vs_consensus"]
        out += [
            "## Agreement between the raters",
            "",
            f"{ag['cases']} cases rated by both. Faithfulness: exact agreement "
            f"{f(ag['faithful_exact'])}, linear-weighted kappa {f(ag['faithful_kappa'], False)}; "
            f"usefulness: linear-weighted kappa {f(ag['useful_kappa'], False)}; preference: kappa "
            f"{f(ag['prefer_kappa'], False)}. Kappa above 0.6 is usually read as substantial, "
            "0.4–0.6 moderate.",
            "",
            "## The claim check against both raters",
            "",
            f"Model narratives the check accepts versus those both raters call faithful: "
            f"agreement {f(ck['agreement'])}, Cohen's kappa {f(ck['kappa'], False)} "
            f"(check accepted {ck['checker_consistent']}, both raters faithful "
            f"{ck['consensus_faithful']}).",
            "",
        ]
    return "\n".join(out)


def prepare_rater_sheets(master: Path, raters: list[str]) -> list[Path]:
    """One blank copy of the review sheet per rater (an existing copy is never replaced)."""
    out = []
    for name in raters:
        copy = master.with_name(master.stem + f"_{name}.csv")
        if not copy.exists():
            copy.write_bytes(master.read_bytes())
        out.append(copy)
    return out


def render_review(s: dict[str, Any], dataset: str) -> str:
    src = s["sources"]

    def f(v: float | None, pct: bool = True) -> str:
        if v is None:
            return "—"
        return f"{100 * v:.0f}%" if pct else f"{v:.2f}"

    ck = s["checker"]
    return "\n".join(
        [
            f"# Blind review of the narratives (A23) · {dataset}",
            "",
            f"{s['rated']} cases rated by the owner, blind to which text is the model's and which "
            "is the template, and to the true pattern.",
            "",
            table(
                [
                    {
                        "source": name,
                        "yes": f(src[key]["faithful_yes"]),
                        "partly": f(src[key]["faithful_partly"]),
                        "no": f(src[key]["faithful_no"]),
                        "useful": f(src[key]["useful_mean"], pct=False),
                    }
                    for key, name in (("model", "Model (llama3.2:3b)"), ("template", "Template"))
                ],
                [
                    ("source", "Narrative"),
                    ("yes", "Faithful: yes"),
                    ("partly", "Partly"),
                    ("no", "No"),
                    ("useful", "Useful (mean, 1-3)"),
                ],
            ),
            "",
            f"Preferred: model {s['prefer']['model']}, template {s['prefer']['template']}, "
            f"same {s['prefer']['same']}.",
            "",
            f"Claim check against the owner (model narratives): agreement {f(ck['agreement'])}, "
            f"Cohen's kappa {f(ck['kappa'], pct=False)} "
            f"(check accepted {ck['checker_consistent']}, "
            f"owner rated faithful {ck['human_faithful']}).",
            "",
        ]
    )


def write_cases(r: dict[str, Any], path: Path) -> Path:
    """One compact JSON line per case, for review and for the paper's examples."""
    keep = (
        "scheme_id",
        "pattern",
        "assigned",
        "confidence",
        "candidates",
        "final_source",
        "narrative",
        "review_actions",
        "latency_total_s",
        "prompt_chars",
        "errors",
    )
    with path.open("w") as f:
        for c in r["cases"]:
            row = {k: c[k] for k in keep}
            row["evidence"] = {e["field"]: e["value"] for e in c["evidence"]}
            row["first"] = {k: v for k, v in c["first"].items() if k != "narrative"}
            row["retry_raw"] = c["retry"]["raw"] if c["retry"] else None
            f.write(json.dumps(row) + "\n")
    return path


__all__ = [
    "cohen_kappa",
    "prepare_rater_sheets",
    "render_narrative",
    "render_review",
    "render_two_raters",
    "rescored_consistency",
    "score_review",
    "score_two_raters",
    "write_cases",
    "write_review",
    "write_review_ab",
]
