"""Tests for dashboard figure builders."""

from __future__ import annotations

from dataclasses import fields

import pandas as pd

from chamber_gui.figures import (
    _degree_axis,
    _empty_figure,
    _heatmap_figure,
    build_dashboard_figures,
)
from chamber_gui.models import CSV_COLUMNS, DashboardFigures


def _parsed_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    parsed = data.copy()
    parsed[CSV_COLUMNS["timestamp"]] = pd.to_datetime(
        parsed[CSV_COLUMNS["timestamp"]],
        errors="coerce",
        utc=True,
    )
    return parsed


def test_build_dashboard_figures_returns_all_dashboard_fields(
    sample_rows_df: pd.DataFrame,
) -> None:
    figures = build_dashboard_figures(_parsed_dataframe(sample_rows_df))
    for field in fields(DashboardFigures):
        assert getattr(figures, field.name) is not None


def test_polar_compass_orientation_applies_to_azimuth_and_pan_only(
    sample_rows_df: pd.DataFrame,
) -> None:
    figures = build_dashboard_figures(_parsed_dataframe(sample_rows_df))
    assert figures.az_peak.layout.polar.angularaxis.rotation == 90
    assert figures.az_peak.layout.polar.angularaxis.direction == "clockwise"
    assert figures.pan_peak.layout.polar.angularaxis.rotation == 90
    assert figures.pan_peak.layout.polar.angularaxis.direction == "clockwise"
    assert figures.el_peak.layout.polar.angularaxis.rotation is None
    assert figures.el_peak.layout.polar.angularaxis.direction is None
    assert figures.tilt_peak.layout.polar.angularaxis.rotation is None
    assert figures.tilt_peak.layout.polar.angularaxis.direction is None


def test_cut_id_groups_create_multiple_traces(sample_rows_df: pd.DataFrame) -> None:
    figures = build_dashboard_figures(_parsed_dataframe(sample_rows_df))
    assert len(figures.az_peak.data) == 2
    assert len(figures.path_pan_tilt.data) == 2
    assert {trace.name for trace in figures.az_peak.data} == {"coarse-az", "fine-pan"}


def test_time_series_uses_expected_series_names(sample_rows_df: pd.DataFrame) -> None:
    figures = build_dashboard_figures(_parsed_dataframe(sample_rows_df))
    assert len(figures.power_time.data) == 2
    assert [trace.name for trace in figures.power_time.data] == [
        CSV_COLUMNS["peak_power_dbm"],
        CSV_COLUMNS["center_power_dbm"],
    ]
    assert len(figures.freq_time.data) == 2


def test_build_dashboard_figures_with_empty_data_returns_empty_figure_set() -> None:
    figures = build_dashboard_figures(pd.DataFrame())
    assert len(figures.az_peak.data) == 0
    assert len(figures.power_time.data) == 0
    assert len(figures.pan_tilt_center_heat.data) == 0
    assert figures.az_peak.layout.annotations[0]["text"] == "No data available"


def test_missing_required_columns_produce_empty_figures(
    sample_rows_df: pd.DataFrame,
) -> None:
    data = _parsed_dataframe(sample_rows_df).drop(
        columns=[CSV_COLUMNS["commanded_azimuth"]]
    )
    figures = build_dashboard_figures(data)
    assert len(figures.az_peak.data) == 0
    assert figures.az_peak.layout.annotations[0]["text"] == "No data available"


def test_time_series_with_only_nans_is_empty(sample_rows_df: pd.DataFrame) -> None:
    data = _parsed_dataframe(sample_rows_df)
    data[CSV_COLUMNS["peak_power_dbm"]] = float("nan")
    data[CSV_COLUMNS["center_power_dbm"]] = float("nan")
    figures = build_dashboard_figures(data)
    assert len(figures.power_time.data) == 0
    assert figures.power_time.layout.annotations[0]["text"] == "No data available"


def test_heatmap_averages_rows_after_binning() -> None:
    data = pd.DataFrame(
        {
            CSV_COLUMNS["commanded_azimuth"]: [1.0, 2.0, 4.0],
            CSV_COLUMNS["commanded_elevation"]: [1.0, 2.0, 4.0],
            CSV_COLUMNS["peak_power_dbm"]: [10.0, 20.0, 40.0],
        }
    )
    figure = _heatmap_figure(
        data=data,
        x_column=CSV_COLUMNS["commanded_azimuth"],
        y_column=CSV_COLUMNS["commanded_elevation"],
        z_column=CSV_COLUMNS["peak_power_dbm"],
        title="Heat",
    )
    assert len(figure.data) == 1
    assert list(figure.data[0]["x"]) == [0.0, 3.0]
    assert list(figure.data[0]["y"]) == [0.0, 3.0]
    z_values = figure.data[0]["z"]
    assert z_values[0][0] == 10.0
    assert z_values[1][1] == 30.0


def test_degree_axis_uses_15_degree_ticks_with_45_degree_labels() -> None:
    axis = _degree_axis()
    assert axis["tickmode"] == "array"
    assert len(axis["tickvals"]) == 25
    labeled_ticks = [tick for tick in axis["ticktext"] if tick]
    assert labeled_ticks[0] == "-180°"
    assert labeled_ticks[-1] == "180°"


def test_empty_figure_contains_message_annotation() -> None:
    figure = _empty_figure("Empty Figure", message="Nothing here")
    assert len(figure.data) == 0
    assert figure.layout.title.text == "Empty Figure"
    assert figure.layout.annotations[0]["text"] == "Nothing here"


def test_polar_figure_hpbw_disabled_has_no_overlay_traces(
    sample_rows_df: pd.DataFrame,
) -> None:
    """With hpbw_enabled=False (default), no overlay traces are added."""
    figures = build_dashboard_figures(_parsed_dataframe(sample_rows_df))
    # az_peak has 2 cuts → 2 data traces, no overlays.
    assert len(figures.az_peak.data) == 2
    assert all(trace.mode == "markers" for trace in figures.az_peak.data)


def test_polar_figure_hpbw_enabled_adds_overlay_traces(
    sample_rows_df: pd.DataFrame,
) -> None:
    """With hpbw_enabled=True, 5 overlay traces are added to polar figures."""
    figures = build_dashboard_figures(
        _parsed_dataframe(sample_rows_df), hpbw_enabled=True
    )
    # az_peak: 5 HPBW overlays + 2 data traces = 7.
    assert len(figures.az_peak.data) == 7
    hpbw_traces = figures.az_peak.data[:5]
    assert all(trace.mode == "lines" for trace in hpbw_traces)
    # The first overlay trace carries the HPBW legend label.
    assert "HPBW:" in hpbw_traces[0].name


def test_hpbw_enabled_does_not_affect_non_polar_figures(
    sample_rows_df: pd.DataFrame,
) -> None:
    """Non-polar figures have no HPBW overlays regardless of the toggle."""
    figures_off = build_dashboard_figures(_parsed_dataframe(sample_rows_df))
    figures_on = build_dashboard_figures(
        _parsed_dataframe(sample_rows_df), hpbw_enabled=True
    )
    assert len(figures_on.path_pan_tilt.data) == len(figures_off.path_pan_tilt.data)
    assert len(figures_on.power_time.data) == len(figures_off.power_time.data)
    assert len(figures_on.az_el_peak_heat.data) == len(figures_off.az_el_peak_heat.data)
