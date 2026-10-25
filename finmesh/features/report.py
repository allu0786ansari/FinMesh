"""Markdown summary of a feature build: rows, rates, time and memory per stage and member."""

from __future__ import annotations

from typing import Any

from finmesh.reporting import table


def render_build(meta: dict[str, Any]) -> str:
    t = meta["timings"]
    nb = meta["neighbourhood"]
    total_s = sum(v["seconds"] for v in t.values())
    peak = max(v["peak_anon_mb"] for v in t.values())
    rates = meta["currencies"]
    lines = [
        f"# Feature build · {meta['dataset']}"
        + ("" if meta.get("view", "member") == "member" else f" · {meta['view']} view"),
        "",
        f"Federation {meta['option']}, {meta.get('view', 'member')} view, "
        f"{meta['window_hours']} h windows, feature schema "
        f"v{meta['schema_version']} (`{meta['schema_sha256'][:12]}`), {meta['slices']} account "
        f"slices. Edge rows in the observation window: {meta['edge_rows']:,}.",
        "",
        f"**Total {total_s:,.0f} s; peak memory {peak:,.0f} MB** "
        "(anonymous memory, the part that counts against RAM; budget 8 GB).",
        "",
        "| Partition | Account-windows |",
        "| --- | --- |",
        *[f"| {p} | {n:,} |" for p, n in meta["rows"].items()],
        "",
        "## Stages",
        "",
        table(
            [{"stage": k, **v} for k, v in t.items()],
            [("stage", "Stage"), ("seconds", "Seconds"), ("peak_anon_mb", "Peak MB")],
        ),
        "",
        f"## Neighbourhood pass per member (lookback {nb['lookback_windows']} windows, "
        f"hub cap {nb['cap']})",
        "",
        table(
            [
                {
                    "member": int(m),
                    "seconds": v["seconds"],
                    "visible_edge_rows": v["visible_edge_rows"],
                    "rate": v["visible_edge_rows"] / v["seconds"] if v["seconds"] else None,
                }
                for m, v in sorted(nb["members"].items(), key=lambda kv: int(kv[0]))
            ],
            [
                ("member", "Member"),
                ("seconds", "Seconds"),
                ("visible_edge_rows", "Visible edge rows (with lookback)"),
                ("rate", "Rows per second"),
            ],
        ),
        "",
        "## Exchange rates (reference-currency value of one unit, from training rows)",
        "",
        table(
            [{"currency": c, "rate": r} for c, r in rates["rates"].items()],
            [("currency", "Currency"), ("rate", "Rate")],
        ),
        "",
        f"Currency pairs observed: {rates['pairs_used']}. "
        + (
            f"No rate for: {', '.join(rates['unreachable'])} (their legs count in "
            "`unconvertible_share`)."
            if rates["unreachable"]
            else "Every currency has a rate."
        ),
    ]
    return "\n".join(lines) + "\n"
