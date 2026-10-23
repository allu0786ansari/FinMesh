from __future__ import annotations

import csv
from pathlib import Path

import polars as pl
import pytest

from finmesh.data.fixture import FixtureTruth
from finmesh.data.ingest import HeaderMismatchError, ingest_transactions, validate_header
from finmesh.data.schema import RAW_TRANSACTION_HEADER, TRANSACTION_DTYPES, dataset_files
from finmesh.paths import DatasetPaths


def test_header_accepted(fixture_paths: DatasetPaths, fixture_truth: FixtureTruth) -> None:
    validate_header(fixture_paths.raw / dataset_files(fixture_paths.name).transactions)


def test_header_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("Timestamp,From,To,Amount\n2022/09/01 00:00,1,2,3\n")
    with pytest.raises(HeaderMismatchError):
        validate_header(bad)


def test_row_count_and_labels(ingested: dict[str, object], fixture_truth: FixtureTruth) -> None:
    tx = ingested["transactions"]
    assert isinstance(tx, dict)
    assert tx["rows"] == fixture_truth.rows
    assert tx["laundering_rows"] == fixture_truth.laundering_rows
    assert tx["banks"] == fixture_truth.banks
    assert tx["malformed_cells"] == 0
    assert tx["duplicate_extra_rows"] == fixture_truth.duplicate_extra_rows
    assert tx["invalid_label_values"] == 0


def test_schema_and_tx_id_order(fixture_paths: DatasetPaths, ingested: dict[str, object]) -> None:
    frame = pl.read_parquet(fixture_paths.transactions)
    assert dict(frame.schema) == TRANSACTION_DTYPES
    assert frame["tx_id"].to_list() == list(range(frame.height))
    # tx_id 0 is the first data line of the CSV.
    with (fixture_paths.raw / dataset_files(fixture_paths.name).transactions).open() as handle:
        reader = csv.reader(handle)
        next(reader)
        first = next(reader)
    row = frame.row(0, named=True)
    assert row["from_account"] == first[2]
    assert row["timestamp"].strftime("%Y/%m/%d %H:%M") == first[0]
    assert row["src_key"] == f"{int(first[1])}:{first[2]}"


def test_malformed_values_are_counted(tmp_path: Path) -> None:
    csv_path = tmp_path / "x_Trans.csv"
    rows = [
        [
            "2022/09/01 00:20",
            "10",
            "8000EBD30",
            "10",
            "8000EBD30",
            "3697.34",
            "US Dollar",
            "3697.34",
            "US Dollar",
            "Reinvestment",
            "0",
        ],
        [
            "not a time",
            "011",
            "8000F4580",
            "01",
            "8000F5340",
            "abc",
            "US Dollar",
            "0.01",
            "US Dollar",
            "Cheque",
            "1",
        ],
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(RAW_TRANSACTION_HEADER)
        writer.writerows(rows)
    report = ingest_transactions(csv_path, tmp_path / "out.parquet")
    assert report["rows"] == 2
    assert report["null_timestamp"] == 1
    assert report["null_amount_received"] == 1
    assert report["malformed_cells"] == 2
    frame = pl.read_parquet(tmp_path / "out.parquet")
    # Zero-padded bank ids normalise to the same integer.
    assert frame["from_bank"].to_list() == [10, 11]
    assert frame["to_bank"].to_list() == [10, 1]
    assert frame["src_key"].to_list() == ["10:8000EBD30", "11:8000F4580"]
