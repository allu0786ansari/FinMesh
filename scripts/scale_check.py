"""Measure ingestion time and peak memory on a synthetic file of real-dataset size.

The fixture has ~4,000 rows; HI-Small has ~5 million. This script writes an
AMLworld-format CSV with N rows of pseudo-random traffic (no patterns) and
runs the week-1 transaction ingestion on it, so you can confirm the memory
budget on your own machine before downloading anything:

    uv run python scripts/scale_check.py --rows 5000000     # HI-Small size
    uv run python scripts/scale_check.py --rows 32000000    # HI-Medium size

The CSV is generated in a child process, so the peak memory printed is that of
ingestion alone. Files go to a temporary folder (or ``--workdir``) and are
deleted afterwards. The numbers are an engineering check only; they are never
research results. Synthetic accounts are spread more widely than real ones,
so this is a pessimistic test of memory.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import polars as pl

from finmesh.data.ingest import ingest_transactions
from finmesh.data.schema import RAW_TRANSACTION_HEADER
from finmesh.sysinfo import AnonPeak, peak_rss_mb


def synthetic_csv(path: Path, rows: int, banks: int = 30_000, accounts: int = 515_000) -> None:
    idx = pl.int_range(0, rows, eager=False, dtype=pl.UInt64)
    # Cheap deterministic pseudo-randomness from multiplicative hashing.
    h1 = (idx * 2654435761) % 4294967291
    h2 = (idx * 40503 + 12345) % 2147483647
    frame = (
        pl.LazyFrame()
        .select(idx.alias("i"))
        .with_columns(h1.alias("h1"), h2.alias("h2"))
        .select(
            (pl.lit(datetime(2022, 9, 1)) + pl.duration(minutes=pl.col("i") * 14_400 // rows))
            .dt.strftime("%Y/%m/%d %H:%M")
            .alias("Timestamp"),
            (pl.col("h1") % banks).cast(pl.String).alias("From Bank"),
            pl.format("A{}", pl.col("h1") % accounts).alias("Account"),
            (pl.col("h2") % banks).cast(pl.String).alias("To Bank"),
            pl.format("A{}", pl.col("h2") % accounts).alias("Account_2"),
            ((pl.col("h1") % 1_000_000) / 100).round(2).cast(pl.String).alias("Amount Received"),
            pl.lit("US Dollar").alias("Receiving Currency"),
            ((pl.col("h1") % 1_000_000) / 100).round(2).cast(pl.String).alias("Amount Paid"),
            pl.lit("US Dollar").alias("Payment Currency"),
            pl.lit("ACH").alias("Payment Format"),
            (pl.col("h2") % 981 == 0).cast(pl.Int8).cast(pl.String).alias("Is Laundering"),
        )
    )
    # Write with placeholder names, then put back AMLworld's header with its
    # repeated "Account" column, which polars cannot write directly.
    frame.sink_csv(path)
    _rewrite_header(path, ",".join(RAW_TRANSACTION_HEADER))


def _rewrite_header(path: Path, header: str) -> None:
    tmp = path.with_suffix(".tmp")
    with path.open("rb") as src, tmp.open("wb") as dst:
        src.readline()
        dst.write((header + "\n").encode())
        shutil.copyfileobj(src, dst, 1 << 24)
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=5_000_000)
    parser.add_argument("--workdir", help="folder for the temporary files (needs ~85 bytes/row)")
    parser.add_argument("--generate-only", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.generate_only:
        synthetic_csv(Path(args.generate_only), args.rows)
        return
    work = Path(tempfile.mkdtemp(prefix="finmesh-scale-", dir=args.workdir))
    try:
        csv_path = work / "SCALE_Trans.csv"
        t0 = time.perf_counter()
        cmd = [sys.executable, __file__, "--rows", str(args.rows), "--generate-only", str(csv_path)]
        subprocess.run(cmd, check=True)
        t1 = time.perf_counter()
        size_mb = csv_path.stat().st_size / 1e6
        print(f"wrote {args.rows:,} rows ({size_mb:,.0f} MB) in {t1 - t0:.1f} s (child process)")
        with AnonPeak() as anon:
            report = ingest_transactions(csv_path, work / "transactions.parquet")
        t2 = time.perf_counter()
        size = (work / "transactions.parquet").stat().st_size / 1e6
        print(f"ingested {report['rows']:,} rows in {t2 - t1:.1f} s -> {size:,.0f} MB Parquet")
        print(
            f"accounts {report['accounts']:,}  banks {report['banks']:,}  "
            f"malformed {report['malformed_cells']}  duplicates {report['duplicate_extra_rows']}"
        )
        print(
            f"peak memory of ingestion {anon.mb} MB "
            f"(peak RSS incl. memory-mapped CSV {peak_rss_mb()} MB)"
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
