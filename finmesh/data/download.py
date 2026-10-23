"""Fetch AMLworld files from Kaggle into ``data/raw/<dataset>/``.

Needs a Kaggle account and API token (``~/.kaggle/kaggle.json`` or the
``KAGGLE_USERNAME`` / ``KAGGLE_KEY`` environment variables) and the optional
dependency: ``uv sync --extra kaggle``. If this fails on your network, use the
manual route in docs/runlog/week-01.md: download the three files from the
dataset page in a browser and place them in the same folder.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from finmesh.data.schema import dataset_files
from finmesh.paths import DatasetPaths

KAGGLE_DATASET = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"


def download(paths: DatasetPaths, include_accounts: bool = True) -> list[Path]:
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "The Kaggle client is not installed. Run `uv sync --extra kaggle`, or download the "
            "files manually (docs/runlog/week-01.md)."
        ) from exc

    api = KaggleApi()
    api.authenticate()
    files = dataset_files(paths.name)
    wanted = [files.transactions, files.patterns] + ([files.accounts] if include_accounts else [])
    paths.raw.mkdir(parents=True, exist_ok=True)
    fetched: list[Path] = []
    for name in wanted:
        target = paths.raw / name
        if target.exists():
            print(f"  already present: {target}")
            fetched.append(target)
            continue
        print(f"  downloading {name} ...")
        try:
            api.dataset_download_file(KAGGLE_DATASET, name, path=str(paths.raw), quiet=False)
        except Exception as exc:  # the Kaggle client raises several unrelated types
            if name == files.accounts:
                print(f"  could not fetch optional {name}: {exc}")
                continue
            raise
        zipped = paths.raw / f"{name}.zip"
        if zipped.exists():
            with zipfile.ZipFile(zipped) as archive:
                archive.extractall(paths.raw)
            zipped.unlink()
        fetched.append(target)
    return fetched
