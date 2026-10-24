"""The bank visibility model (proposal Section 7.2).

A member sees every transaction in which one of its accounts is the sender or
the receiver, with the full record, including the counterparty's account and
bank, as it would in a real payment message. It does not see transactions
between two accounts that are both held elsewhere, so its graph view holds
first-hop edges to other banks and nothing beyond them.

Every downstream per-bank computation (features, detectors, evidence) must
start from :func:`member_view`; nothing else in FinMesh reads another
member's rows.
"""

from __future__ import annotations

from typing import Any

import polars as pl

LEG_KINDS: tuple[str, ...] = ("internal", "cross_member", "boundary", "invisible")


def attach_members(lf: pl.LazyFrame, membership: pl.DataFrame) -> pl.LazyFrame:
    """Add ``src_member`` and ``dst_member`` (null when the bank is outside)."""
    m = membership.lazy()
    return lf.join(
        m.select(pl.col("bank").alias("from_bank"), pl.col("member").alias("src_member")),
        on="from_bank",
        how="left",
    ).join(
        m.select(pl.col("bank").alias("to_bank"), pl.col("member").alias("dst_member")),
        on="to_bank",
        how="left",
    )


def leg_kind_expr() -> pl.Expr:
    """How a transaction sits relative to the federation."""
    src, dst = pl.col("src_member"), pl.col("dst_member")
    return (
        pl.when(src.is_null() & dst.is_null())
        .then(pl.lit("invisible"))
        .when(src.is_null() | dst.is_null())
        .then(pl.lit("boundary"))
        .when(src == dst)
        .then(pl.lit("internal"))
        .otherwise(pl.lit("cross_member"))
        .cast(pl.Enum(list(LEG_KINDS)))
    )


def member_view(lf_with_members: pl.LazyFrame, member: int) -> pl.LazyFrame:
    """Rows member ``member`` can see, with its side of each transaction."""
    src, dst = pl.col("src_member"), pl.col("dst_member")
    return lf_with_members.filter((src == member) | (dst == member)).with_columns(
        pl.when((src == member) & (dst == member))
        .then(pl.lit("internal"))
        .when(src == member)
        .then(pl.lit("out"))
        .otherwise(pl.lit("in"))
        .alias("side")
    )


def visible_members_expr() -> pl.Expr:
    """Inside an aggregation: the distinct members that can see any of the rows."""
    return (
        pl.concat_list("src_member", "dst_member")
        .explode(empty_as_null=False)
        .drop_nulls()
        .unique()
        .sort()
    )


def coverage(lf_with_members: pl.LazyFrame) -> dict[str, Any]:
    """Share of transactions the federation can see, by leg kind (one streaming pass)."""
    legs = (
        lf_with_members.group_by(leg_kind_expr().alias("kind"))
        .agg(pl.len().alias("rows"))
        .collect(engine="streaming")
    )
    by_kind = {k: 0 for k in LEG_KINDS}
    by_kind.update({str(k): int(v) for k, v in legs.iter_rows()})
    total = sum(by_kind.values())
    return {
        "rows": total,
        "rows_by_leg_kind": by_kind,
        "visible_share": (total - by_kind["invisible"]) / total if total else None,
    }


def account_share(sizes: pl.DataFrame, membership: pl.DataFrame) -> dict[str, Any]:
    """Accounts held at member banks.

    An account key is ``<bank>:<account>``, so every account belongs to exactly
    one bank and its member follows from the bank. The per-bank distinct
    account counts from :func:`finmesh.data.consortium.bank_sizes` therefore
    give the share directly, with no pass over the transactions.
    """
    total = int(sizes["accounts"].sum())
    inside = int(sizes.join(membership, on="bank", how="inner")["accounts"].sum())
    return {
        "accounts": total,
        "member_accounts": inside,
        "member_account_share": inside / total if total else None,
    }
