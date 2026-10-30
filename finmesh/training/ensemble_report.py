"""X4 part 2 page (week 12): the stacked ensemble."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import table
from finmesh.training.ensemble import neural_inputs
from finmesh.training.membership_report import _ci

LABELS = {
    "dp1": "DP scorer, ε = 1",
    "dp3": "DP scorer, ε = 3",
    "dp10": "DP scorer, ε = 10",
    "fedavg": "FedAvg MLP, non-private",
    "centralised": "Centralised MLP, non-private",
}


def render_ensemble(r: dict[str, Any]) -> str:
    s = r["summary"]
    cap = r["cap"]
    rows = [
        {"config": "Local GBDT (raw scores)", "auprc": _ci(s["gbdt"]["auprc"])},
        {"config": "Stack: GBDT", "auprc": _ci(s["stack[gbdt]"]["auprc"])},
        {"config": "Stack: GBDT + autoencoder (local)", "auprc": _ci(s["stack[local]"]["auprc"])},
    ]
    gains = []
    for k in neural_inputs(cap):
        name = f"stack[local+{k}]"
        if name not in s:
            continue
        rows.append({"config": f"{LABELS[k]} alone", "auprc": _ci(s[k]["auprc"])})
        rows.append({"config": f"Stack: local + {LABELS[k]}", "auprc": _ci(s[name]["auprc"])})
        g = s["gain_over_local"][k]
        gains.append(
            {
                "input": LABELS[k],
                "gain": _ci(g),
                "above": "yes" if g["ci_above_zero"] else "no",
            }
        )
    eps = s.get("smallest_qualifying_epsilon")
    verdict = (
        f"The DP scorer adds to the local ensemble from ε = {eps:g} (smallest ε whose gain has a "
        "95% CI above 0)."
        if eps is not None
        else "At no ε ≤ 10 does the DP scorer add to the local ensemble with a 95% CI above 0."
    )
    hp = r["hparams"]
    return "\n".join(
        [
            f"# X4 · stacked ensemble on validation · {r['dataset']}",
            "",
            "Base scores per seed: each member's local GBDT and local autoencoder (member view), "
            f"and the neural scorers saved by X5 run `{r['x5_run']}` (DP scorer: account unit, "
            f"degree cap {cap}; {hp['source']}). Stacker: A13 (per member, standardised logistic "
            "regression, C = 1), cross-fitted on the two halves of validation, on logit(GBDT), "
            "log(autoencoder error) and logit(neural). AUPRC pooled over validation, averaged "
            f"over seeds {r['seeds']}, paired Poisson bootstrap over accounts. "
            f"{r['seconds']:,.0f} s, peak memory {r['peak_anon_mb']:,.0f} MB.",
            "",
            table(rows, [("config", "Configuration"), ("auprc", "AUPRC [95% CI]")]),
            "",
            f"Recalibrating the GBDT per member (stack − raw): {_ci(s['stacking_over_raw_gbdt'])}; "
            f"adding the autoencoder: {_ci(s['autoencoder_over_gbdt'])}.",
            "",
            "## What each federated scorer adds to the local ensemble",
            "",
            table(
                gains,
                [
                    ("input", "Added scorer"),
                    ("gain", "Gain over local ensemble [95% CI]"),
                    ("above", "CI above 0"),
                ],
            ),
            "",
            verdict,
            "",
        ]
    )


__all__ = ["render_ensemble"]
