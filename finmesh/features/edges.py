"""The label-free edge table every feature pass reads (week 4).

One streaming pass over the transactions writes, for rows inside the
observation window, only what the extractor needs: window, time, banks,
hashed account keys, amounts converted to the reference currency, currency
and payment-format codes. The ground-truth column is never selected, so nothing
downstream of this table can read it.

Currency rates are derived from the data: AMLworld records both the amount
paid (payment currency) and the amount received (receiving currency), so a
cross-currency row reveals the exchange rate. The median ratio per currency
pair on **training** rows is chained to the reference currency.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import polars as pl

from finmesh.data.lowmem import hashed_key
from finmesh.data.splits import SplitPlan, window_index_expr

# AMLworld payment formats, in code order; anything else is code 7.
FORMATS: tuple[str, ...] = (
    "ACH",
    "Bitcoin",
    "Cash",
    "Cheque",
    "Credit Card",
    "Reinvestment",
    "Wire",
)
OTHER_FORMAT = len(FORMATS)


def _in_observation(plan: SplitPlan) -> pl.Expr:
    ts = pl.col("timestamp")
    return (ts >= plan.observation.start) & (ts < plan.observation.end)


def currencies(transactions: Path, plan: SplitPlan) -> list[str]:
    """Every currency used inside the observation window, sorted (its code order)."""
    lf = pl.scan_parquet(transactions).filter(_in_observation(plan))
    names = pl.concat(
        [
            lf.select(pl.col("payment_currency").alias("c")),
            lf.select(pl.col("receiving_currency").alias("c")),
        ]
    ).unique()
    return sorted(names.collect(engine="streaming")["c"].to_list())


def pair_ratios(transactions: Path, plan: SplitPlan) -> pl.DataFrame:
    """Median received/paid ratio per (payment, receiving) currency pair on training rows."""
    train = plan.period("train")
    ts = pl.col("timestamp")
    return (
        pl.scan_parquet(transactions)
        .filter(
            (ts >= train.start)
            & (ts < train.end)
            & (pl.col("payment_currency") != pl.col("receiving_currency"))
            & (pl.col("amount_paid") > 0)
            & (pl.col("amount_received") > 0)
        )
        .group_by("payment_currency", "receiving_currency")
        .agg(
            (pl.col("amount_received") / pl.col("amount_paid")).median().alias("ratio"),
            pl.len().alias("rows"),
        )
        .sort("payment_currency", "receiving_currency")
        .collect(engine="streaming")
    )


def chain_rates(
    names: Sequence[str], ratios: pl.DataFrame, reference: str
) -> dict[str, float | None]:
    """Reference-currency value of one unit of each currency (None when unreachable).

    A pair row (P, R, r) means one unit of P buys r units of R. Rates spread
    from the reference currency along pairs, in a fixed order, until nothing
    changes; the first path found wins, so the result is deterministic.
    """
    rate: dict[str, float | None] = {c: None for c in names}
    if reference in rate:
        rate[reference] = 1.0
    pairs = [(str(p), str(r), float(x)) for p, r, x, _ in ratios.iter_rows() if x and x > 0]
    changed = True
    while changed:
        changed = False
        for p, r, x in pairs:
            rp, rr = rate.get(p), rate.get(r)
            if rp is None and rr is not None:
                rate[p] = x * rr
                changed = True
            elif rr is None and rp is not None:
                rate[r] = rp / x
                changed = True
    return rate


def write_edges(
    transactions: Path,
    plan: SplitPlan,
    out: Path,
    rates: dict[str, float | None],
    names: Sequence[str],
) -> int:
    """Write the label-free edge table; return its row count."""
    # Lookups are written as Enum casts and when-chains, not replace_strict:
    # replace_strict on a string column holds about 1.7 GB per use at 32 M rows,
    # while these stream in about 200 MB.
    enum = pl.Enum(list(names))

    def code(currency: str) -> pl.Expr:
        return pl.col(currency).cast(enum).to_physical().cast(pl.UInt8)

    def lookup(column: str, mapping: dict[str, Any], default: Any) -> pl.Expr:
        items = list(mapping.items())
        if not items:
            return pl.lit(default)
        k0, v0 = items[0]
        expr: Any = pl.when(pl.col(column) == k0).then(pl.lit(v0))
        for k, v in items[1:]:
            expr = expr.when(pl.col(column) == k).then(pl.lit(v))
        result: pl.Expr = expr.otherwise(pl.lit(default))
        return result

    known = {c: r for c, r in rates.items() if r is not None}

    def usd(amount: str, currency: str) -> pl.Expr:
        return pl.col(amount) * lookup(currency, known, None).cast(pl.Float64)

    lf = (
        pl.scan_parquet(transactions)
        .filter(_in_observation(plan))
        .select(
            window_index_expr(plan).alias("window"),
            "timestamp",
            pl.col("from_bank"),
            pl.col("to_bank"),
            hashed_key("src_key").alias("src"),
            hashed_key("dst_key").alias("dst"),
            usd("amount_paid", "payment_currency").alias("usd_paid"),
            usd("amount_received", "receiving_currency").alias("usd_received"),
            code("payment_currency").alias("pay_ccy"),
            code("receiving_currency").alias("recv_ccy"),
            lookup("payment_format", {f: i for i, f in enumerate(FORMATS)}, OTHER_FORMAT)
            .cast(pl.UInt8)
            .alias("fmt"),
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    lf.sink_parquet(out, compression="zstd")
    rows: int = pl.scan_parquet(out).select(pl.len()).collect().item()
    return rows


def rate_report(ratios: pl.DataFrame, rates: dict[str, float | None]) -> dict[str, Any]:
    return {
        "pairs_used": ratios.height,
        "rates": rates,
        "unreachable": sorted(c for c, r in rates.items() if r is None),
    }
