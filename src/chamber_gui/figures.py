"""Figure construction helpers."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.graph_objects as go

import plotly.colors

from chamber_gui.models import (
    CSV_COLUMNS,
    DashboardFigures,
    HORIZONTAL_POLAR_IDS,
    classify_cut,
)


def _degree_axis(extra: dict[str, object] | None = None) -> dict[str, object]:
    """Returns a cartesian axis config with gridlines and labels at 15-deg intervals."""
    tick_vals = list(range(-180, 181, 15))
    tick_text = [f"{v}°" if v % 45 == 0 else "" for v in tick_vals]
    axis: dict[str, object] = {
        "tickmode": "array",
        "tickvals": tick_vals,
        "ticktext": tick_text,
        "layer": "below traces",
    }
    if extra:
        axis.update(extra)
    return axis


_LEGEND: dict[str, object] = {
    "yanchor": "bottom",
    "y": 0.0,
    "xanchor": "left",
    "x": 0.0,
    "bgcolor": "rgba(255, 255, 255, 0.5)",
}


def build_cut_color_map(cut_ids: list[str]) -> dict[str, str]:
    """Returns a mapping of cut_id to color, consistent across all graphs."""
    palette = plotly.colors.qualitative.Plotly
    sorted_ids = sorted(set(cut_ids))
    return {
        cut_id: palette[i % len(palette)]
        for i, cut_id in enumerate(sorted_ids)
    }


def _filter_polar_data(
    data: pd.DataFrame,
    graph_id: str,
    cut_mode: str,
) -> pd.DataFrame:
    """Filters data for a polar graph based on cut mode."""
    if cut_mode == "all":
        return data

    cut_col = CSV_COLUMNS["cut_id"]
    if cut_col not in data.columns or data.empty:
        return data

    is_horizontal_graph = graph_id in HORIZONTAL_POLAR_IDS
    keep_cuts = []
    for cut_id in data[cut_col].dropna().unique():
        classification = classify_cut(str(cut_id))
        if classification == "horizontal" and is_horizontal_graph:
            keep_cuts.append(cut_id)
        elif classification == "vertical" and not is_horizontal_graph:
            keep_cuts.append(cut_id)
        elif classification == "indeterminate" and cut_mode == "auto-include":
            keep_cuts.append(cut_id)
    return data[data[cut_col].isin(keep_cuts)]


def _empty_figure(title: str, message: str = "No data available") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
            }
        ],
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def _polar_figure(
    data: pd.DataFrame,
    theta_column: str,
    r_column: str,
    title: str,
    compass_orientation: bool = False,
    color_map: dict[str, str] | None = None,
) -> go.Figure:
    required = {theta_column, r_column}
    if data.empty or not required.issubset(set(data.columns)):
        return _empty_figure(title)

    fig = go.Figure()
    if CSV_COLUMNS["cut_id"] in data.columns:
        for cut_id, subset in data.groupby(CSV_COLUMNS["cut_id"], dropna=False):
            clean = subset[[theta_column, r_column]].dropna()
            if clean.empty:
                continue
            marker: dict[str, object] = {}
            if color_map and str(cut_id) in color_map:
                marker["color"] = color_map[str(cut_id)]
            fig.add_trace(
                go.Scatterpolar(
                    theta=clean[theta_column],
                    r=clean[r_column],
                    mode="markers",
                    name=str(cut_id),
                    marker=marker,
                )
            )
    else:
        clean = data[[theta_column, r_column]].dropna()
        fig.add_trace(
            go.Scatterpolar(
                theta=clean[theta_column],
                r=clean[r_column],
                mode="markers",
                name="data",
            )
        )

    tick_vals = list(range(0, 360, 15))
    tick_text = [
        f"{v - 360}°" if v % 45 == 0 and v > 180 else f"{v}°" if v % 45 == 0 else ""
        for v in tick_vals
    ]
    angularaxis: dict[str, object] = {
        "tickmode": "array",
        "tickvals": tick_vals,
        "ticktext": tick_text,
        "layer": "below traces",
    }
    if compass_orientation:
        angularaxis["rotation"] = 90
        angularaxis["direction"] = "clockwise"

    fig.update_layout(
        title=title,
        margin={"l": 24, "r": 24, "t": 48, "b": 24},
        polar={
            "angularaxis": angularaxis,
            "radialaxis": {"rangemode": "normal", "layer": "below traces"},
        },
        legend=_LEGEND,
    )
    return fig


def _path_figure(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: str,
    color_map: dict[str, str] | None = None,
) -> go.Figure:
    required = {x_column, y_column}
    if data.empty or not required.issubset(set(data.columns)):
        return _empty_figure(title)

    fig = go.Figure()
    if CSV_COLUMNS["cut_id"] in data.columns:
        for cut_id, subset in data.groupby(CSV_COLUMNS["cut_id"], dropna=False):
            clean = subset[[x_column, y_column]].dropna()
            if clean.empty:
                continue
            line: dict[str, object] = {}
            marker: dict[str, object] = {}
            if color_map and str(cut_id) in color_map:
                line["color"] = color_map[str(cut_id)]
                marker["color"] = color_map[str(cut_id)]
            fig.add_trace(
                go.Scatter(
                    x=clean[x_column],
                    y=clean[y_column],
                    mode="lines+markers",
                    name=str(cut_id),
                    line=line,
                    marker=marker,
                )
            )
    else:
        clean = data[[x_column, y_column]].dropna()
        fig.add_trace(
            go.Scatter(
                x=clean[x_column], y=clean[y_column], mode="lines+markers", name="data"
            )
        )

    fig.update_layout(
        title=title,
        margin={"l": 40, "r": 24, "t": 48, "b": 40},
        legend=_LEGEND,
        xaxis=_degree_axis(),
        yaxis=_degree_axis({"scaleanchor": "x"}),
    )
    return fig


def _time_series_figure(
    data: pd.DataFrame,
    y_columns: Iterable[str],
    title: str,
) -> go.Figure:
    timestamp_column = CSV_COLUMNS["timestamp"]
    if data.empty or timestamp_column not in data.columns:
        return _empty_figure(title)

    fig = go.Figure()
    for column in y_columns:
        if column not in data.columns:
            continue
        clean = data[[timestamp_column, column]].dropna()
        if clean.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=clean[timestamp_column], y=clean[column], mode="lines", name=column
            )
        )

    if not fig.data:
        return _empty_figure(title)

    fig.update_layout(
        title=title,
        margin={"l": 48, "r": 24, "t": 48, "b": 40},
        legend=_LEGEND,
        xaxis={"layer": "below traces"},
        yaxis={"layer": "below traces"},
    )
    return fig


def _heatmap_figure(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    z_column: str,
    title: str,
) -> go.Figure:
    required = {x_column, y_column, z_column}
    if data.empty or not required.issubset(set(data.columns)):
        return _empty_figure(title)

    clean = data[[x_column, y_column, z_column]].dropna()
    if clean.empty:
        return _empty_figure(title)

    bin_size = 3
    binned = clean.copy()
    binned[x_column] = (binned[x_column] / bin_size).round(0) * bin_size
    binned[y_column] = (binned[y_column] / bin_size).round(0) * bin_size
    pivot = binned.pivot_table(
        index=y_column,
        columns=x_column,
        values=z_column,
        aggfunc="mean",
    )
    if pivot.empty:
        return _empty_figure(title)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.to_list(),
            y=pivot.index.to_list(),
            showscale=False,
            connectgaps=False,
        )
    )
    fig.update_layout(
        title=title,
        margin={"l": 48, "r": 24, "t": 48, "b": 40},
        xaxis=_degree_axis(),
        yaxis=_degree_axis({"scaleanchor": "x"}),
    )
    return fig


def build_dashboard_figures(
    data: pd.DataFrame,
    cut_mode: str = "auto-include",
) -> DashboardFigures:
    """Builds all dashboard figures from a DataFrame."""
    cut_col = CSV_COLUMNS["cut_id"]
    if cut_col in data.columns and not data.empty:
        all_cut_ids = [str(c) for c in data[cut_col].dropna().unique()]
        color_map = build_cut_color_map(all_cut_ids)
    else:
        color_map = {}

    def polar_data(graph_id: str) -> pd.DataFrame:
        return _filter_polar_data(data, graph_id, cut_mode)

    return DashboardFigures(
        az_peak=_polar_figure(
            data=polar_data("az-peak"),
            theta_column=CSV_COLUMNS["commanded_azimuth"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Azimuth Peak Power",
            compass_orientation=True,
            color_map=color_map,
        ),
        az_center=_polar_figure(
            data=polar_data("az-center"),
            theta_column=CSV_COLUMNS["commanded_azimuth"],
            r_column=CSV_COLUMNS["center_power_dbm"],
            title="Azimuth Center Power",
            compass_orientation=True,
            color_map=color_map,
        ),
        el_peak=_polar_figure(
            data=polar_data("el-peak"),
            theta_column=CSV_COLUMNS["commanded_elevation"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Elevation Peak Power",
            color_map=color_map,
        ),
        path_pan_tilt=_path_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_pan"],
            y_column=CSV_COLUMNS["commanded_tilt"],
            title="Path of Travel (Pan/Tilt)",
            color_map=color_map,
        ),
        power_time=_time_series_figure(
            data=data,
            y_columns=(CSV_COLUMNS["peak_power_dbm"], CSV_COLUMNS["center_power_dbm"]),
            title="Power vs Time",
        ),
        pan_peak=_polar_figure(
            data=polar_data("pan-peak"),
            theta_column=CSV_COLUMNS["commanded_pan"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Pan Peak Power",
            compass_orientation=True,
            color_map=color_map,
        ),
        pan_center=_polar_figure(
            data=polar_data("pan-center"),
            theta_column=CSV_COLUMNS["commanded_pan"],
            r_column=CSV_COLUMNS["center_power_dbm"],
            title="Pan Center Power",
            compass_orientation=True,
            color_map=color_map,
        ),
        tilt_peak=_polar_figure(
            data=polar_data("tilt-peak"),
            theta_column=CSV_COLUMNS["commanded_tilt"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Tilt Peak Power",
            color_map=color_map,
        ),
        path_az_el=_path_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_azimuth"],
            y_column=CSV_COLUMNS["commanded_elevation"],
            title="Path of Travel (Az/El)",
            color_map=color_map,
        ),
        freq_time=_time_series_figure(
            data=data,
            y_columns=(
                CSV_COLUMNS["peak_frequency_hz"],
                CSV_COLUMNS["center_frequency_hz"],
            ),
            title="Frequency vs Time",
        ),
        az_el_peak_heat=_heatmap_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_azimuth"],
            y_column=CSV_COLUMNS["commanded_elevation"],
            z_column=CSV_COLUMNS["peak_power_dbm"],
            title="Az/El Peak Power Heatmap",
        ),
        az_el_center_heat=_heatmap_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_azimuth"],
            y_column=CSV_COLUMNS["commanded_elevation"],
            z_column=CSV_COLUMNS["center_power_dbm"],
            title="Az/El Center Power Heatmap",
        ),
        pan_tilt_peak_heat=_heatmap_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_pan"],
            y_column=CSV_COLUMNS["commanded_tilt"],
            z_column=CSV_COLUMNS["peak_power_dbm"],
            title="Pan/Tilt Peak Power Heatmap",
        ),
        pan_tilt_center_heat=_heatmap_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_pan"],
            y_column=CSV_COLUMNS["commanded_tilt"],
            z_column=CSV_COLUMNS["center_power_dbm"],
            title="Pan/Tilt Center Power Heatmap",
        ),
    )
