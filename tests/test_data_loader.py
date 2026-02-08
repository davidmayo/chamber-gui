"""Tests for CSV loading and snapshot cache behavior."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from chamber_gui.data_loader import (
    SnapshotCache,
    get_latest_snapshot,
    load_csv_snapshot,
)
from chamber_gui.models import CSV_COLUMNS


def test_load_csv_snapshot_parses_valid_data(sample_csv_path: Path) -> None:
    snapshot = load_csv_snapshot(csv_path=sample_csv_path, previous_mtime=None)
    assert snapshot.file_exists is True
    assert snapshot.rows_loaded == 4
    assert snapshot.data.empty is False
    assert snapshot.parse_errors_count == 0
    assert snapshot.warning is None
    timestamp_series = snapshot.data[CSV_COLUMNS["timestamp"]]
    assert timestamp_series.dt.tz is not None
    assert str(timestamp_series.dt.tz) == "UTC"


def test_load_csv_snapshot_missing_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "does_not_exist.csv"
    snapshot = load_csv_snapshot(csv_path=csv_path, previous_mtime=None)
    assert snapshot.file_exists is False
    assert snapshot.data.empty is True
    assert snapshot.rows_loaded == 0
    assert "CSV not found" in (snapshot.warning or "")


def test_load_csv_snapshot_returns_empty_data_when_mtime_unchanged(
    sample_csv_path: Path,
) -> None:
    initial = load_csv_snapshot(csv_path=sample_csv_path, previous_mtime=None)
    unchanged = load_csv_snapshot(
        csv_path=sample_csv_path,
        previous_mtime=initial.mtime,
    )
    assert initial.mtime is not None
    assert unchanged.file_exists is True
    assert unchanged.mtime == initial.mtime
    assert unchanged.data.empty is True
    assert unchanged.rows_loaded == 0
    assert unchanged.parse_errors_count == 0
    assert unchanged.warning is None


def test_load_csv_snapshot_surfaces_read_errors(
    monkeypatch,
    sample_csv_path: Path,
) -> None:
    def _raise_read_error(*_, **__):
        raise OSError("read failed for test")

    monkeypatch.setattr("chamber_gui.data_loader.pd.read_csv", _raise_read_error)
    snapshot = load_csv_snapshot(csv_path=sample_csv_path, previous_mtime=None)
    assert snapshot.file_exists is True
    assert snapshot.data.empty is True
    assert snapshot.rows_loaded == 0
    assert "CSV read failed" in (snapshot.warning or "")


def test_load_csv_snapshot_counts_parse_errors(tmp_path: Path) -> None:
    csv_path = tmp_path / "parse_errors.csv"
    bad_data = pd.DataFrame(
        [
            {
                CSV_COLUMNS["timestamp"]: "2026-02-06T18:00:38+00:00",
                CSV_COLUMNS["cut_id"]: "ok",
                CSV_COLUMNS["commanded_tilt"]: 0.0,
                CSV_COLUMNS["commanded_pan"]: 0.0,
                CSV_COLUMNS["commanded_elevation"]: 0.0,
                CSV_COLUMNS["commanded_azimuth"]: 0.0,
                CSV_COLUMNS["actual_tilt"]: 0.0,
                CSV_COLUMNS["actual_pan"]: 0.0,
                CSV_COLUMNS["actual_elevation"]: 0.0,
                CSV_COLUMNS["actual_azimuth"]: 0.0,
                CSV_COLUMNS["center_frequency_hz"]: 10_000_000_000.0,
                CSV_COLUMNS["center_power_dbm"]: -20.0,
                CSV_COLUMNS["peak_frequency_hz"]: 10_001_000_000.0,
                CSV_COLUMNS["peak_power_dbm"]: -18.0,
            },
            {
                CSV_COLUMNS["timestamp"]: "invalid-time",
                CSV_COLUMNS["cut_id"]: "bad",
                CSV_COLUMNS["commanded_tilt"]: 1.0,
                CSV_COLUMNS["commanded_pan"]: "oops",
                CSV_COLUMNS["commanded_elevation"]: 1.0,
                CSV_COLUMNS["commanded_azimuth"]: 1.0,
                CSV_COLUMNS["actual_tilt"]: 1.0,
                CSV_COLUMNS["actual_pan"]: 1.0,
                CSV_COLUMNS["actual_elevation"]: 1.0,
                CSV_COLUMNS["actual_azimuth"]: 1.0,
                CSV_COLUMNS["center_frequency_hz"]: 10_000_000_000.0,
                CSV_COLUMNS["center_power_dbm"]: -20.0,
                CSV_COLUMNS["peak_frequency_hz"]: 10_001_000_000.0,
                CSV_COLUMNS["peak_power_dbm"]: "bad-number",
            },
        ]
    )
    bad_data.to_csv(csv_path, index=False)

    snapshot = load_csv_snapshot(csv_path=csv_path, previous_mtime=None)
    assert snapshot.parse_errors_count == 3
    assert pd.isna(snapshot.data.loc[1, CSV_COLUMNS["timestamp"]])
    assert pd.isna(snapshot.data.loc[1, CSV_COLUMNS["commanded_pan"]])
    assert pd.isna(snapshot.data.loc[1, CSV_COLUMNS["peak_power_dbm"]])


def test_get_latest_snapshot_reuses_cached_data_when_file_unchanged(
    sample_csv_path: Path,
) -> None:
    cache = SnapshotCache()
    first = get_latest_snapshot(cache=cache, csv_path=sample_csv_path)
    second = get_latest_snapshot(cache=cache, csv_path=sample_csv_path)
    assert first.data.empty is False
    assert second.data.empty is False
    assert len(second.data.index) == len(first.data.index)
    assert second.rows_loaded == first.rows_loaded
    assert second.parse_errors_count == first.parse_errors_count


def test_get_latest_snapshot_keeps_last_good_data_when_read_fails(
    monkeypatch,
    sample_csv_path: Path,
) -> None:
    cache = SnapshotCache()
    first = get_latest_snapshot(cache=cache, csv_path=sample_csv_path)
    old_mtime = sample_csv_path.stat().st_mtime
    os.utime(sample_csv_path, (old_mtime + 5, old_mtime + 5))

    def _raise_read_error(*_, **__):
        raise OSError("boom")

    monkeypatch.setattr("chamber_gui.data_loader.pd.read_csv", _raise_read_error)
    second = get_latest_snapshot(cache=cache, csv_path=sample_csv_path)
    assert first.data.empty is False
    assert second.data.empty is False
    assert len(second.data.index) == len(first.data.index)
    assert second.rows_loaded == first.rows_loaded
    assert second.warning is not None
    assert "CSV read failed" in second.warning
