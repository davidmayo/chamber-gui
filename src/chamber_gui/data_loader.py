"""CSV loading and refresh cache utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from chamber_gui.models import CSV_COLUMNS, CsvSnapshot, NUMERIC_COLUMNS


@dataclass
class SnapshotCache:
    """In-memory cache to avoid reloading unchanged CSV data."""

    snapshot: CsvSnapshot | None = None


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
    )


def get_latest_snapshot(cache: SnapshotCache, csv_path: Path) -> CsvSnapshot:
    """Returns updated snapshot, reusing cached data when file is unchanged."""
    previous_mtime = cache.snapshot.mtime if cache.snapshot else None
    fresh = load_csv_snapshot(csv_path=csv_path, previous_mtime=previous_mtime)

    if cache.snapshot is None:
        cache.snapshot = fresh
        return fresh

    if fresh.mtime is not None and fresh.mtime == cache.snapshot.mtime and fresh.data.empty:
        # Unchanged file. Keep last parsed dataset.
        return CsvSnapshot(
            data=cache.snapshot.data,
            mtime=cache.snapshot.mtime,
            file_exists=cache.snapshot.file_exists,
            rows_loaded=cache.snapshot.rows_loaded,
            parse_errors_count=cache.snapshot.parse_errors_count,
            last_update_time=datetime.now(tz=UTC),
            warning=cache.snapshot.warning,
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
        )
        return cache.snapshot

    cache.snapshot = fresh
    return fresh

