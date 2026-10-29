"""X4 page (week 10): the neural scorer on validation and the privacy ledger."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import fmt, table

LABELS = {
    "gbdt-local": "Local GBDT (S0 reference)",
    "mlp-centralised": "MLP, centralised, non-private",
    "mlp-local": "MLP, local only, non-private",
    "mlp-fedavg": "MLP, FedAvg, non-private",
}


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def _label(name: str) -> str:
    if name in LABELS:
        return LABELS[name]
    eps = name.split("=")[1].rstrip("]")
    return f"MLP, FedAvg + DP-SGD, window unit, ε = {eps}"


def render_x4(r: dict[str, Any]) -> str:
    s = r["summary"]
    rows = [
        {
            "config": _label(n),
            "auprc": _ci(v["auprc"]),
            "auroc": v["auroc_mean"],
            "member": v["auprc_member_mean"],
        }
        for n, v in s.items()
        if n != "H2a"
    ]
    h2a = [
        {
            "config": _label(n),
            "share": _ci(v["share_of_centralised"]),
            "local": _ci(v["minus_local"]),
            "met": "yes" if v["met_on_validation"] else "no",
        }
        for n, v in s["H2a"].items()
    ]
    priv = []
    for seed in r["per_seed"]:
        for name, p in seed["privacy"].items():
            for client, rep in p["clients"].items():
                priv.append(
                    {
                        "seed": seed["seed"],
                        "config": name.split("[")[1].rstrip("]"),
                        "client": client,
                        "units": seed["clients"][client],
                        "q": rep["rate"],
                        "sigma": rep["noise"],
                        "steps": rep["steps_done"],
                        "delta": f"{rep['delta']:.1e}",
                        "spent": rep["epsilon_spent"],
                        "clipped": p["clipped_share"].get(client),
                    }
                )
    lines = [
        f"# X4 (part 1) · neural scorer on validation · {r['dataset']}",
        "",
        f"Seeds {r['seeds']}; {r['rounds']} rounds × {r['local_steps']} local steps; batch "
        f"{r['batch']} per client step; positive loss weight {r['pos_weight']:g}; clip norm 1; "
        "fixed piecewise-linear encoding (no data-dependent normalisation). AUPRC pooled over "
        "the federation's validation account-windows, averaged over seeds; Poisson bootstrap "
        f"over accounts shared by all configurations. Run `{r['run_id']}`; total "
        f"{r['seconds']:,.0f} s, peak memory {r['peak_anon_mb']:,.0f} MB.",
        "",
        "## Validation AUPRC",
        "",
        table(
            rows,
            [
                ("config", "Configuration"),
                ("auprc", "AUPRC [95% CI]"),
                ("auroc", "AUROC (mean)"),
                ("member", "Mean per-member AUPRC"),
            ],
        ),
        "",
        "## H2a on validation",
        "",
        "Federated DP at ε ≤ 10 reaches at least 0.70 of the centralised non-private AUPRC and "
        "exceeds the local-only network. Judged on test.",
        "",
        table(
            h2a,
            [
                ("config", "Configuration"),
                ("share", "Share of centralised [95% CI]"),
                ("local", "Minus local-only [95% CI]"),
                ("met", "Met on validation"),
            ],
        ),
        "",
        "## Privacy accounting per client",
        "",
        "Noise calibrated once for the planned steps with an RDP accountant (Poisson-subsampled "
        "Gaussian); accountants persist per run, and every private training is appended to "
        f"`privacy_ledger_{r['dataset']}.jsonl`, which is never rewritten.",
        "",
        table(
            priv,
            [
                ("seed", "Seed"),
                ("config", "Target"),
                ("client", "Client"),
                ("units", "Units"),
                ("q", "Sampling rate"),
                ("sigma", "Noise multiplier"),
                ("steps", "Steps"),
                ("delta", "δ"),
                ("spent", "ε spent"),
                ("clipped", "Share clipped"),
            ],
        ),
        "",
        "## Time per seed",
        "",
        table(
            [{"seed": x["seed"], **x["seconds"]} for x in r["per_seed"]],
            [("seed", "Seed")] + [(k, k) for k in r["per_seed"][0]["seconds"]],
        ),
        "",
    ]
    return "\n".join(lines)


__all__ = ["render_x4"]
