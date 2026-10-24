"""Convert AMLworld transaction CSVs to typed Parquet.

Design choices, all made for a single 8 GB machine and for auditability:

* The CSV is scanned lazily and written with ``sink_parquet`` so the full
  file is never held in memory at once.
* Every column is read as text and cast explicitly with ``strict=False``;
  values that fail to parse become nulls and are counted in the quality
  report instead of silently disappearing.
* ``tx_id`` is the zero-based row number in the original CSV. It is the only
  transaction identifier used anywhere downstream (scheme links, splits,
  evidence records), so results always map back to a source line.
* Bank identifiers are parsed as integers, which makes ``"010"`` (as written
  in pattern files) and ``"10"`` (as written in the CSV) the same bank.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from finmesh.data.schema import (
    CANONICAL_COLUMNS,
    RAW_TRANSACTION_HEADER,
    TIMESTAMP_FORMAT,
    account_key,
)


class HeaderMismatchError(ValueError):
    """The CSV header is not the AMLworld transactions header."""


def _normalise_header_cell(cell: str) -> str:
    return " ".join(cell.strip().strip('"').split()).lower()


def validate_header(path: Path) -> None:
    """Fail fast if ``path`` does not start with the AMLworld transactions header."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        first = handle.readline().rstrip("\r\n")
    found = tuple(_normalise_header_cell(c) for c in first.split(","))
    expected = tuple(_normalise_header_cell(c) for c in RAW_TRANSACTION_HEADER)
    if found != expected:
        raise HeaderMismatchError(
            f"{path.name}: unexpected header.\n  expected: {list(RAW_TRANSACTION_HEADER)}\n"
            f"  found:    {first.split(',')}"
        )


def scan_raw_transactions(path: Path) -> pl.LazyFrame:
    """Lazily read the CSV with every column as text and canonical names by position."""
    return pl.scan_csv(
        path,
        has_header=False,
        skip_rows=1,
        schema={name: pl.String for name in CANONICAL_COLUMNS},
        encoding="utf8-lossy",
    )


def _bank(col: str) -> pl.Expr:
    return pl.col(col).str.strip_chars().cast(pl.Int64, strict=False).alias(col)


def _account(col: str) -> pl.Expr:
    return pl.col(col).str.strip_chars().str.to_uppercase().alias(col)


def _amount(col: str) -> pl.Expr:
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False).alias(col)


def _text(col: str) -> pl.Expr:
    return pl.col(col).str.strip_chars().alias(col)


def normalise(raw: pl.LazyFrame, *, with_row_index: bool = True) -> pl.LazyFrame:
    """Cast raw text columns to the canonical schema and add account keys."""
    frame = raw.with_row_index("tx_id") if with_row_index else raw
    typed = frame.with_columns(
        pl.col("timestamp")
        .str.strip_chars()
        .str.strptime(pl.Datetime("us"), TIMESTAMP_FORMAT, strict=False),
        _bank("from_bank"),
        _account("from_account"),
        _bank("to_bank"),
        _account("to_account"),
        _amount("amount_received"),
        _text("receiving_currency"),
        _amount("amount_paid"),
        _text("payment_currency"),
        _text("payment_format"),
        pl.col("is_laundering").str.strip_chars().cast(pl.Int8, strict=False),
    )
    if with_row_index:
        typed = typed.with_columns(pl.col("tx_id").cast(pl.UInt64))
    return typed.with_columns(
        account_key(pl.col("from_bank"), pl.col("from_account")).alias("src_key"),
        account_key(pl.col("to_bank"), pl.col("to_account")).alias("dst_key"),
    )


