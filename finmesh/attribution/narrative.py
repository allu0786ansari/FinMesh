"""Constrained case narrative and its grounding test (week 14; amendment A21; H3b).

For a detected case at level S2, the incident's owner gets a short narrative
written by a local language model (llama3.2:3b through Ollama on this machine,
threat ADV-6). The model never decides anything:

* the **typology** comes from the X6 attributor, and only when its cross-fitted
  confidence reaches τ (selective classification, Geifman and El-Yaniv 2017);
  below τ the case is ``UNATTRIBUTED`` and the top three candidates are listed;
* the **evidence** is rendered by a fixed template from what S2 reveals to the
  owner (own features, cross-bank structure, other members' record counters as
  bucket ranges); the model may cite only these fields;
* the **review actions** come from the catalogue entry, never from the model.

Each case gets one JSON-only call (temperature 0, A7). A reply that fails the
structural check gets one schema-constrained retry, then a template narrative.

**H3b grounding** is measured on the raw first replies: valid JSON, typology
equal to the assigned one (or UNATTRIBUTED), cited fields all in the evidence;
target 0.95. Numeric grounding (every number in the narrative appears in the
prompt), retry and fallback rates and latency (target p95 ≤ 30 s) are reported
alongside.
"""

from __future__ import annotations

import json
import re
import statistics
import time
import urllib.error
from collections.abc import Callable
from typing import Any

import numpy as np
import polars as pl

from finmesh.attribution.llm_probe import DEFAULT_MODEL, assert_local, call_ollama
from finmesh.sharing.evidence import load_evidence_schema

UNATTRIBUTED = "UNATTRIBUTED"
TAU_GRID: tuple[float, ...] = tuple(round(0.30 + 0.05 * i, 2) for i in range(14))  # 0.30-0.95
MIN_SELECTIVE_ACCURACY = 0.5
MIN_COVERAGE = 0.10
SAMPLE_N = 200
PER_PATTERN = 25
SAMPLE_SEED = 0
LATENCY_TARGET_S = 30.0
GROUNDING_TARGET = 0.95
NARRATIVE_MAX_CHARS = 900
MAX_TOKENS = 320  # bounds a runaway reply; a cut-off reply fails the check and is retried

# A model call: (prompt, format) -> raw response text. Raises on transport failure.
Call = Callable[[str, dict[str, Any] | str], str]

# (field, description shown to the model, source column(s), kind)
OWN_FIELDS: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("own_accounts", "case accounts at your bank", ("own_accounts",), "int"),
    ("own_account_windows", "alerted account-windows at your bank", ("own_rows",), "int"),
    ("own_span_hours", "hours spanned at your bank", ("own_span",), "hours"),
    (
        "own_max_fan_out",
        "max distinct payees of one account",
        ("own_max_fan_out",),
        "int",
    ),
    ("own_max_fan_in", "max distinct payers of one account", ("own_max_fan_in",), "int"),
    (
        "own_mean_pass_through",
        "mean share of inflow paid out again",
        ("own_mean_pass_through",),
        "share",
    ),
    (
        "own_max_cycles",
        "max short cycles through one account",
        ("own_max_cyc2", "own_max_cyc3", "own_max_cyc4"),
        "int",
    ),
    (
        "own_max_gather_scatter",
        "max gather-then-scatter fan",
        ("own_max_gs_min_fan",),
        "int",
    ),
    (
        "own_max_scatter_gather",
        "max scatter-then-gather fan",
        ("own_max_sg_out_max", "own_max_sg_in_max"),
        "int",
    ),
    (
        "own_max_amount_out",
        "max amount paid out by one account in a window",
        ("own_max_amt_out",),
        "amount",
    ),
    (
        "own_max_amount_in",
        "max amount received by one account in a window",
        ("own_max_amt_in",),
        "amount",
    ),
    (
        "own_mean_cross_bank_share",
        "mean share of transfers with other banks",
        ("own_mean_cross_bank_share",),
        "share",
    ),
    (
        "own_mean_new_counterparty_share",
        "mean share of new counterparties",
        ("own_mean_new_cp_share",),
        "share",
    ),
)
CASE_FIELDS: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("case_accounts", "accounts in the linked case", ("n_accounts",), "int"),
    ("case_members", "federation members in the case", ("n_members",), "int"),
    ("case_account_windows", "alerted account-windows in the case", ("n_rows",), "int"),
    ("case_span_hours", "hours spanned by the case", ("span",), "hours"),
)
RECORD_LABELS = {
    "fan_out": "distinct payees",
    "fan_in": "distinct payers",
    "tx_out": "outgoing transfers",
    "tx_in": "incoming transfers",
    "amt_out": "amount paid out",
    "amt_in": "amount received",
    "pass_through": "share of incoming money paid out again",
    "cross_bank_share": "share of transfers with other banks",
    "new_cp_share": "share of new counterparties",
    "delay_min_h": "min hours from money in to money out",
}


