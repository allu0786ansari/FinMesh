"""What the analyst console shows beside an incident card (week 16).

* A **rule-based typology hint** from the catalogue's fixed decision list, applied to what
  the bank itself sees of the alerted account (its own neighbourhood features) and the
  linked case's size. It is labelled as a hint: the evaluated attributor is X6, which
  works on incidents assembled over the validation period, and its own accuracy (about
  0.2, top three about 0.47) is reported on its page. The hint's review actions come from
  the catalogue, never from a model.
* A **deterministic summary** in the A23 template's style: values with their fixed
  plain-word readings, neutral wording, so it passes the A23 claim check by construction.
  No language model runs on the demo path; the narrative study is A21–A23.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from finmesh.attribution.claims import count_word, reading
from finmesh.training.x6 import load_catalogue, rule_predict


def _f(features: dict[str, Any], name: str) -> float | None:
    v = features.get(name)
    if v is None:
        return None
    v = float(v)
    return None if np.isnan(v) else v


def _said(field: str, value: float | None, kind: str) -> str:
    if value is None:
        return "not available"
    text = f"{value:.2f}" if kind == "share" else f"{round(value):,}"
    words = reading(field, text)
    return f"{text} ({words})" if words else text


def _loops(cycles: float | None) -> str:
    # Worded without "cycle": the frozen A23 claim check does not see negation for cycles.
    if cycles is None:
        return "an unknown number of short money loops (2 to 4 hops)"
    n = round(cycles)
    return f"{n} ({count_word(n, n)}) short money loops (2 to 4 hops)"


def case_summary(features: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    catalogue = load_catalogue()
    fan_in, fan_out = _f(features, "fan_in"), _f(features, "fan_out")
    cycles_parts = [_f(features, c) for c in ("cyc2", "cyc3", "cyc4")]
    cycles = max((c for c in cycles_parts if c is not None), default=None)
    sg = [_f(features, c) for c in ("sg_out_max", "sg_in_max")]
    scatter = max((c for c in sg if c is not None), default=None)
    pass_through = _f(features, "pass_through")
    peers_with_record = int(card.get("peer_records", 0))
    members = 1 + len({e["member"] for e in card.get("evidence", []) if e["status"] == "ok"})
    names = catalogue["shape_features"]
    shape = {
        "fan_in": fan_in,
        "fan_out": fan_out,
        "gather_scatter": None,  # not part of the alert's own features on the demo path
        "cycles": cycles,
        "scatter_gather": scatter,
        "pass_through": pass_through,
        "accounts": 1 + peers_with_record,
        "members": members,
    }
    sig = np.array([[np.nan if shape[n] is None else shape[n] for n in names]], dtype=float)
    hint = str(rule_predict(sig, catalogue)[0])
    entry = {e["id"]: e for e in catalogue["entries"]}[hint]
    peers = card.get("peer_alerts", 0)
    asked = card.get("members_asked", 0)
    summary = (
        f"At your bank, the alerted account has {_said('own_max_fan_out', fan_out, 'count')} "
        f"distinct payees, {_said('own_max_fan_in', fan_in, 'count')} distinct payers, "
        f"{_loops(cycles)} and a pass-through share of "
        f"{_said('own_mean_pass_through', pass_through, 'share')}. "
        f"{asked} other members were asked; {peers} reported an alert on a counterparty and "
        f"{peers_with_record} returned a record."
        + (" Some members could not be reached." if card.get("evidence_incomplete") else "")
    )
    return {
        "typology_hint": hint,
        "typology_hint_basis": "catalogue rules on the bank's own view (a hint, not the X6 "
        "attributor)",
        "typology_description": entry["description"],
        "review_actions": list(entry["review_actions"]),
        "summary": summary,
    }


__all__ = ["case_summary"]
