"""CSV loading and refresh cache utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from chamber_gui.models import CSV_COLUMNS, CsvSnapshot, NUMERIC_COLUMNS, SourceMode


@dataclass
class SnapshotCache:
    """In-memory cache to avoid reloading unchanged CSV data."""

    snapshot: CsvSnapshot | None = None
    source_key: str | None = None


def infer_source_mode(path: Path) -> SourceMode:
    """Infers whether the source is a file or folder."""
    if path.exists():
        if path.is_dir():
            return "folder"
        return "file"
    if path.suffix.lower() == ".csv":
        return "file"
    return "folder"


def find_latest_csv(folder_path: Path) -> Path | None:
    """Finds the most recently modified CSV under the folder."""
    if not folder_path.exists() or not folder_path.is_dir():
        return None
    latest_path: Path | None = None
    latest_mtime: float | None = None
    for csv_path in folder_path.rglob("*.csv"):
        try:
            mtime = csv_path.stat().st_mtime
        except OSError:
            continue
        if latest_mtime is None or mtime > latest_mtime:
            latest_mtime = mtime
            latest_path = csv_path
    return latest_path


def load_csv_snapshot(csv_path: Path, previous_mtime: float | None) -> CsvSnapshot:
    """Loads a CSV snapshot from disk.

    Args:
        csv_path: Input CSV location.
        previous_mtime: Previous modified time used by caller.

    Returns:
        Parsed CSV snapshot.
    """
    if not csv_path.exists():
        return CsvSnapshot(
            data=pd.DataFrame(),
            mtime=None,
            file_exists=False,
            rows_loaded=0,
            parse_errors_count=0,
            last_update_time=datetime.now(tz=UTC),
            warning=f"CSV not found: {csv_path}",
            data_changed=False,
        )

    mtime = csv_path.stat().st_mtime
    if previous_mtime is not None and mtime == previous_mtime:
        # Caller can skip replace when mtime unchanged.
        return CsvSnapshot(
            data=pd.DataFrame(),
            mtime=mtime,
            file_exists=True,
            rows_loaded=0,
            parse_errors_count=0,
            last_update_time=datetime.now(tz=UTC),
            warning=None,
            data_changed=False,
        )

    try:
        df = pd.read_csv(csv_path)
    except Exception as error:  # pylint: disable=broad-except
        return CsvSnapshot(
            data=pd.DataFrame(),
            mtime=mtime,
            file_exists=True,
            rows_loaded=0,
            parse_errors_count=0,
            last_update_time=datetime.now(tz=UTC),
            warning=f"CSV read failed: {error}",
            data_changed=False,
        )

    parse_errors_count = 0
    timestamp_column = CSV_COLUMNS["timestamp"]
    if timestamp_column in df.columns:
        parsed = pd.to_datetime(df[timestamp_column], errors="coerce", utc=True)
        parse_errors_count += int(parsed.isna().sum())
        df[timestamp_column] = parsed

    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            continue
        parsed = pd.to_numeric(df[column], errors="coerce")
        parse_errors_count += int(parsed.isna().sum()) - int(df[column].isna().sum())
        df[column] = parsed

    return CsvSnapshot(
        data=df,
        mtime=mtime,
        file_exists=True,
        rows_loaded=len(df.index),
        parse_errors_count=max(parse_errors_count, 0),
        last_update_time=datetime.now(tz=UTC),
        warning=None,
        data_changed=True,
    )


def _warning_snapshot(
    cache: SnapshotCache,
    warning: str,
    *,
    file_exists: bool,
) -> CsvSnapshot:
    """Builds a warning snapshot, preserving last good data when available."""
    if cache.snapshot and not cache.snapshot.data.empty:
        cache.snapshot = CsvSnapshot(
            data=cache.snapshot.data,
            mtime=cache.snapshot.mtime,
            file_exists=file_exists,
            rows_loaded=cache.snapshot.rows_loaded,
            parse_errors_count=cache.snapshot.parse_errors_count,
            last_update_time=datetime.now(tz=UTC),
            warning=warning,
            data_changed=False,
        )
        return cache.snapshot

    cache.snapshot = CsvSnapshot(
        data=pd.DataFrame(),
        mtime=None,
        file_exists=file_exists,
        rows_loaded=0,
        parse_errors_count=0,
        last_update_time=datetime.now(tz=UTC),
        warning=warning,
        data_changed=False,
    )
    return cache.snapshot


def get_latest_snapshot(
    cache: SnapshotCache,
    csv_path: Path,
    *,
    source_mode: SourceMode | None = None,
) -> CsvSnapshot:
    """Returns updated snapshot, reusing cached data when file is unchanged."""
    mode = source_mode or infer_source_mode(csv_path)
    resolved_path = csv_path
    warning: str | None = None

    if mode == "folder":
        latest_csv = find_latest_csv(csv_path)
        if latest_csv is None:
            if not csv_path.exists():
                warning = f"Folder not found: {csv_path}"
            else:
                warning = f"No CSV files found in folder: {csv_path}"
        else:
            resolved_path = latest_csv

    if warning is not None:
        file_exists = csv_path.exists() if mode == "folder" else False
        if cache.source_key is None:
            cache.source_key = f"{mode}:{csv_path}"
        return _warning_snapshot(cache, warning, file_exists=file_exists)

    source_key = f"{mode}:{resolved_path}"
    if cache.source_key != source_key:
        cache.snapshot = None
        cache.source_key = source_key

    previous_mtime = cache.snapshot.mtime if cache.snapshot else None
    fresh = load_csv_snapshot(csv_path=resolved_path, previous_mtime=previous_mtime)

    if cache.snapshot is None:
        cache.snapshot = fresh
        return fresh

    if (
        fresh.mtime is not None
        and fresh.mtime == cache.snapshot.mtime
        and fresh.data.empty
    ):
        # Unchanged file. Keep last parsed dataset.
        return CsvSnapshot(
            data=cache.snapshot.data,
            mtime=cache.snapshot.mtime,
            file_exists=cache.snapshot.file_exists,
            rows_loaded=cache.snapshot.rows_loaded,
            parse_errors_count=cache.snapshot.parse_errors_count,
            last_update_time=datetime.now(tz=UTC),
            warning=cache.snapshot.warning,
            data_changed=False,
        )

    # If read failed, keep last good data but surface warning.
    if fresh.warning and not cache.snapshot.data.empty:
        cache.snapshot = CsvSnapshot(
            data=cache.snapshot.data,
            mtime=cache.snapshot.mtime,
            file_exists=fresh.file_exists,
            rows_loaded=cache.snapshot.rows_loaded,
            parse_errors_count=cache.snapshot.parse_errors_count,
            last_update_time=fresh.last_update_time,
            warning=fresh.warning,
            data_changed=False,
        )
        return cache.snapshot

    cache.snapshot = fresh
    return fresh
