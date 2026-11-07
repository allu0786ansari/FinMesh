"""A25 P5: narratives from an exported case file, so the model calls can run elsewhere.

The owner's laptop (8 GB) cannot hold a 7-8 B model, so the narrative step is split:

1. **Export** (owner's machine, has the data): :func:`export_cases` builds exactly the cases
   the narrative run would build (same tables, tau, stratified sample, evidence, prompts'
   inputs) and writes one JSON file. With ``split="test"`` it reads the tables the sealed
   X1+X6 run saved and logs the narrative's own opening first, as `narrative --test` does.
2. **Run** (a GPU notebook, no dataset needed): :func:`run_cases` calls the model on every
   case with the frozen protocol (A23 prompt; A25N adds the scope rule to strict
   grounding), retry and template fallback, saving after every case so a dropped session
   resumes.
3. **Render** (back on the owner's machine): the result file goes through the same
   report writers as a local run.

:func:`select_then_template` derives candidate N4 from a finished run without new calls: the
model's chosen fields and typology are kept, and fixed templates write every sentence.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from finmesh.attribution import narrative as nar
from finmesh.attribution.claims import claim_check, reading, scope_check

BUNDLE_VERSION = 1


def _cases_from_tables(
    tables: dict[str, Any],
    val_s2: dict[str, Any],
    n: int,
    catalogue: dict[str, Any],
    window_hours: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], float | None]:
    """Cases from the S2 table to narrate, with tau from ``val_s2`` (validation)."""
    det_v = val_s2["table"]["incident"].is_not_null().to_numpy()
    idx_v = np.nonzero(det_v)[0]
    pat_v = val_s2["table"]["pattern"].to_numpy().astype(str)
    classes: list[str] = val_s2["classes"]
    p_v = val_s2["p"][idx_v]
    conf_v = p_v.max(axis=1) if len(idx_v) else np.zeros(0)
    correct_v = np.array(classes, dtype=object)[p_v.argmax(axis=1)] == pat_v[idx_v]
    tau = nar.selective_threshold(conf_v, correct_v)

    s2 = tables["S2"]
    table: pl.DataFrame = s2["table"]
    proba: np.ndarray = s2["p"]
    det = table["incident"].is_not_null().to_numpy()
    patterns = table["pattern"].to_numpy().astype(str)
    idx_det = np.nonzero(det)[0]
    p_det = proba[idx_det]
    conf = p_det.max(axis=1) if len(idx_det) else np.zeros(0)
    correct = np.array(classes, dtype=object)[p_det.argmax(axis=1)] == patterns[idx_det]
    pick = idx_det[nar.stratified_sample(table["scheme_id"].to_numpy()[det], patterns[det], n=n)]
    rows = table.to_dicts()
    cases = [nar.build_case(rows[i], classes, proba[i], tau, catalogue, window_hours) for i in pick]
    selective = {
        "tau": tau,
        "grid": nar.risk_coverage(conf, correct),
        "detected_schemes": int(det.sum()),
        "schemes": len(det),
        "accuracy_detected": float(correct.mean()) if len(correct) else None,
        "rule": "smallest tau with selective accuracy >= 0.5 and coverage >= 10%",
    }
    return cases, selective, tau


def export_cases(
    paths: Any,
    option: str = "B8",
    n: int = nar.SAMPLE_N,
    protocol: str = "A25N",
    split: str = "val",
    allow_repeat: bool = False,
) -> dict[str, Any]:
    """The case bundle for :func:`run_cases`. Validation recomputes the X6 tables (seed 0);
    test reads the sealed run's saved tables and logs the narrative's opening."""
    from finmesh.eval.split_io import load_plan
    from finmesh.training.x6 import load_catalogue, run_seed_x6

    if protocol not in nar.PROTOCOLS or protocol in ("A21", "A22"):
        raise ValueError("export supports the A23 family (A23, A25N)")
    catalogue = load_catalogue()
    window_hours = int(load_plan(paths).window_hours)
    if split == "val":
        r = run_seed_x6(paths, option, nar.SAMPLE_SEED, levels=("S0", "S2"), keep_tables=True)
        tables = r["tables"]
        cases, selective, _ = _cases_from_tables(tables, tables["S2"], n, catalogue, window_hours)
        topk = nar.topk_analysis(tables)
        opened = None
    else:
        from finmesh.eval.sealed import EvalStore, open_sealed_test, opened_before
        from finmesh.training.sealed_runs import _load, test_dir

        inputs = test_dir(paths, option) / "narrative_inputs.pkl"
        if not inputs.exists():
            return {"error": f"{inputs} is missing; run `finmesh test-x1` on this dataset first"}
        digest = hashlib.sha256(inputs.read_bytes()).hexdigest()
        got = _load(inputs)
        config = {"experiment": f"narrative-{protocol}", "dataset": paths.name, "option": option}
        first = opened_before(paths, config, int(got["seed"]))
        if first is not None and not allow_repeat:
            return {
                "error": f"the {protocol} narrative already opened this test on {first['time']}"
            }
        open_sealed_test(
            EvalStore(paths, option),
            config,
            int(got["seed"]),
            f"A25: {protocol} narratives exported for a remote model run",
            allow_repeat=allow_repeat,
            extra={"inputs_sha256": digest},
        )
        cases, selective, _ = _cases_from_tables(
            got["test"], got["val"]["S2"], n, catalogue, window_hours
        )
        pat_v = got["val"]["S2"]["table"]
        src = pat_v.filter(pl.col("incident").is_not_null())["pattern"].to_numpy().astype(str)
        topk = nar.topk_analysis(got["test"], frequency_source=src)
        opened = {"inputs_sha256": digest}
    return {
        "version": BUNDLE_VERSION,
        "dataset": paths.name,
        "option": option,
        "split": split,
        "protocol": protocol,
        "seed": nar.SAMPLE_SEED,
        "n": n,
        "catalogue": catalogue,
        "cases": cases,
        "selective": selective,
        "topk": topk,
        "opened": opened,
    }


def run_cases(
    bundle: dict[str, Any],
    call: nar.Call,
    model: str,
    checkpoint: Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Narrate every case of ``bundle``; resumable from ``checkpoint`` (a JSON list)."""
    protocol = bundle["protocol"]
    catalogue = bundle["catalogue"]
    done: list[dict[str, Any]] = []
    if checkpoint is not None and checkpoint.exists():
        saved = json.loads(checkpoint.read_text())
        if saved.get("model") == model and saved.get("protocol") == protocol:
            done = saved["results"]
    t0 = time.perf_counter()
    results = list(done)
    for k in range(len(done), len(bundle["cases"])):
        try:
            results.append(nar.narrate(bundle["cases"][k], catalogue, call, protocol))
        except nar.ModelUnavailable as exc:
            return {
                "error": f"the model server stopped at case {k + 1} ({exc}); "
                f"{len(results)} cases are saved. Run the same command again to resume."
            }
        if checkpoint is not None:
            checkpoint.write_text(
                json.dumps({"model": model, "protocol": protocol, "results": results})
            )
        if progress and (k + 1) % 25 == 0:
            progress(f"narratives {k + 1}/{len(bundle['cases'])}")
    return result_from(bundle, results, model, round(time.perf_counter() - t0, 1))


