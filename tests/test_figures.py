"""Tests for dashboard figure builders."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chamber_gui.figures import build_cut_color_map, build_dashboard_figures
from chamber_gui.models import classify_cut


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


def test_classify_cut_horizontal() -> None:
    assert classify_cut("coarse-az") == "horizontal"
    assert classify_cut("fine-pan") == "horizontal"
    assert classify_cut("horizontal-sweep") == "horizontal"


def test_classify_cut_vertical() -> None:
    assert classify_cut("coarse-el") == "vertical"
    assert classify_cut("tilt-fine") == "vertical"
    assert classify_cut("vertical-sweep") == "vertical"


def test_classify_cut_indeterminate() -> None:
    assert classify_cut("diagonal") == "indeterminate"
    assert classify_cut("random-sweep") == "indeterminate"
    assert classify_cut("az-el-combined") == "indeterminate"


def test_build_cut_color_map_consistent() -> None:
    map1 = build_cut_color_map(["coarse-az", "coarse-el", "fine-az"])
    map2 = build_cut_color_map(["fine-az", "coarse-el", "coarse-az"])
    assert map1 == map2
    assert len(map1) == 3


def test_polar_filtering_auto_include() -> None:
    df = pd.read_csv(Path("sample_data") / "run_data.csv")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    figures = build_dashboard_figures(df, cut_mode="auto-include")

    az_trace_names = [t.name for t in figures.az_peak.data]
    assert "coarse-az" in az_trace_names
    assert "coarse-el" not in az_trace_names

    el_trace_names = [t.name for t in figures.el_peak.data]
    assert "coarse-el" in el_trace_names
    assert "coarse-az" not in el_trace_names


def test_polar_filtering_all_mode() -> None:
    df = pd.read_csv(Path("sample_data") / "run_data.csv")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    figures = build_dashboard_figures(df, cut_mode="all")

    az_trace_names = [t.name for t in figures.az_peak.data]
    assert "coarse-az" in az_trace_names
    assert "coarse-el" in az_trace_names


def test_color_consistency_across_graphs() -> None:
    df = pd.read_csv(Path("sample_data") / "run_data.csv")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    figures = build_dashboard_figures(df, cut_mode="all")

    def get_trace_color(fig, trace_name):
        for t in fig.data:
            if t.name == trace_name:
                return t.marker.color
        return None

    az_peak_color = get_trace_color(figures.az_peak, "coarse-az")
    pan_peak_color = get_trace_color(figures.pan_peak, "coarse-az")
    assert az_peak_color is not None
    assert az_peak_color == pan_peak_color


def test_non_polar_graphs_unaffected_by_cut_mode() -> None:
    df = pd.read_csv(Path("sample_data") / "run_data.csv")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    figs_all = build_dashboard_figures(df, cut_mode="all")
    figs_auto = build_dashboard_figures(df, cut_mode="auto-include")
    assert len(figs_all.power_time.data) == len(figs_auto.power_time.data)
    assert len(figs_all.az_el_peak_heat.data) == len(figs_auto.az_el_peak_heat.data)
