"""Gate G3 evidence: the federated DP track on validation (end of week 12).

Gathers, per dataset, the week-12 artifacts (X5 with the A19 settings and the
IID arm, the membership audit, the stacked ensemble), the week-11 influence
study, the A19 tuning and the privacy ledger, and applies the rule fixed in
A19 before any of them existed:

* **blocked** if any client's spent ε exceeds its target, or the membership
  audit finds a DP model leaking beyond its bound;
* otherwise the DP scorer joins the deployed detector at the smallest ε ≤ 10
  whose ensemble gain over the local ensemble on **HI-Medium** validation has
  a 95% CI above 0; if none does, the local ensemble is deployed and the DP
  scorer is reported as a finding.

H2a and H2b are recorded on validation; test decides them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir
from finmesh.reporting import fmt, table
from finmesh.training.dp_tune import PROXY_DATASETS

DATASETS = ("HI-Medium", "LI-Medium")
DECIDING = "HI-Medium"


def _load(week: str, kind: str, dataset: str) -> dict[str, Any] | None:
    path = artifacts_dir() / week / f"{kind}_{dataset}.json"
    if not path.exists():
        return None
    prov, r = read_artifact(path)
    return None if prov["fixture"] else r


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def ledger_check(dataset: str) -> dict[str, Any]:
    """Every private training on record for this dataset: spent ε never above its target."""
    entries, over = 0, 0
    for week in ("week10", "week11", "week12"):
        path = artifacts_dir() / week / f"privacy_ledger_{dataset}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            entries += 1
            over += int(e["epsilon_spent"] > e["epsilon_target"] + 1e-9)
    return {"entries": entries, "over_target": over, "ok": entries > 0 and over == 0}


def summarise(dataset: str) -> dict[str, Any] | None:
    x5 = _load("week12", "x5", dataset)
    mia = _load("week12", "membership", dataset)
    ens = _load("week12", "ensemble", dataset)
    inf = _load("week11", "influence", dataset)
    if x5 is None and mia is None and ens is None:
        return None
    out: dict[str, Any] = {"dataset": dataset, "ledger": ledger_check(dataset)}
    if x5 is not None:
        s = x5["summary"]
        out["hparams"] = x5["hparams"]
        out["h2a"] = {
            k: {
                "share": v["share_of_centralised"],
                "minus_local": v["minus_local"],
                "met": v["met_on_validation"],
            }
            for k, v in s["H2a"].items()
        }
        out["h2b"] = {
            k: {"diff": v["window_minus_account"], "met": v["met_on_validation"]}
            for k, v in s["H2b"].items()
        }
        out["iid"] = s.get("iid")
        out["cap_cost_nonprivate"] = s["cap_cost_nonprivate"]
        out["deployed"] = {
            k: s[f"dp[account,cap{x5['cap']},eps={k}]"]["auprc"] for k in ("1", "3", "10")
        }
        out["centralised"] = s["centralised"]["auprc"]
    if mia is not None:
        out["audit_violation"] = mia["audit_violation"]
        out["mia"] = {
            name: {
                attack: (res["attacks"][attack]["all"].get("tpr@0.01") or {})
                for attack in res["attacks"]
            }
            | {"bound": res.get("dp_bound_at_1pct")}
            for name, res in mia["results"].items()
        }
        np_res = next(r for r in mia["results"].values() if r["epsilon"] is None)
        out["mia_power"] = {
            a: (np_res["attacks"][a]["all"].get("auc_ci") or {}) for a in np_res["attacks"]
        }
    if ens is not None:
        es = ens["summary"]
        out["ensemble"] = {
            "local": es["stack[local]"]["auprc"],
            "gains": es["gain_over_local"],
            "smallest_qualifying_epsilon": es["smallest_qualifying_epsilon"],
        }
    if inf is not None:
        views = inf["views"]
        out["influence"] = {
            v: {k: views[v]["group_size"][k] for k in ("q50", "q99", "q100")} for v in views
        }
    return out


def tuning_summary() -> list[dict[str, Any]]:
    rows = []
    for ds in PROXY_DATASETS:
        r = _load("week12", "dp_tune", ds)
        if r is None or not r.get("best"):
            continue
        b = r["best"]
        ref = (r.get("non_private") or {}).get("holdout_auprc")
        rows.append(
            {
                "dataset": ds,
                "chosen": f"clip {b['clip']:g}, batch {b['batch']}, lr {b['lr']:g}",
                "auprc": b["holdout_auprc"],
                "nonprivate": ref,
                "edge": ", ".join(k for k, v in (r.get("on_edge") or {}).items() if v) or "none",
            }
        )
    return rows


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ledger_ok = all(r["ledger"]["ok"] for r in rows)
    audit_ok = all(not r.get("audit_violation", False) for r in rows)
    if not ledger_ok or not audit_ok:
        return {
            "decision": "blocked",
            "reason": "accounting" if not ledger_ok else "membership audit",
            "epsilon": None,
        }
    hi = next((r for r in rows if r["dataset"] == DECIDING), None)
    if hi is None or "ensemble" not in hi:
        return {"decision": "pending", "reason": f"no {DECIDING} ensemble yet", "epsilon": None}
    eps = hi["ensemble"]["smallest_qualifying_epsilon"]
    if eps is None:
        return {"decision": "local ensemble", "reason": "no ε qualifies", "epsilon": None}
    return {
        "decision": "DP scorer joins",
        "reason": f"smallest qualifying ε = {eps:g}",
        "epsilon": eps,
    }


def render_g3(rows: list[dict[str, Any]], tuning: list[dict[str, Any]]) -> str:
    d = decide(rows)
    eps_txt = "—" if d["epsilon"] is None else f"{d['epsilon']:g}"
    text = {
        "blocked": f"**Blocked** ({d['reason']}): fix before week 13.",
        "pending": f"**Pending:** {d['reason']}.",
        "local ensemble": "**The local ensemble (GBDT + autoencoder) is deployed**; at no "
        "ε ≤ 10 does the DP scorer add to it on HI-Medium validation. The DP scorer is reported "
        "as a finding.",
        "DP scorer joins": f"**The DP scorer joins the deployed detector at ε = {eps_txt}** "
        "(the smallest ε whose ensemble gain on HI-Medium validation has a CI above 0).",
    }[d["decision"]]
    lines = [
        "# Gate G3 evidence · federated DP detection on validation",
        "",
        "Generated by `finmesh g3` from the week-12 artifacts (X5 with the A19 settings, the "
        "membership audit, the stacked ensemble), the week-11 influence study and the privacy "
        "ledgers. Rule fixed in A19 before these results. Hypotheses are judged on test.",
        "",
        f"**Rule outcome:** {text}",
        "",
    ]
    if tuning:
        lines += [
            "## A19 tuning on the proxy federations",
            "",
            table(
                tuning,
                [
                    ("dataset", "Proxy"),
                    ("chosen", "Chosen"),
                    ("auprc", "Hold-out AUPRC (DP, ε = 3)"),
                    ("nonprivate", "Non-private FedAvg"),
                    ("edge", "On the grid's edge"),
                ],
            ),
            "",
        ]
    for r in rows:
        items: list[dict[str, Any]] = [
            {
                "item": "Privacy ledger: spent ε ≤ target",
                "value": f"{r['ledger']['entries']:,} client trainings, "
                f"{r['ledger']['over_target']} over target",
                "ok": "yes" if r["ledger"]["ok"] else "no",
            }
        ]
        if "audit_violation" in r:
            mia_txt = "; ".join(
                f"{n.split('eps=')[1].rstrip(']') if 'eps=' in n else 'non-private'}: REF "
                f"{fmt((v.get('REF') or {}).get('estimate'))}"
                + (f" (bound {fmt(v['bound'])})" if v.get("bound") else "")
                for n, v in r["mia"].items()
            )
            items.append(
                {
                    "item": "Membership audit: TPR at 1% FPR within the DP bound",
                    "value": mia_txt,
                    "ok": "no" if r["audit_violation"] else "yes",
                }
            )
            items.append(
                {
                    "item": "Membership attack power on the non-private model (AUC)",
                    "value": ", ".join(f"{a} {_ci(c)}" for a, c in r["mia_power"].items()),
                    "ok": "—",
                }
            )
        if "h2a" in r:
            for k, v in r["h2a"].items():
                items.append(
                    {
                        "item": f"H2a, ε = {k}: share of centralised; minus local-only",
                        "value": f"{_ci(v['share'])}; {_ci(v['minus_local'])}",
                        "ok": "yes" if v["met"] else "no",
                    }
                )
            for k, v in r["h2b"].items():
                items.append(
                    {
                        "item": f"H2b, ε = {k}: window − account",
                        "value": _ci(v["diff"]),
                        "ok": "yes" if v["met"] else "no",
                    }
                )
            for k, v in r["deployed"].items():
                items.append(
                    {
                        "item": f"Deployed DP scorer, ε = {k} (AUPRC)",
                        "value": f"{_ci(v)} vs centralised {_ci(r['centralised'])}",
                        "ok": "—",
                    }
                )
            if r.get("iid"):
                for k, v in r["iid"].items():
                    arm = "non-private" if k == "nonprivate" else f"ε = {k}"
                    items.append(
                        {
                            "item": f"IID − bank-partitioned, {arm}",
                            "value": _ci(v["iid_minus_partitioned"]),
                            "ok": "—",
                        }
                    )
            items.append(
                {
                    "item": "Degree cap's cost, non-private",
                    "value": _ci(r["cap_cost_nonprivate"]),
                    "ok": "—",
                }
            )
        if "influence" in r:
            items.append(
                {
                    "item": "Group size (median / p99 / max), uncapped vs capped",
                    "value": "; ".join(
                        f"{v}: {fmt(g['q50'])} / {fmt(g['q99'])} / {fmt(g['q100'])}"
                        for v, g in r["influence"].items()
                    ),
                    "ok": "—",
                }
            )
        if "ensemble" in r:
            e = r["ensemble"]
            items.append(
                {
                    "item": "Local ensemble (GBDT + autoencoder) AUPRC",
                    "value": _ci(e["local"]),
                    "ok": "—",
                }
            )
            for k, g in e["gains"].items():
                items.append(
                    {
                        "item": f"Ensemble gain from {k}",
                        "value": _ci(g),
                        "ok": "yes" if g["ci_above_zero"] else "no",
                    }
                )
        lines += [
            f"## {r['dataset']}",
            "",
            table(items, [("item", "Item"), ("value", "Validation"), ("ok", "Holds")]),
            "",
        ]
    return "\n".join(lines)


def run_g3(out: Path) -> tuple[Path | None, dict[str, Any]]:
    """Write the page; without any real-data artifact (CI), leave an existing page alone."""
    rows = [r for ds in DATASETS if (r := summarise(ds)) is not None]
    if not rows:
        return None, {"decision": "pending", "reason": "no real-data artifacts", "epsilon": None}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_g3(rows, tuning_summary()))
    return out, decide(rows)


__all__ = ["decide", "ledger_check", "render_g3", "run_g3", "summarise"]