# --------------------------------------------------------------------------- abstention
def risk_coverage(confidence: np.ndarray, correct: np.ndarray) -> list[dict[str, Any]]:
    """Selective accuracy and coverage at each τ in the grid (detected schemes only)."""
    n = len(confidence)
    rows = []
    for tau in TAU_GRID:
        keep = confidence >= tau
        rows.append(
            {
                "tau": tau,
                "coverage": float(keep.mean()) if n else 0.0,
                "selective_accuracy": float(correct[keep].mean()) if keep.any() else None,
                "kept": int(keep.sum()),
            }
        )
    return rows


def selective_threshold(confidence: np.ndarray, correct: np.ndarray) -> float | None:
    """The smallest τ with selective accuracy ≥ 0.5 and coverage ≥ 10%; None if none."""
    for r in risk_coverage(confidence, correct):
        acc = r["selective_accuracy"]
        if acc is not None and acc >= MIN_SELECTIVE_ACCURACY and r["coverage"] >= MIN_COVERAGE:
            return float(r["tau"])
    return None


# --------------------------------------------------------------------------- sample
def stratified_sample(
    scheme_ids: np.ndarray,
    patterns: np.ndarray,
    n: int = SAMPLE_N,
    per_pattern: int = PER_PATTERN,
    seed: int = SAMPLE_SEED,
) -> np.ndarray:
    """Indices: up to ``per_pattern`` per pattern at random, then filled at random to ``n``."""
    rng = np.random.default_rng(seed)
    order = np.argsort(scheme_ids, kind="stable")
    kinds = sorted(set(patterns.tolist()))
    # A smaller n shrinks the cap evenly, so no pattern is crowded out (n = 200: 25 each).
    cap = min(per_pattern, max(1, n // max(len(kinds), 1)))
    chosen: list[int] = []
    for p in kinds:
        idx = order[patterns[order] == p]
        chosen += rng.permutation(idx)[:cap].tolist()
    chosen = chosen[:n]
    rest = np.setdiff1d(order, np.array(chosen, dtype=np.int64))
    chosen += rng.permutation(rest)[: max(0, n - len(chosen))].tolist()
    return np.array(sorted(chosen, key=lambda i: scheme_ids[i]), dtype=np.int64)


# --------------------------------------------------------------------------- evidence
def _num(v: float, kind: str, window_hours: int) -> str:
    if kind == "hours":
        return f"{round(v * window_hours):,}"
    if kind == "share":
        return f"{v:.2f}"
    if kind == "amount":
        return f"{v:,.0f}"
    return f"{round(v):,}"


def _value(row: dict[str, Any], cols: tuple[str, ...]) -> float | None:
    vals = [float(v) for v in (row.get(c) for c in cols) if v is not None]
    vals = [v for v in vals if not np.isnan(v)]
    return max(vals) if vals else None


def bucket_range(index: float | None, edges: tuple[float, ...]) -> str:
    """Human range of an evidence bucket (see ``finmesh.sharing.evidence.bucket``)."""
    if index is None or np.isnan(index):
        return "no record from another member"
    i = round(index)

    def e(x: float) -> str:
        return f"{x:,.0f}" if float(x).is_integer() else f"{x:g}"

    if i == 0:
        return f"below {e(edges[0])}"
    if i < len(edges):
        return f"at least {e(edges[i - 1])}, below {e(edges[i])}"
    if i == len(edges):
        return f"{e(edges[-1])} or more"
    return "not reported"


def evidence(row: dict[str, Any], window_hours: int) -> list[dict[str, str]]:
    """The fixed evidence template: what S2 reveals to the incident's owner."""
    out = []
    for section, fields in (("Your bank", OWN_FIELDS), ("Linked case", CASE_FIELDS)):
        for field, label, cols, kind in fields:
            v = _value(row, cols)
            out.append(
                {
                    "section": section,
                    "field": field,
                    "label": label,
                    "value": "not available" if v is None else _num(v, kind, window_hours),
                }
            )
    for name, _, edges in load_evidence_schema().counters:
        out.append(
            {
                "section": "Other members' records (highest bucket)",
                "field": f"others_{name}",
                "label": RECORD_LABELS.get(name, name.replace("_", " ")),
                "value": bucket_range(_value(row, (f"rec_max_c_{name}",)), edges),
            }
        )
    return out


# --------------------------------------------------------------------------- prompt
def _entry_text(entry: dict[str, Any]) -> str:
    flags = "; ".join(entry["red_flags"])
    return f"- {entry['id']} ({entry['name']}): {entry['description']} Red flags: {flags}."


MISSING = ("not available", "no record from another member")


def shown(case: dict[str, Any]) -> list[dict[str, str]]:
    """Evidence lines in the prompt: only fields with a value (shorter, nothing to misread)."""
    return [e for e in case["evidence"] if e["value"] not in MISSING]


def build_prompt(case: dict[str, Any], catalogue: dict[str, Any]) -> str:
    entries = {e["id"]: e for e in catalogue["entries"]}
    if case["assigned"] == UNATTRIBUTED:
        decision = (
            f'The case is UNATTRIBUTED: the attributor is not confident enough. Set "typology_id" '
            f'to "{UNATTRIBUTED}". You may mention the candidate typologies only as possibilities '
            "to check, never as a finding."
        )
        context = [_entry_text(entries[c["id"]]) for c in case["candidates"]]
        conf = "Candidate typologies (attributor confidence): " + ", ".join(
            f"{c['id']} ({c['confidence']:.2f})" for c in case["candidates"]
        )
    else:
        decision = (
            f'The typology is already decided: set "typology_id" to "{case["assigned"]}". '
            "Do not argue for another typology."
        )
        context = [_entry_text(entries[case["assigned"]])]
        conf = f"Attributor confidence: {case['confidence']:.2f}"
    lines = []
    section = None
    for ev in shown(case):
        if ev["section"] != section:
            section = ev["section"]
            lines.append(f"{section}:")
        lines.append(f"- [{ev['field']}] {ev['label']}: {ev['value']}")
    return "\n".join(
        [
            "You help an anti-money-laundering analyst write a short case summary.",
            "Rules:",
            "- Use only the evidence below. Do not invent names, accounts, dates or amounts.",
            "- Copy numbers exactly as written in the evidence. Do not calculate new numbers.",
            f"- {decision}",
            '- "cited_fields": the evidence field names (in square brackets) that your '
            "narrative relies on.",
            '- "narrative": two to four plain sentences for the analyst.',
            "- Do not recommend actions; they are added separately.",
            'Reply with one JSON object with exactly the keys "typology_id", "cited_fields" '
            'and "narrative".',
            "",
            "Typology context:",
            *context,
            conf,
            "",
            "Evidence:",
            *lines,
        ]
    )


def reply_schema(expected: str, fields: list[str]) -> dict[str, Any]:
    """The schema for the constrained retry: only the assigned typology, only real fields."""
    return {
        "type": "object",
        "properties": {
            "typology_id": {"type": "string", "enum": [expected]},
            "cited_fields": {"type": "array", "items": {"type": "string", "enum": fields}},
            "narrative": {"type": "string", "maxLength": NARRATIVE_MAX_CHARS},
        },
        "required": ["typology_id", "cited_fields", "narrative"],
        "additionalProperties": False,
    }


# --------------------------------------------------------------------------- checks
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")


def numbers_in(text: str) -> set[float]:
    return {round(float(m.replace(",", "")), 6) for m in _NUMBER.findall(text)}


def check_reply(
    text: str, expected: str, fields: list[str], prompt_numbers: set[float]
) -> dict[str, Any]:
    """H3b checks on one raw reply, before any repair."""
    out: dict[str, Any] = {
        "json": False,
        "typology": False,
        "cited": False,
        "grounded": False,
        "numeric": False,
        "cites_any": False,
        "narrative": None,
        "cited_fields": [],
    }
    try:
        reply = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return out
    if not isinstance(reply, dict):
        return out
    out["json"] = True
    narrative = reply.get("narrative")
    cited = reply.get("cited_fields")
    out["typology"] = reply.get("typology_id") == expected
    out["cited"] = isinstance(cited, list) and all(
        isinstance(f, str) and f in fields for f in cited
    )
    ok_text = isinstance(narrative, str) and bool(narrative.strip())
    out["grounded"] = bool(out["typology"] and out["cited"] and ok_text)
    if isinstance(narrative, str) and ok_text:
        out["narrative"] = narrative.strip()
        out["numeric"] = numbers_in(narrative) <= prompt_numbers
    if isinstance(cited, list):
        out["cited_fields"] = [str(f) for f in cited]
        out["cites_any"] = bool(cited)
    return out


def template_narrative(case: dict[str, Any]) -> str:
    """Deterministic fallback, built only from the evidence values (grounded by construction)."""
    ev = {e["field"]: e["value"] for e in case["evidence"]}
    if case["assigned"] == UNATTRIBUTED:
        what = "The pattern is unattributed; candidates to check: " + ", ".join(
            c["id"] for c in case["candidates"]
        )
    else:
        what = f"Assigned typology: {case['assigned']}"
    return (
        f"{ev['case_accounts']} accounts at {ev['case_members']} federation members are linked "
        f"in this case over {ev['case_span_hours']} hours; {ev['own_accounts']} of them are at "
        f"your bank. {what}. Largest fan-out at your bank: {ev['own_max_fan_out']}; largest "
        f"fan-in: {ev['own_max_fan_in']}; average pass-through: {ev['own_mean_pass_through']}."
    )


# --------------------------------------------------------------------------- cases
def build_case(
    row: dict[str, Any],
    classes: list[str],
    proba: np.ndarray,
    tau: float | None,
    catalogue: dict[str, Any],
    window_hours: int,
) -> dict[str, Any]:
    order = np.argsort(-proba, kind="stable")
    top = [{"id": classes[i], "confidence": float(proba[i])} for i in order[:3]]
    confidence = float(proba[order[0]])
    attributed = tau is not None and confidence >= tau
    assigned = classes[order[0]] if attributed else UNATTRIBUTED
    entries = {e["id"]: e for e in catalogue["entries"]}
    actions = (
        list(entries[assigned]["review_actions"])
        if attributed
        else [entries[c["id"]]["review_actions"][0] for c in top]
    )
    return {
        "scheme_id": int(row["scheme_id"]),
        "pattern": row["pattern"],
        "assigned": assigned,
        "top_prediction": classes[order[0]],
        "confidence": confidence,
        "candidates": top,
        "evidence": evidence(row, window_hours),
        "review_actions": actions,
    }


def narrate(case: dict[str, Any], catalogue: dict[str, Any], call: Call) -> dict[str, Any]:
    """One case: JSON-only call, one schema-constrained retry if needed, else the template."""
    prompt = build_prompt(case, catalogue)
    fields = [e["field"] for e in shown(case)]
    expected = case["assigned"]
    known = numbers_in(prompt)
    t0 = time.perf_counter()
    errors: list[str] = []

    def attempt(fmt: dict[str, Any] | str, text: str) -> dict[str, Any]:
        try:
            raw = call(text, fmt)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}"[:200])
            raw = ""
        return {"raw": raw, **check_reply(raw, expected, fields, known)}

    first = attempt("json", prompt)
    first_s = time.perf_counter() - t0
    retry = None
    final_source = "first"
    final = first
    if not first["grounded"]:
        retry = attempt(
            reply_schema(expected, fields),
            prompt + "\n\nYour previous reply did not follow the rules. Reply with the JSON "
            "object only.",
        )
        final, final_source = retry, "retry"
        if not retry["grounded"]:
            final_source = "template"
    narrative = template_narrative(case) if final_source == "template" else final["narrative"]
    return {
        **case,
        "prompt_chars": len(prompt),
        "first": first,
        "retry": retry,
        "final_source": final_source,
        "narrative": narrative,
        "final_numeric": numbers_in(narrative) <= known,
        "latency_first_s": round(first_s, 3),
        "latency_total_s": round(time.perf_counter() - t0, 3),
        "errors": errors,
    }


def ollama_call(url: str, model: str, timeout: float) -> Call:
    assert_local(url)

    def call(prompt: str, fmt: dict[str, Any] | str) -> str:
        reply = call_ollama(url, model, prompt, fmt, timeout, max_tokens=MAX_TOKENS)
        return str(reply.get("response", ""))

    return call


# --------------------------------------------------------------------------- summary
def _rate(xs: list[bool]) -> float | None:
    return float(np.mean(xs)) if xs else None


def _wilson(k: int, n: int) -> dict[str, float | None]:
    if not n:
        return {"estimate": None, "low": None, "high": None}
    z, p = 1.959964, k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"estimate": p, "low": float(centre - half), "high": float(centre + half)}


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(results)
    grounded = [r["first"]["grounded"] for r in results]
    lat = sorted(r["latency_total_s"] for r in results)
    attributed = [r for r in results if r["assigned"] != UNATTRIBUTED]
    unattributed = [r for r in results if r["assigned"] == UNATTRIBUTED]
    by_pattern: dict[str, dict[str, Any]] = {}
    for p in sorted({r["pattern"] for r in results}):
        rs = [r for r in results if r["pattern"] == p]
        by_pattern[p] = {
            "cases": len(rs),
            "attributed": sum(r["assigned"] != UNATTRIBUTED for r in rs),
            "correct": sum(r["assigned"] == p for r in rs),
            "grounded": _rate([r["first"]["grounded"] for r in rs]),
        }
    return {
        "cases": n,
        "H3b": {
            "grounding": _wilson(sum(grounded), n),
            "target": GROUNDING_TARGET,
            "met_on_validation": bool(n and np.mean(grounded) >= GROUNDING_TARGET),
        },
        "first_reply": {
            k: _rate([bool(r["first"][k]) for r in results])
            for k in ("json", "typology", "cited", "numeric", "cites_any")
        },
        "retry_rate": _rate([r["retry"] is not None for r in results]),
        "retry_grounded": _rate([r["retry"]["grounded"] for r in results if r["retry"]]),
        "fallback_rate": _rate([r["final_source"] == "template" for r in results]),
        "final_numeric": _rate([r["final_numeric"] for r in results]),
        "errors": sum(bool(r["errors"]) for r in results),
        "latency_s": {
            "p50": statistics.median(lat) if lat else None,
            "p95": lat[min(n - 1, int(np.ceil(0.95 * n)) - 1)] if lat else None,
            "max": lat[-1] if lat else None,
            "target_p95": LATENCY_TARGET_S,
        },
        "attributed": {
            "cases": len(attributed),
            "accuracy": _rate([r["assigned"] == r["pattern"] for r in attributed]),
        },
        "unattributed": {
            "cases": len(unattributed),
            "top3_contains_truth": _rate(
                [r["pattern"] in {c["id"] for c in r["candidates"]} for r in unattributed]
            ),
        },
        "by_pattern": by_pattern,
    }


