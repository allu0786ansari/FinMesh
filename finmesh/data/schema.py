"""AMLworld file formats and the canonical FinMesh transaction schema.

AMLworld (Altman et al., NeurIPS 2023) ships, per dataset, a transactions CSV,
a pattern file that groups some laundering transactions into named schemes, and
an accounts CSV mapping accounts to banks and owning entities.

The transactions CSV header repeats the column name ``Account`` (sender, then
receiver), so FinMesh never relies on header names for those columns: it
checks the header against :data:`RAW_TRANSACTION_HEADER` and then assigns
canonical names by position.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

RAW_TRANSACTION_HEADER: tuple[str, ...] = (
    "Timestamp",
    "From Bank",
    "Account",
    "To Bank",
    "Account",
    "Amount Received",
    "Receiving Currency",
    "Amount Paid",
    "Payment Currency",
    "Payment Format",
    "Is Laundering",
)

CANONICAL_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_received",
    "receiving_currency",
    "amount_paid",
    "payment_currency",
    "payment_format",
    "is_laundering",
)

TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M"

# Final dtypes after normalisation (see finmesh.data.ingest.normalise).
TRANSACTION_DTYPES: dict[str, pl.DataType] = {
    "tx_id": pl.UInt64(),
    "timestamp": pl.Datetime("us"),
    "from_bank": pl.Int64(),
    "from_account": pl.String(),
    "to_bank": pl.Int64(),
    "to_account": pl.String(),
    "amount_received": pl.Float64(),
    "receiving_currency": pl.String(),
    "amount_paid": pl.Float64(),
    "payment_currency": pl.String(),
    "payment_format": pl.String(),
    "is_laundering": pl.Int8(),
    "src_key": pl.String(),
    "dst_key": pl.String(),
}

# The eight laundering patterns modelled by the AMLworld generator.
PATTERN_TYPES: tuple[str, ...] = (
    "FAN-OUT",
    "FAN-IN",
    "GATHER-SCATTER",
    "SCATTER-GATHER",
    "CYCLE",
    "RANDOM",
    "BIPARTITE",
    "STACK",
)

# Columns used to match a pattern-file line to its row in the transactions CSV.
# Amount received and receiving currency are left out on purpose: they are
# derived from amount paid by the generator's FX step and add no selectivity.
LINK_KEY: tuple[str, ...] = (
    "timestamp",
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_paid",
    "payment_currency",
    "payment_format",
)


@dataclass(frozen=True)
class DatasetFiles:
    transactions: str
    patterns: str
    accounts: str


def dataset_files(name: str) -> DatasetFiles:
    """File names AMLworld uses for a dataset such as ``HI-Small``."""
    return DatasetFiles(
        transactions=f"{name}_Trans.csv",
        patterns=f"{name}_Patterns.txt",
        accounts=f"{name}_accounts.csv",
    )


PRIMARY_DATASETS: tuple[str, ...] = ("HI-Small", "LI-Small")
FALLBACK_DATASETS: tuple[str, ...] = ("HI-Medium",)
FIXTURE_DATASET = "FIXTURE-Small"


def account_key(bank: pl.Expr, account: pl.Expr) -> pl.Expr:
    """Globally unique account key: ``<bank id>:<account id>``.

    AMLworld account identifiers are only unique within a bank, so every
    downstream join uses this key rather than the raw account string.
    """
    return pl.concat_str([bank.cast(pl.String), pl.lit(":"), account])
