"""Small helpers for writing markdown reports from result dictionaries."""

from __future__ import annotations

from typing import Any

# Columns that hold identifiers or dates: printed as-is, never as 1,124.
ID_COLUMNS = frozenset({"bank", "day", "member", "largest_bank", "scheme_id", "window_hours"})


def fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.4f}" if abs(v) < 1 else f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def cell(key: str, value: Any) -> str:
    return str(value) if key in ID_COLUMNS and value is not None else fmt(value)


def table(rows: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
    head = "| " + " | ".join(label for _, label in cols) + " |"
    rule = "| " + " | ".join("---" for _ in cols) + " |"
    body = ["| " + " | ".join(cell(key, r.get(key)) for key, _ in cols) + " |" for r in rows]
    return "\n".join([head, rule, *body])