def ingest_transactions(csv_path: Path, out_path: Path) -> dict[str, Any]:
    """Validate, normalise and write ``transactions.parquet``; return a quality report."""
    validate_header(csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    normalise(scan_raw_transactions(csv_path)).sink_parquet(out_path, compression="zstd")
    return transaction_quality(out_path)


ROWS_PER_DUPLICATE_SLICE = 4_000_000


def _duplicate_counts(lf: pl.LazyFrame, value_cols: list[str], rows: int) -> tuple[int, int]:
    """Count duplicate rows (every value column equal) in bounded memory.

    AMLworld can contain genuine repeats, so duplicates are reported, never
    dropped. Rows are compared through a 64-bit hash of all value columns (a
    false match has probability about n^2 / 2^65, under 1e-4 at 32 M rows).
    The hash space is processed in slices of about four million rows, so the
    hash table stays near 250 MB whatever the dataset size. Week-1 counts on
    the Small sets (exact comparison) were 9 and 8.
    """
    slices = max(1, -(-rows // ROWS_PER_DUPLICATE_SLICE))
    hashed = lf.select(pl.struct(value_cols).hash(seed=0).alias("row_hash"))
    extra = groups = 0
    for i in range(slices):
        part = (
            hashed.filter(pl.col("row_hash") % slices == i)
            .group_by("row_hash")
            .agg(pl.len().alias("n"))
            .filter(pl.col("n") > 1)
            .select((pl.col("n") - 1).sum().alias("extra"), pl.len().alias("groups"))
            .collect(engine="streaming")
            .row(0, named=True)
        )
        extra += int(part["extra"] or 0)
        groups += int(part["groups"] or 0)
    return extra, groups


def transaction_quality(parquet_path: Path) -> dict[str, Any]:
    """Counts that decide whether the data can be trusted before any modelling."""
    lf = pl.scan_parquet(parquet_path)
    value_cols = [c for c in CANONICAL_COLUMNS]
    summary = lf.select(
        pl.len().alias("rows"),
        *[pl.col(c).null_count().alias(f"null_{c}") for c in value_cols],
        (pl.col("amount_paid") < 0).sum().alias("negative_amount_paid"),
        (pl.col("amount_received") < 0).sum().alias("negative_amount_received"),
        (pl.col("src_key") == pl.col("dst_key")).sum().alias("self_transfers"),
        pl.col("is_laundering").sum().alias("laundering_rows"),
        # A range test, not ``is_in``: ``is_in`` is not supported by the streaming
        # engine and silently moves the whole query in memory (5.3 GB at 32 M rows).
        ((pl.col("is_laundering") < 0) | (pl.col("is_laundering") > 1))
        .sum()
        .alias("invalid_label_values"),
        pl.col("timestamp").min().alias("first_timestamp"),
        pl.col("timestamp").max().alias("last_timestamp"),
    ).collect(engine="streaming")
    report: dict[str, Any] = summary.row(0, named=True)

    malformed = sum(report[f"null_{c}"] for c in value_cols)
    report["malformed_cells"] = malformed

    extra, groups = _duplicate_counts(lf, value_cols, int(report["rows"]))
    report["duplicate_extra_rows"] = extra
    report["duplicate_groups"] = groups

    # Distinct accounts and banks, counted on 64-bit hashes of the keys: about
    # a third of the memory of counting the strings, with a negligible chance
    # of a collision (about 1e-8 at 3 M accounts).
    accounts = (
        pl.concat(
            [
                lf.select(pl.col("src_key").hash(seed=0).alias("k")),
                lf.select(pl.col("dst_key").hash(seed=0).alias("k")),
            ]
        )
        .select(pl.col("k").n_unique())
        .collect(engine="streaming")
        .item()
    )
    banks = (
        pl.concat(
            [lf.select(pl.col("from_bank").alias("b")), lf.select(pl.col("to_bank").alias("b"))]
        )
        .select(pl.col("b").n_unique())
        .collect(engine="streaming")
        .item()
    )
    report["accounts"] = int(accounts)
    report["banks"] = int(banks)
    for key in ("first_timestamp", "last_timestamp"):
        if report[key] is not None:
            report[key] = report[key].isoformat(sep=" ")
    return report
