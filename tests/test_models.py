"""Tests for shared constants and dataclass contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objects as go
import pytest

from chamber_gui.models import (
    CSV_COLUMNS,
    GRAPH_IDS,
    NUMERIC_COLUMNS,
    PANEL_IDS,
    PANEL_LABELS,
    CsvSnapshot,
    DashboardFigures,
)


def test_graph_panel_constants_are_consistent() -> None:
    assert PANEL_IDS == (*GRAPH_IDS, "info")
    assert len(set(GRAPH_IDS)) == len(GRAPH_IDS)
    assert len(set(PANEL_IDS)) == len(PANEL_IDS)
    assert all(panel_id in PANEL_LABELS for panel_id in PANEL_IDS)


def test_numeric_columns_are_defined_in_csv_columns() -> None:
    csv_values = set(CSV_COLUMNS.values())
    assert set(NUMERIC_COLUMNS).issubset(csv_values)
    assert CSV_COLUMNS["timestamp"] not in NUMERIC_COLUMNS


def test_csv_columns_match_lems_schema() -> None:
    assert CSV_COLUMNS == {
        "timestamp": "timestamp",
        "cut_id": "cut_id",
        "commanded_tilt": "commanded_tilt",
        "commanded_pan": "commanded_pan",
        "commanded_elevation": "commanded_elevation",
        "commanded_azimuth": "commanded_azimuth",
        "actual_tilt": "actual_tilt",
        "actual_pan": "actual_pan",
        "actual_elevation": "actual_elevation",
        "actual_azimuth": "actual_azimuth",
        "center_frequency_hz": "center_frequency",
        "center_power_dbm": "center_amplitude",
        "peak_frequency_hz": "peak_frequency",
        "peak_power_dbm": "peak_amplitude",
    }


def test_csv_snapshot_is_frozen_dataclass() -> None:
    snapshot = CsvSnapshot(
        data=pd.DataFrame(),
        mtime=None,
        file_exists=False,
        rows_loaded=0,
        parse_errors_count=0,
        last_update_time=datetime(2026, 2, 8, tzinfo=UTC),
        warning=None,
        data_changed=False,
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.rows_loaded = 1  # type: ignore[misc]


def test_dashboard_figures_is_frozen_dataclass() -> None:
    figure = go.Figure()
    dashboard_figures = DashboardFigures(
        az_peak=figure,
        az_center=figure,
        el_peak=figure,
        el_center=figure,
        path_pan_tilt=figure,
        power_time=figure,
        pan_peak=figure,
        pan_center=figure,
        tilt_peak=figure,
        tilt_center=figure,
        path_az_el=figure,
        freq_time=figure,
        az_el_peak_heat=figure,
        az_el_center_heat=figure,
        pan_tilt_peak_heat=figure,
        pan_tilt_center_heat=figure,
    )
    with pytest.raises(FrozenInstanceError):
        dashboard_figures.az_peak = go.Figure()  # type: ignore[misc]
