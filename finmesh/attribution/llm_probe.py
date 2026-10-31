"""Week-2 check: can a local 3-4B model answer in schema-valid JSON, fast enough?

Proposal Section 8.4 calls a locally hosted model once per incident to draft a
grounded narrative, with output constrained to a JSON schema. This probe sends
``n`` synthetic incident prompts to an Ollama server on this machine and
records latency, JSON validity and schema validity, so the model can be
chosen at Gate G0 and the language-model latency target set (PT6).

Prompts are built from the eight AMLworld pattern names and random bucketed
evidence; they contain no real data. Only ``localhost`` endpoints are
accepted (threat ADV-6: no investigation content leaves the machine).
"""

from __future__ import annotations

import json
import random
import statistics
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

TYPOLOGIES: dict[str, str] = {
    "T-FAN-OUT": "one account pays many accounts in a short time",
    "T-FAN-IN": "many accounts pay one account in a short time",
    "T-GATHER-SCATTER": "funds gathered into one account, then paid out to many",
    "T-SCATTER-GATHER": "funds paid out to intermediaries, then gathered into one account",
    "T-CYCLE": "funds move through a chain of accounts and return to the origin",
    "T-RANDOM": "funds hop through a random chain of accounts",
    "T-BIPARTITE": "a set of accounts pays another set of accounts",
    "T-STACK": "two or more layers of bipartite transfers",
}
EVIDENCE_FIELDS = (
    "fan_out_bucket",
    "fan_in_bucket",
    "pass_through_bucket",
    "new_counterparty",
    "cross_bank_share_bucket",
    "amount_bucket",
    "burst_level",
)
DEFAULT_MODEL = "llama3.2:3b"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def response_schema(candidates: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "typology_id": {"type": "string", "enum": candidates},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "cited_fields": {
                "type": "array",
                "items": {"type": "string", "enum": list(EVIDENCE_FIELDS)},
            },
            "rationale": {"type": "string", "maxLength": 400},
        },
        "required": ["typology_id", "confidence", "cited_fields", "rationale"],
    }


def make_prompt(rng: random.Random) -> tuple[str, list[str], dict[str, Any]]:
    candidates = rng.sample(sorted(TYPOLOGIES), 5)
    evidence = {
        "fan_out_bucket": rng.choice(["0", "1-2", "3-5", "6-10", ">10"]),
        "fan_in_bucket": rng.choice(["0", "1-2", "3-5", "6-10", ">10"]),
        "pass_through_bucket": rng.choice(["<0.2", "0.2-0.5", "0.5-0.8", ">0.8"]),
        "new_counterparty": rng.choice([True, False]),
        "cross_bank_share_bucket": rng.choice(["<0.25", "0.25-0.75", ">0.75"]),
        "amount_bucket": rng.choice(["<1k", "1k-10k", "10k-100k", ">100k"]),
        "burst_level": rng.choice(["low", "medium", "high"]),
    }
    catalogue = "\n".join(f"- {c}: {TYPOLOGIES[c]}" for c in candidates)
    prompt = (
        "You are assisting an anti-money-laundering analyst. Choose the typology that best "
        "matches the evidence. Use only the candidate IDs listed. Cite only evidence fields "
        "that appear below. Answer in JSON.\n\n"
        f"Candidate typologies:\n{catalogue}\n\nEvidence (bucketed):\n"
        + "\n".join(f"- {k}: {v}" for k, v in evidence.items())
    )
    return prompt, candidates, evidence


def validate_reply(text: str, candidates: list[str]) -> dict[str, bool]:
    """Checks applied to the raw model output, before any repair."""
    out = {"json": False, "schema": False, "grounded": False}
    try:
        reply = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return out
    out["json"] = isinstance(reply, dict)
    if not out["json"]:
        return out
    conf = reply.get("confidence")
    cited = reply.get("cited_fields")
    out["schema"] = (
        isinstance(reply.get("typology_id"), str)
        and isinstance(conf, int | float)
        and 0 <= conf <= 1
        and isinstance(cited, list)
        and isinstance(reply.get("rationale"), str)
    )
    out["grounded"] = (
        out["schema"]
        and reply["typology_id"] in candidates
        and all(f in EVIDENCE_FIELDS for f in cited)
    )
    return out


def assert_local(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in LOCAL_HOSTS:
        raise ValueError(f"refusing non-local model endpoint {url!r} (proposal threat ADV-6)")


def call_ollama(
    url: str,
    model: str,
    prompt: str,
    schema: dict[str, Any] | str,
    timeout: float,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {"temperature": 0, "num_ctx": 2048}
    if max_tokens is not None:
        options["num_predict"] = max_tokens
    body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "format": schema, "options": options}
    ).encode()
    request = urllib.request.Request(
        url.rstrip("/") + "/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result: dict[str, Any] = json.loads(response.read())
    return result


def run_probe(
    model: str = DEFAULT_MODEL,
    n: int = 20,
    url: str = "http://localhost:11434",
    seed: int = 7,
    timeout: float = 120.0,
    constrained: bool = True,
) -> dict[str, Any]:
    """Probe a model.

    ``constrained=True`` passes the JSON schema with the candidate enum to the
    decoder, so the typology can only be a candidate: grounding is then true by
    construction and measures nothing. ``constrained=False`` asks only for JSON
    output (amendment A7): the grounding rate then measures the model itself.
    """
    assert_local(url)
    rng = random.Random(seed)
    latencies: list[float] = []
    checks = {"json": 0, "schema": 0, "grounded": 0}
    errors: list[str] = []
    # One untimed warm-up call loads the model into memory.
    warm_prompt, warm_cands, _ = make_prompt(random.Random(seed + 1))
    try:
        warm_format: dict[str, Any] | str = response_schema(warm_cands) if constrained else "json"
        call_ollama(url, model, warm_prompt, warm_format, timeout)
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"model": model, "error": f"cannot reach Ollama at {url}: {exc}"}
    for _ in range(n):
        prompt, candidates, _ = make_prompt(rng)
        if not constrained:
            prompt += (
                '\n\nReply with a JSON object with keys "typology_id", "confidence" '
                '(0 to 1), "cited_fields" (list of evidence field names) and "rationale".'
            )
        fmt: dict[str, Any] | str = response_schema(candidates) if constrained else "json"
        start = time.perf_counter()
        try:
            reply = call_ollama(url, model, prompt, fmt, timeout)
        except (urllib.error.URLError, TimeoutError) as exc:
            errors.append(str(exc))
            continue
        latencies.append(time.perf_counter() - start)
        for key, ok in validate_reply(reply.get("response", ""), candidates).items():
            checks[key] += int(ok)
    done = len(latencies)
    ordered = sorted(latencies)
    return {
        "model": model,
        "decoding": "schema-constrained" if constrained else "json-only",
        "calls": n,
        "completed": done,
        "errors": errors[:5],
        "latency_s": {
            "p50": round(statistics.median(ordered), 2) if ordered else None,
            "p95": round(ordered[min(done - 1, int(0.95 * done))], 2) if ordered else None,
            "max": round(ordered[-1], 2) if ordered else None,
        },
        "json_valid_rate": checks["json"] / done if done else None,
        "schema_valid_rate": checks["schema"] / done if done else None,
        "grounded_rate": checks["grounded"] / done if done else None,
    }
