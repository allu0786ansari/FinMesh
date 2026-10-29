"""X5 page (week 11): privacy unit and degree cap, with DP settings tuned on the proxy."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import fmt, table
from finmesh.training.x5 import dp_name


def _ci(d: dict[str, Any] | None) -> str:
    if not d or d.get("estimate") is None:
        return "—"
    return f"{fmt(d['estimate'])} [{fmt(d['low'])}, {fmt(d['high'])}]"


def render_x5(r: dict[str, Any]) -> str:
    s = r["summary"]
    cap = f"cap{r['cap']}"
    refs = [
        {"config": label, "auprc": _ci(s[key]["auprc"]), "auroc": s[key]["auroc_mean"]}
        for key, label in (
            ("centralised", "Centralised MLP, non-private"),
            ("local", "Local-only MLP, non-private"),
            ("fedavg", "FedAvg MLP, non-private"),
            (f"centralised[{cap}]", f"Centralised MLP, non-private, degree cap {r['cap']}"),
        )
        if key in s
    ]
    grid = []
    for eps in r["epsilons"]:
        row: dict[str, Any] = {"eps": eps}
        for unit in ("window", "account"):
            for view in ("member", cap):
                row[f"{unit}_{view}"] = _ci(s[dp_name(unit, view, eps)]["auprc"])
        grid.append(row)
    h2a = [
        {
            "eps": k,
            "share": _ci(v["share_of_centralised"]),
            "local": _ci(v["minus_local"]),
            "met": "yes" if v["met_on_validation"] else "no",
        }
        for k, v in s["H2a"].items()
    ]
    h2b = [
        {
            "eps": k,
            "loss": _ci(v["window_minus_account"]),
            "share": _ci(v["account_share_of_window"]),
            "met": "yes" if v["met_on_validation"] else "no",
        }
        for k, v in s["H2b"].items()
    ]
    cost = [
        {
            "eps": k,
            "account": _ci(v["account_capped_minus_uncapped"]),
            "window": _ci(v["window_capped_minus_uncapped"]),
        }
        for k, v in s["cap_cost"].items()
    ]
    hp = r["hparams"]
    return "\n".join(
        [
            f"# X5 · privacy unit and degree cap on validation · {r['dataset']}",
            "",
            f"Seeds {r['seeds']}; {r['rounds']} rounds × {r['local_steps']} local steps. DP "
            f"settings from `finmesh/schemas/dp_hparams.json` ({hp['source']}): clip norm "
            f"{hp['clip']:g}, expected batch {hp['batch']}, learning rate {hp['lr']:g} (A18). "
            "Account unit: one account's bag of at most 8 windows. Degree cap: at most "
            f"{r['cap']} distinct counterparties per account, features rebuilt. AUPRC pooled over "
            "validation, averaged over seeds; Poisson bootstrap over accounts shared by every "
            f"configuration. Run `{r['run_id']}`; total {r['seconds']:,.0f} s, peak memory "
            f"{r['peak_anon_mb']:,.0f} MB.",
            "",
            "## Non-private references",
            "",
            table(
                refs,
                [
                    ("config", "Configuration"),
                    ("auprc", "AUPRC [95% CI]"),
                    ("auroc", "AUROC (mean)"),
                ],
            ),
            "",
            f"The cap alone (non-private): {_ci(s['cap_cost_nonprivate'])} AUPRC.",
            "",
            "## FedAvg + DP-SGD: AUPRC by unit, features and ε",
            "",
            table(
                grid,
                [
                    ("eps", "ε"),
                    ("window_member", "Window unit"),
                    (f"window_{cap}", "Window unit, capped"),
                    ("account_member", "Account unit"),
                    (f"account_{cap}", "Account unit, capped"),
                ],
            ),
            "",
            "## H2a on validation (tuned DP)",
            "",
            "Window unit, member-view features: at least 0.70 of the centralised MLP and above "
            "the local-only MLP. Judged on test.",
            "",
            table(
                h2a,
                [
                    ("eps", "ε"),
                    ("share", "Share of centralised [95% CI]"),
                    ("local", "Minus local-only [95% CI]"),
                    ("met", "Met on validation"),
                ],
            ),
            "",
            "## H2b on validation",
            "",
            "At the same ε the account unit loses measurably more AUPRC than the window unit: the "
            "paired difference window − account has a 95% CI above 0.",
            "",
            table(
                h2b,
                [
                    ("eps", "ε"),
                    ("loss", "Window − account [95% CI]"),
                    ("share", "Account as a share of window"),
                    ("met", "Met on validation"),
                ],
            ),
            "",
            "## Cost of the degree cap under DP",
            "",
            table(
                cost,
                [
                    ("eps", "ε"),
                    ("account", "Account unit: capped − uncapped"),
                    ("window", "Window unit: capped − uncapped"),
                ],
            ),
            "",
            "What the cap buys is in `influence_<ds>.md`: the number of other accounts' training "
            "units one account moves through its neighbours' features.",
            "",
        ]
    )


__all__ = ["render_x5"]
