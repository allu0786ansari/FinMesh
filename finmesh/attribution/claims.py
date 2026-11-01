"""Worded evidence and claim consistency for the narrative (amendment A23).

A22 showed that rule checks on form (valid JSON, real field names, numbers copied
from the prompt) do not catch a narrative that says "most of the money was passed
on" when the evidence says pass-through 0.00. A23 adds two things, both fixed
before the run:

* **worded evidence**: every count and share value carries a fixed plain-word
  reading ("1, one payer", "0.00, none passed on"), so the model can copy true words
  instead of interpreting numbers (content planning in data-to-text generation);
* **claim consistency**: per-sentence rules that tie the claims small models make
  most often (pass-through, many payers or payees, cycles, gathering, splitting,
  layering) to the evidence field that would support them.

Hedged sentences (could, may, might, possibly, check, candidate) are not claims.
"""

from __future__ import annotations

import re
from typing import Any

# --------------------------------------------------------------------------- reading values
_COUNT_NOUN = {
    "fan_in": ("payer", "payers"),
    "fan_out": ("payee", "payees"),
    "tx_in": ("incoming transfer", "incoming transfers"),
    "tx_out": ("outgoing transfer", "outgoing transfers"),
    "cycles": ("cycle", "cycles"),
    "gather_scatter": ("account in the fan", "accounts in the fan"),
    "scatter_gather": ("account in the fan", "accounts in the fan"),
}
_SHARE_TAIL = {
    "pass_through": "passed on",
    "cross_bank_share": "with other banks",
    "new_cp_share": "new counterparties",
    "new_counterparty_share": "new counterparties",
}


def _kind(field: str) -> tuple[str, str] | None:
    """('count' | 'share', key) for a field that gets a reading, else None."""
    for key in _COUNT_NOUN:
        if field.endswith(key):
            return "count", key
    for key in _SHARE_TAIL:
        if field.endswith(key):
            return "share", key
    return None


def _float(text: str) -> float:
    return float(text.replace(",", ""))


def value_range(value: str) -> tuple[float, float] | None:
    """[low, high) of a rendered value: a number, or a bucket range."""
    v = value.strip()
    m = re.fullmatch(r"below ([\d,.]+)", v)
    if m:
        return 0.0, _float(m.group(1))
    m = re.fullmatch(r"at least ([\d,.]+), below ([\d,.]+)", v)
    if m:
        return _float(m.group(1)), _float(m.group(2))
    m = re.fullmatch(r"([\d,.]+) or more", v)
    if m:
        return _float(m.group(1)), float("inf")
    try:
        x = _float(v)
    except ValueError:
        return None
    return x, x


def count_word(low: float, high: float) -> str:
    """A23: 0 none, 1 one, 2 two, 3-9 several, 10+ many; a bucket reads by its lower bound."""
    v = low
    if v < 1:
        return "none"
    if v < 2:
        return "one"
    if v < 3:
        return "two"
    if v < 10:
        return "several"
    return "many"


def share_word(low: float, high: float) -> str:
    """A23: < 0.05 none, < 0.5 under half, < 0.8 most, else nearly all; a bucket whose upper
    bound is at most 0.5 reads under half, any other bucket by its lower bound."""
    if low != high and high <= 0.5:
        return "under half"
    v = low
    if v < 0.05:
        return "none"
    if v < 0.5:
        return "under half"
    if v < 0.8:
        return "most"
    return "nearly all"


def reading(field: str, value: str) -> str | None:
    """The fixed plain-word reading of a value (A23), or None for fields without one."""
    kind = _kind(field)
    rng = value_range(value)
    if kind is None or rng is None:
        return None
    what, key = kind
    if what == "count":
        word = count_word(*rng)
        one, many = _COUNT_NOUN[key]
        if word == "none":
            return f"no {many}"
        return f"{word} {one if word == 'one' else many}"
    return f"{share_word(*rng)} {_SHARE_TAIL[key]}"


# --------------------------------------------------------------------------- evidence facts
def _hi(ev: dict[str, str], fields: tuple[str, ...], threshold: float) -> bool:
    for f in fields:
        rng = value_range(ev.get(f, ""))
        if rng is not None and rng[0] >= threshold:
            return True
    return False


def evidence_facts(ev: dict[str, str]) -> dict[str, bool]:
    """What the evidence supports, by claim family (``ev``: field -> rendered value)."""
    fans = ("own_max_gather_scatter", "own_max_scatter_gather")
    fan_in = _hi(ev, ("own_max_fan_in", "others_fan_in"), 3)
    fan_out = _hi(ev, ("own_max_fan_out", "others_fan_out"), 3)
    return {
        "pass_through": _hi(ev, ("own_mean_pass_through", "others_pass_through"), 0.5),
        "many_payers": fan_in,
        "many_payees": fan_out,
        "cycle": _hi(ev, ("own_max_cycles",), 1),
        "gathered": fan_in or _hi(ev, fans, 2),
        "split": fan_out or _hi(ev, fans, 2),
        "layered": False,
    }


