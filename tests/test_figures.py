"""Tests for dashboard figure builders."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chamber_gui.figures import build_dashboard_figures


def test_build_dashboard_figures_with_sample_data() -> None:
    df = pd.read_csv(Path("sample_data") / "run_data.csv")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    figures = build_dashboard_figures(df)
    assert figures.az_peak is not None
    assert figures.power_time is not None
    assert len(figures.power_time.data) >= 1
    assert figures.az_el_peak_heat is not None


def test_polar_compass_orientation_applies_to_azimuth_and_pan_only() -> None:
    df = pd.read_csv(Path("sample_data") / "run_data.csv")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    figures = build_dashboard_figures(df)

    assert figures.az_peak.layout.polar.angularaxis.rotation == 90
    assert figures.az_peak.layout.polar.angularaxis.direction == "clockwise"
    assert figures.pan_peak.layout.polar.angularaxis.rotation == 90
    assert figures.pan_peak.layout.polar.angularaxis.direction == "clockwise"

    assert figures.el_peak.layout.polar.angularaxis.rotation is None
    assert figures.el_peak.layout.polar.angularaxis.direction is None
    assert figures.tilt_peak.layout.polar.angularaxis.rotation is None
    assert figures.tilt_peak.layout.polar.angularaxis.direction is None

    for fig in (figures.az_peak, figures.el_peak, figures.pan_peak, figures.tilt_peak):
        assert fig.layout.polar.angularaxis.tickmode == "array"
        assert len(fig.layout.polar.angularaxis.tickvals) == 24  # every 15 degrees
        labeled = [t for t in fig.layout.polar.angularaxis.ticktext if t]
        assert len(labeled) == 8  # labels every 45 degrees


def test_build_dashboard_figures_with_empty_data() -> None:
    figures = build_dashboard_figures(pd.DataFrame())
    assert len(figures.az_peak.data) == 0
    assert len(figures.power_time.data) == 0
    assert len(figures.pan_tilt_center_heat.data) == 0
