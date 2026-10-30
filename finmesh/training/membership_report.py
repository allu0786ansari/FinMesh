"""A5 on the model: the page (week 12)."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import fmt, table
from finmesh.training.membership import FPRS


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def render_membership(r: dict[str, Any]) -> str:
    acc = r["accounts"]
    hp = r["hparams"]
    rows = []
    for res in r["results"].values():
        eps = res["epsilon"]
        for attack, groups in res["attacks"].items():
            for group, m in groups.items():
                row: dict[str, Any] = {
                    "model": "non-private FedAvg" if eps is None else f"DP, ε = {eps:g}",
                    "attack": attack,
                    "group": group,
                    "auc": _ci(m.get("auc_ci")),
                }
                for fpr in FPRS:
                    t = m.get(f"tpr@{fpr:g}") or {}
                    row[f"tpr{fpr:g}"] = _ci(t)
                    row[f"eps{fpr:g}"] = t.get("epsilon_lower_bound")
                row["bound"] = (
                    fmt(res["dp_bound_at_1pct"]) if group == "all" and eps is not None else "—"
                )
                rows.append(row)
    cols = [
        ("model", "Model"),
        ("attack", "Attack"),
        ("group", "Accounts"),
        ("auc", "AUC [95% CI]"),
        ("tpr0.01", "TPR at 1% FPR [95% CI]"),
        ("bound", "DP bound at 1% FPR"),
        ("eps0.01", "Empirical ε lower bound (1% FPR)"),
        ("tpr0.001", "TPR at 0.1% FPR [95% CI]"),
    ]
    verdict = (
        "**Audit failed:** a DP model's TPR at 1% FPR is above its bound. The implementation "
        "leaks more than it claims; Gate G3 blocks."
        if r["audit_violation"]
        else "**Audit passed:** no DP model's TPR at 1% FPR exceeds e^ε × 0.01 + δ."
    )
    return "\n".join(
        [
            f"# A5 · membership inference on the federated model · {r['dataset']}",
            "",
            "Deployed setup (A19): account unit (bags of at most 8 windows), degree cap "
            f"{r['cap']}. Each member's training accounts split 50/50 by a fixed hash: IN "
            f"({acc['in']:,} accounts, {acc['laundering_in']:,} with laundering) trains the "
            f"models, OUT ({acc['out']:,}, {acc['laundering_out']:,} with laundering) never does. "
            f"Seed {r['seed']}; {r['rounds']} rounds; DP settings {hp['source']} (clip "
            f"{hp['clip']:g}, batch {hp['batch']}, lr {hp['lr']:g}). The attacker is a peer bank "
            "holding the global model and the candidate's rows and labels (worst case). LOSS = "
            "−mean weighted loss of the account's bag; REF = the attacker's own local "
            "non-private MLP's loss minus the global model's. A useless attack has TPR = FPR "
            f"and AUC 0.5. Run `{r['run_id']}`; {r['seconds']['total']:,.0f} s, peak memory "
            f"{r['peak_anon_mb']:,.0f} MB.",
            "",
            table(rows, cols),
            "",
            verdict,
            "",
            "The empirical ε lower bound comes from Clopper–Pearson 95% bounds at one threshold "
            "chosen on the same data, so it is indicative; a value above the target ε would also "
            "flag a leak. Laundering accounts are few, so their intervals are wide.",
            "",
        ]
    )


__all__ = ["render_membership"]