# --------------------------------------------------------------------------- driver
def run_narrative(
    paths: Any,
    option: str = "B8",
    n: int = SAMPLE_N,
    model: str = DEFAULT_MODEL,
    url: str = "http://localhost:11434",
    timeout: float = 120.0,
    call: Call | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    from finmesh.eval.split_io import load_plan
    from finmesh.sysinfo import AnonPeak
    from finmesh.training.x6 import load_catalogue, run_seed_x6

    t0 = time.perf_counter()
    if call is None:
        call = ollama_call(url, model, timeout)
        try:  # untimed warm-up, before the expensive part: fail fast if Ollama is down
            call('Reply with the JSON object {"ok": true}.', "json")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"error": f"cannot reach Ollama at {url} ({exc}); start it with `ollama serve`"}
    catalogue = load_catalogue()
    window_hours = int(load_plan(paths).window_hours)
    with AnonPeak() as anon:
        r = run_seed_x6(paths, option, SAMPLE_SEED, progress, levels=("S2",), keep_tables=True)
        t_x6 = time.perf_counter() - t0
        got = r["tables"]["S2"]
        table: pl.DataFrame = got["table"]
        classes: list[str] = got["classes"]
        proba: np.ndarray = got["p"]
        det = table["incident"].is_not_null().to_numpy()
        patterns = table["pattern"].to_numpy().astype(str)
        idx_det = np.nonzero(det)[0]
        p_det = proba[idx_det]  # cross-fitted, defined for every detected scheme
        conf = p_det.max(axis=1) if len(idx_det) else np.zeros(0)
        correct = np.array(classes, dtype=object)[p_det.argmax(axis=1)] == patterns[idx_det]
        tau = selective_threshold(conf, correct)
        pick = idx_det[stratified_sample(table["scheme_id"].to_numpy()[det], patterns[det], n=n)]
        rows = table.to_dicts()
        results = []
        for k, i in enumerate(pick):
            case = build_case(rows[i], classes, proba[i], tau, catalogue, window_hours)
            results.append(narrate(case, catalogue, call))
            if progress and (k + 1) % 25 == 0:
                progress(f"narratives {k + 1}/{len(pick)}")
    return {
        "dataset": paths.name,
        "option": option,
        "level": "S2",
        "seed": SAMPLE_SEED,
        "model": model,
        "decoding": "json-only first, schema-constrained retry, template fallback",
        "selective": {
            "tau": tau,
            "grid": risk_coverage(conf, correct),
            "detected_schemes": int(det.sum()),
            "schemes": len(det),
            "accuracy_detected": float(correct.mean()) if len(correct) else None,
            "rule": "smallest tau with selective accuracy >= 0.5 and coverage >= 10%",
        },
        "summary": summarise(results),
        "cases": results,
        "seconds": {"x6_s2": round(t_x6, 1), "total": round(time.perf_counter() - t0, 1)},
        "peak_anon_mb": anon.mb,
    }


__all__ = [
    "TAU_GRID",
    "UNATTRIBUTED",
    "bucket_range",
    "build_case",
    "build_prompt",
    "check_reply",
    "evidence",
    "narrate",
    "numbers_in",
    "risk_coverage",
    "run_narrative",
    "selective_threshold",
    "stratified_sample",
    "summarise",
    "template_narrative",
]