def result_from(
    bundle: dict[str, Any], results: list[dict[str, Any]], model: str, seconds: float
) -> dict[str, Any]:
    return {
        "dataset": bundle["dataset"],
        "option": bundle["option"],
        "split": bundle["split"],
        "protocol": bundle["protocol"],
        "topk": bundle["topk"],
        "level": "S2",
        "seed": bundle["seed"],
        "model": model,
        "decoding": "json-only first, schema-constrained retry, template fallback",
        "timeout_s": nar.TIMEOUT_S[bundle["protocol"]],
        "selective": bundle["selective"],
        "summary": nar.summarise(results),
        "cases": results,
        "seconds": {"total": seconds},
        "peak_anon_mb": None,
    }


def _selected_text(case: dict[str, Any], fields: list[str]) -> str:
    """N4: fixed sentences for the case, then the selected evidence lines, worded."""
    ev = {e["field"]: e for e in case["evidence"]}
    head = (
        f"The linked case holds {ev['case_accounts']['value']} accounts at "
        f"{ev['case_members']['value']} federation members over "
        f"{ev['case_span_hours']['value']} hours, of which {ev['own_accounts']['value']} are "
        "at your bank."
    )
    if case["assigned"] == nar.UNATTRIBUTED:
        what = "The pattern is unattributed; candidates to check: " + ", ".join(
            c["id"] for c in case["candidates"]
        )
    else:
        what = f"Assigned pattern: {case['assigned']}"
    parts = []
    for f in fields:
        e = ev.get(f)
        if e is None or e["value"] in nar.MISSING:
            continue
        words = reading(f, e["value"])
        where = "at your bank" if e["section"] == "Your bank" else e["section"].lower()
        parts.append(f"{e['label']} ({where}): {e['value']}" + (f", {words}" if words else ""))
    tail = (" Key evidence: " + "; ".join(parts) + ".") if parts else ""
    return f"{head} {what}.{tail}"


