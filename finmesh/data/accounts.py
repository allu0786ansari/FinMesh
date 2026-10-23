"""Optional AMLworld accounts file: which entity owns which account at which bank.

The proposal needs this to state that an account-level privacy unit is not a
customer-level unit (one entity can hold accounts at several banks). The file
is optional for week 1: if it is missing or its header is unexpected, ingestion
continues and the profile says the entity statistics are unavailable.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from finmesh.data.schema import account_key

# Header names are matched case-insensitively after collapsing spaces.
_WANTED = {
    "bank id": "bank",
    "account number": "account",
    "entity id": "entity_id",
}


def load_accounts(path: Path) -> pl.DataFrame | None:
    """Return ``bank, account, account_key, entity_id`` or None if unusable."""
    if not path.exists():
        return None
    raw = pl.read_csv(path, infer_schema=False, encoding="utf8-lossy")
    rename: dict[str, str] = {}
    for col in raw.columns:
        norm = " ".join(col.strip().lower().split())
        if norm in _WANTED and _WANTED[norm] not in rename.values():
            rename[col] = _WANTED[norm]
    if set(rename.values()) != set(_WANTED.values()):
        return None
    return (
        raw.rename(rename)
        .select(
            pl.col("bank").str.strip_chars().cast(pl.Int64, strict=False),
            pl.col("account").str.strip_chars().str.to_uppercase(),
            pl.col("entity_id").str.strip_chars(),
        )
        .with_columns(account_key(pl.col("bank"), pl.col("account")).alias("account_key"))
    )
