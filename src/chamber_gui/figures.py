"""Figure construction helpers."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.graph_objects as go

from chamber_gui.models import CSV_COLUMNS, DashboardFigures

_LEGEND: dict[str, object] = {
    "yanchor": "bottom",
    "y": 0.0,
    "xanchor": "left",
    "x": 0.0,
    "bgcolor": "rgba(255, 255, 255, 0.5)",
}


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
            fig.add_trace(
                go.Scatterpolar(
                    theta=clean[theta_column],
                    r=clean[r_column],
                    mode="markers",
                    name=str(cut_id),
                )
            )
    else:
        clean = data[[theta_column, r_column]].dropna()
        fig.add_trace(
            go.Scatterpolar(theta=clean[theta_column], r=clean[r_column], mode="markers", name="data")
        )
    tick_vals = list(range(0, 360, 15))
    tick_text = [
        f"{v - 360}°" if v % 45 == 0 and v > 180 else f"{v}°" if v % 45 == 0 else ""
        for v in tick_vals
    ]
    grid_widths = [2 if v % 45 == 0 else 1 for v in tick_vals]
    angularaxis: dict[str, object] = {
        "tickmode": "array",
        "tickvals": tick_vals,
        "ticktext": tick_text,
        "gridwidth": 1,
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
    # Draw thicker grid lines at 45-degree intervals.
    all_r = pd.concat([trace.r if isinstance(trace.r, pd.Series) else pd.Series(trace.r) for trace in fig.data])
    r_bounds = [float(all_r.min()), float(all_r.max())]
    for angle in range(0, 360, 45):
        fig.add_trace(
            go.Scatterpolar(
                r=r_bounds,
                theta=[angle, angle],
                mode="lines",
                line={"color": "lightgray", "width": 2},
                showlegend=False,
                hoverinfo="skip",
            )
        )
    return fig


def _path_figure(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: str,
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
            fig.add_trace(
                go.Scatter(
                    x=clean[x_column],
                    y=clean[y_column],
                    mode="lines+markers",
                    name=str(cut_id),
                )
            )
    else:
        clean = data[[x_column, y_column]].dropna()
        fig.add_trace(go.Scatter(x=clean[x_column], y=clean[y_column], mode="lines+markers", name="data"))

    fig.update_layout(
        title=title,
        margin={"l": 40, "r": 24, "t": 48, "b": 40},
        legend=_LEGEND,
        xaxis={"layer": "below traces"},
        yaxis={"layer": "below traces"},
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
        fig.add_trace(go.Scatter(x=clean[timestamp_column], y=clean[column], mode="lines", name=column))

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
    )
    return fig


def build_dashboard_figures(data: pd.DataFrame) -> DashboardFigures:
    """Builds all dashboard figures from a DataFrame."""
    return DashboardFigures(
        az_peak=_polar_figure(
            data=data,
            theta_column=CSV_COLUMNS["commanded_azimuth"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Azimuth Peak Power",
            compass_orientation=True,
        ),
        az_center=_polar_figure(
            data=data,
            theta_column=CSV_COLUMNS["commanded_azimuth"],
            r_column=CSV_COLUMNS["center_power_dbm"],
            title="Azimuth Center Power",
            compass_orientation=True,
        ),
        el_peak=_polar_figure(
            data=data,
            theta_column=CSV_COLUMNS["commanded_elevation"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Elevation Peak Power",
        ),
        path_pan_tilt=_path_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_pan"],
            y_column=CSV_COLUMNS["commanded_tilt"],
            title="Path of Travel (Pan/Tilt)",
        ),
        power_time=_time_series_figure(
            data=data,
            y_columns=(CSV_COLUMNS["peak_power_dbm"], CSV_COLUMNS["center_power_dbm"]),
            title="Power vs Time",
        ),
        pan_peak=_polar_figure(
            data=data,
            theta_column=CSV_COLUMNS["commanded_pan"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Pan Peak Power",
            compass_orientation=True,
        ),
        pan_center=_polar_figure(
            data=data,
            theta_column=CSV_COLUMNS["commanded_pan"],
            r_column=CSV_COLUMNS["center_power_dbm"],
            title="Pan Center Power",
            compass_orientation=True,
        ),
        tilt_peak=_polar_figure(
            data=data,
            theta_column=CSV_COLUMNS["commanded_tilt"],
            r_column=CSV_COLUMNS["peak_power_dbm"],
            title="Tilt Peak Power",
        ),
        path_az_el=_path_figure(
            data=data,
            x_column=CSV_COLUMNS["commanded_azimuth"],
            y_column=CSV_COLUMNS["commanded_elevation"],
            title="Path of Travel (Az/El)",
        ),
        freq_time=_time_series_figure(
            data=data,
            y_columns=(CSV_COLUMNS["peak_frequency_hz"], CSV_COLUMNS["center_frequency_hz"]),
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

