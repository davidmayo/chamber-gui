"""Tests for CSV loading and snapshot cache behavior."""

from __future__ import annotations

from pathlib import Path

from chamber_gui.data_loader import (
    SnapshotCache,
    get_latest_snapshot,
    load_csv_snapshot,
)


def test_load_csv_snapshot_valid_sample() -> None:
    csv_path = Path("sample_data") / "run_data.csv"
    snapshot = load_csv_snapshot(csv_path=csv_path, previous_mtime=None)
    assert snapshot.file_exists is True
    assert snapshot.rows_loaded > 0
    assert snapshot.data.empty is False


def test_load_csv_snapshot_missing_file() -> None:
    csv_path = Path("sample_data") / "does_not_exist.csv"
    snapshot = load_csv_snapshot(csv_path=csv_path, previous_mtime=None)
    assert snapshot.file_exists is False
    assert snapshot.data.empty is True
    assert snapshot.warning is not None


def test_get_latest_snapshot_uses_cache_when_unchanged() -> None:
    csv_path = Path("sample_data") / "run_data.csv"
    cache = SnapshotCache()
    first = get_latest_snapshot(cache=cache, csv_path=csv_path)
    second = get_latest_snapshot(cache=cache, csv_path=csv_path)
    assert first.data.empty is False
    assert second.data.empty is False
    assert len(second.data.index) == len(first.data.index)
