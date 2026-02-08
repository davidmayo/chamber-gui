"""Shared models and constants for chamber GUI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go


CSV_COLUMNS = {
    "timestamp": "timestamp_utc",
    "cut_id": "cut_id",
    "commanded_tilt": "commanded_tilt_degrees",
    "commanded_pan": "commanded_pan_degrees",
    "commanded_elevation": "commanded_elevation_degrees",
    "commanded_azimuth": "commanded_azimuth_degrees",
    "actual_tilt": "actual_tilt_degrees",
    "actual_pan": "actual_pan_degrees",
    "actual_elevation": "actual_elevation_degrees",
    "actual_azimuth": "actual_azimuth_degrees",
    "center_frequency_hz": "central_frequency_hz",
    "center_power_dbm": "central_frequency_power_dbm",
    "peak_frequency_hz": "peak_power_frequency_hz",
    "peak_power_dbm": "peak_power_dbm",
}

NUMERIC_COLUMNS = (
    CSV_COLUMNS["commanded_tilt"],
    CSV_COLUMNS["commanded_pan"],
    CSV_COLUMNS["commanded_elevation"],
    CSV_COLUMNS["commanded_azimuth"],
    CSV_COLUMNS["actual_tilt"],
    CSV_COLUMNS["actual_pan"],
    CSV_COLUMNS["actual_elevation"],
    CSV_COLUMNS["actual_azimuth"],
    CSV_COLUMNS["center_frequency_hz"],
    CSV_COLUMNS["center_power_dbm"],
    CSV_COLUMNS["peak_frequency_hz"],
    CSV_COLUMNS["peak_power_dbm"],
)

GRAPH_IDS = (
    "az-peak",
    "az-center",
    "el-peak",
    "path-pan-tilt",
    "power-time",
    "pan-peak",
    "pan-center",
    "tilt-peak",
    "path-az-el",
    "freq-time",
    "az-el-peak-heat",
    "az-el-center-heat",
    "pan-tilt-peak-heat",
    "pan-tilt-center-heat",
)

PANEL_IDS = (*GRAPH_IDS, "info")

PANEL_LABELS = {
    "az-peak": "Azimuth Peak Power",
    "az-center": "Azimuth Center Power",
    "el-peak": "Elevation Peak Power",
    "path-pan-tilt": "Path of Travel (Pan/Tilt)",
    "power-time": "Power vs Time",
    "pan-peak": "Pan Peak Power",
    "pan-center": "Pan Center Power",
    "tilt-peak": "Tilt Peak Power",
    "path-az-el": "Path of Travel (Az/El)",
    "freq-time": "Frequency vs Time",
    "az-el-peak-heat": "Az/El Peak Power Heatmap",
    "az-el-center-heat": "Az/El Center Power Heatmap",
    "pan-tilt-peak-heat": "Pan/Tilt Peak Power Heatmap",
    "pan-tilt-center-heat": "Pan/Tilt Center Power Heatmap",
    "info": "Run Info",
}


@dataclass(frozen=True)
class CsvSnapshot:
    """CSV data and metadata from the latest load attempt."""

    data: pd.DataFrame
    mtime: float | None
    file_exists: bool
    rows_loaded: int
    parse_errors_count: int
    last_update_time: datetime | None
    warning: str | None


@dataclass(frozen=True)
class DashboardFigures:
    """All figures required by the dashboard layout."""

    az_peak: go.Figure
    az_center: go.Figure
    el_peak: go.Figure
    path_pan_tilt: go.Figure
    power_time: go.Figure
    pan_peak: go.Figure
    pan_center: go.Figure
    tilt_peak: go.Figure
    path_az_el: go.Figure
    freq_time: go.Figure
    az_el_peak_heat: go.Figure
    az_el_center_heat: go.Figure
    pan_tilt_peak_heat: go.Figure
    pan_tilt_center_heat: go.Figure