# --------------------------------------------------------------------------- claims
_HEDGE = re.compile(r"\b(could|may|might|possibl\w*|check\w*|candidates?)\b", re.IGNORECASE)
_NEG = re.compile(r"\b(no|none|not|little|low|under half|less than half|few)\b", re.IGNORECASE)
_PASS = re.compile(
    r"\b(pass(?:ed|es|ing)?|paid|sent|moved|forward(?:ed|s|ing)?)\b[^.]{0,30}?"
    r"\b(on|onward|onwards|out|through)\b|\bpass[- ]?through\b",
    re.IGNORECASE,
)
_HIGH = re.compile(
    r"\b(most|majority|nearly all|almost all|all of|much of|high|large share)\b", re.IGNORECASE
)
_MANY = r"(many|several|multiple|numerous|a (?:large|high) number of|lots of)"
_PAYERS = re.compile(
    rf"\b{_MANY}\b[^.]{{0,25}}?\b(payers|senders|sources)\b"
    rf"|\b(received|receiving|receives|inflows?)\b[^.]{{0,30}}?\bfrom {_MANY}\b",
    re.IGNORECASE,
)
_PAYEES = re.compile(
    rf"\b{_MANY}\b[^.]{{0,25}}?\b(payees|recipients|beneficiaries|destinations)\b"
    rf"|\b(sent|paid|transferred|sending|paying)\b[^.]{{0,30}}?\bto {_MANY}\b",
    re.IGNORECASE,
)
_CYCLE = re.compile(
    r"\b(cycle|cycles|cyclical|circular|round[- ]trip|returned to|back to the (?:origin\w*))\b"
)
_GATHER = re.compile(r"\b(gathered|consolidated|pooled|collected)\b", re.IGNORECASE)
_SPLIT = re.compile(r"\b(split|scattered|dispersed|distributed)\b", re.IGNORECASE)
_LAYER = re.compile(r"\b(layered|layers|layering)\b", re.IGNORECASE)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def claims_in(sentence: str) -> set[str]:
    """Claim families a non-hedged sentence asserts."""
    if _HEDGE.search(sentence):
        return set()
    found = set()
    if _PASS.search(sentence) and _HIGH.search(sentence) and not _NEG.search(sentence):
        found.add("pass_through")
    if _PAYERS.search(sentence):
        found.add("many_payers")
    if _PAYEES.search(sentence):
        found.add("many_payees")
    if _CYCLE.search(sentence.replace("CYCLE", "")):  # the upper-case id is a candidate name
        found.add("cycle")
    if _GATHER.search(sentence):
        found.add("gathered")
    if _SPLIT.search(sentence):
        found.add("split")
    if _LAYER.search(sentence):
        found.add("layered")
    return found


def claim_check(text: str, ev: dict[str, str]) -> dict[str, Any]:
    """Every claim the narrative makes, and those its evidence does not support."""
    facts = evidence_facts(ev)
    made: set[str] = set()
    for s in sentences(text):
        made |= claims_in(s)
    unsupported = sorted(c for c in made if not facts[c])
    return {
        "claims": sorted(made),
        "unsupported": unsupported,
        "consistent": not unsupported,
        "copied": bool(re.search(r"[<>]", text)),
    }


# --------------------------------------------------------------------------- number words
_UNITS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "zero": 0,
}  # fmt: skip
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}  # fmt: skip
_WORD = re.compile(
    r"\b(" + "|".join(_TENS) + r")(?:[- ](one|" + "|".join(_UNITS) + r"))?\b"
    r"|\b(" + "|".join(_UNITS) + r"|hundred|thousand)\b",
    re.IGNORECASE,
)


def number_words(text: str) -> set[float]:
    """Numbers written as words ('six', 'twenty-four'); 'one' is a determiner and skipped."""
    out: set[float] = set()
    for m in _WORD.finditer(text):
        tens, unit, single = m.group(1), m.group(2), m.group(3)
        if tens:
            n = _TENS[tens.lower()] + (
                1 if unit and unit.lower() == "one" else _UNITS.get((unit or "").lower(), 0)
            )
            out.add(float(n))
        elif single:
            s = single.lower()
            out.add(float({"hundred": 100, "thousand": 1000}.get(s, _UNITS.get(s, 0))))
    return out


__all__ = [
    "claim_check",
    "claims_in",
    "count_word",
    "evidence_facts",
    "number_words",
    "reading",
    "sentences",
    "share_word",
    "value_range",
]