def _rebuild(
    att: dict[str, Any] | None, case: dict[str, Any], catalogue: dict[str, Any]
) -> dict[str, Any] | None:
    """One reply with its narrative rebuilt from the cited fields; every check rerun."""
    if att is None:
        return None
    fields = [e["field"] for e in nar.shown(case)]
    known = nar.evidence_numbers(case)
    allowed = nar.allowed_typologies(case)
    ev_map = {e["field"]: e["value"] for e in case["evidence"]}
    try:
        reply = json.loads(att.get("raw") or "")
    except (ValueError, TypeError):
        reply = None
    if not isinstance(reply, dict):
        raw = att.get("raw") or ""
    else:
        cited = [f for f in reply.get("cited_fields") or [] if isinstance(f, str)]
        reply["narrative"] = _selected_text(case, cited[:4])
        raw = json.dumps(reply)
    res: dict[str, Any] = {"raw": raw}
    res.update(nar.check_reply(raw, case["assigned"], fields, known, allowed, catalogue))
    res.update(nar._a23_checks(res, ev_map, known))
    sc = scope_check(res.get("narrative") or "", ev_map)
    res.update(sc)
    res["strict"] = bool(res["strict"] and sc["scope_ok"])
    return res


def select_then_template(result: dict[str, Any], catalogue: dict[str, Any]) -> dict[str, Any]:
    """Candidate N4 from a finished run: same replies, but the narrative is rebuilt from the
    model's cited fields and typology by fixed templates, then every check is rerun."""
    out_cases = []
    for c in result["cases"]:
        keep: tuple[str, ...] = ("scheme_id", "pattern", "assigned", "top_prediction")
        keep += ("confidence", "candidates", "evidence", "review_actions")
        case = {k: c[k] for k in keep}
        known = nar.evidence_numbers(case)
        allowed = nar.allowed_typologies(case)
        ev_map = {e["field"]: e["value"] for e in case["evidence"]}
        first = _rebuild(c["first"], case, catalogue)
        retry = _rebuild(c["retry"], case, catalogue)
        assert first is not None
        if first["strict"]:
            final, source = first, "first"
        elif retry is not None and retry["strict"]:
            final, source = retry, "retry"
        else:
            final, source = None, "template"
        text = (
            nar.template_narrative(case, "A23") if final is None else final.get("narrative") or ""
        )
        claims = claim_check(text, ev_map)
        out_cases.append(
            {
                **c,
                "first": first,
                "retry": retry,
                "final_source": source,
                "narrative": text,
                "final_numeric": nar.numbers_in(text) <= known,
                "final_mentions_ok": nar.typologies_named(text, catalogue) <= allowed,
                "final_consistent": claims["consistent"],
                "final_unsupported": claims["unsupported"],
                "final_scope_ok": scope_check(text, ev_map)["scope_ok"],
                "protocol": "A25N-select",
            }
        )
    return {
        **result,
        "protocol": "A25N",
        "design": "N4 select-then-template",
        "summary": nar.summarise(out_cases),
        "cases": out_cases,
    }


__all__ = ["BUNDLE_VERSION", "export_cases", "result_from", "run_cases", "select_then_template"]
