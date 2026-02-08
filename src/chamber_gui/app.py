"""Dash application factory and callback wiring."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, dcc, html

from chamber_gui.data_loader import SnapshotCache, get_latest_snapshot
from chamber_gui.figures import build_dashboard_figures
from chamber_gui.models import CSV_COLUMNS
from chamber_gui.theme import APP_INDEX_TEMPLATE


def create_app(csv_path: Path, poll_interval_ms: int = 1000) -> Dash:
    """Creates and configures the Dash app."""
    app = Dash(__name__, update_title=None)
    app.index_string = APP_INDEX_TEMPLATE
    app.layout = _build_layout(poll_interval_ms=poll_interval_ms)
    cache = SnapshotCache()

    @app.callback(
        Output("az-peak", "figure"),
        Output("az-center", "figure"),
        Output("el-peak", "figure"),
        Output("path-pan-tilt", "figure"),
        Output("power-time", "figure"),
        Output("pan-peak", "figure"),
        Output("pan-center", "figure"),
        Output("tilt-peak", "figure"),
        Output("path-az-el", "figure"),
        Output("freq-time", "figure"),
        Output("az-el-peak-heat", "figure"),
        Output("az-el-center-heat", "figure"),
        Output("pan-tilt-peak-heat", "figure"),
        Output("pan-tilt-center-heat", "figure"),
        Output("info-panel", "children"),
        Input("poll-interval", "n_intervals"),
    )
    def _refresh(_: int):
        snapshot = get_latest_snapshot(cache=cache, csv_path=csv_path)
        figures = build_dashboard_figures(snapshot.data)
        info_panel = _build_info_panel(snapshot=snapshot)
        return (
            figures.az_peak,
            figures.az_center,
            figures.el_peak,
            figures.path_pan_tilt,
            figures.power_time,
            figures.pan_peak,
            figures.pan_center,
            figures.tilt_peak,
            figures.path_az_el,
            figures.freq_time,
            figures.az_el_peak_heat,
            figures.az_el_center_heat,
            figures.pan_tilt_peak_heat,
            figures.pan_tilt_center_heat,
            info_panel,
        )

    return app


def _build_layout(poll_interval_ms: int) -> html.Div:
    return html.Div(
        className="page",
        children=[
            html.H1("Chamber Monitoring", className="title"),
            html.Div(
                className="grid",
                children=[
                    _graph_panel("az-peak"),
                    _graph_panel("az-center"),
                    _graph_panel("el-peak"),
                    _graph_panel("path-pan-tilt"),
                    _graph_panel("power-time"),
                ],
            ),
            html.Div(
                className="grid",
                children=[
                    _graph_panel("pan-peak"),
                    _graph_panel("pan-center"),
                    _graph_panel("tilt-peak"),
                    _graph_panel("path-az-el"),
                    _graph_panel("freq-time"),
                ],
            ),
            html.Div(
                className="grid",
                children=[
                    _graph_panel("az-el-peak-heat"),
                    _graph_panel("az-el-center-heat"),
                    _graph_panel("pan-tilt-peak-heat"),
                    _graph_panel("pan-tilt-center-heat"),
                    html.Div(id="info-panel", className="info"),
                ],
            ),
            dcc.Interval(id="poll-interval", interval=poll_interval_ms, n_intervals=0),
        ],
    )


def _graph_panel(graph_id: str) -> html.Div:
    return html.Div(className="panel", children=[dcc.Graph(id=graph_id, config={"displayModeBar": False})])


def _build_info_panel(snapshot) -> html.Div:
    latest_row = _safe_latest_row(snapshot.data)
    return html.Div(
        children=[
            html.H3("Run Info"),
            html.Ul(
                children=[
                    html.Li(f"File exists: {snapshot.file_exists}"),
                    html.Li(f"Rows loaded: {snapshot.rows_loaded}"),
                    html.Li(f"Parse errors: {snapshot.parse_errors_count}"),
                    html.Li(f"Last refresh: {_format_timestamp(snapshot.last_update_time)}"),
                    html.Li(f"Latest timestamp: {_format_timestamp(latest_row.get(CSV_COLUMNS['timestamp']))}"),
                    html.Li(f"Latest cut: {latest_row.get(CSV_COLUMNS['cut_id'], 'N/A')}"),
                    html.Li(f"Latest peak power (dBm): {_format_number(latest_row.get(CSV_COLUMNS['peak_power_dbm']))}"),
                    html.Li(
                        "Latest center power (dBm): "
                        f"{_format_number(latest_row.get(CSV_COLUMNS['center_power_dbm']))}"
                    ),
                    html.Li(
                        "Latest peak frequency (Hz): "
                        f"{_format_number(latest_row.get(CSV_COLUMNS['peak_frequency_hz']))}"
                    ),
                    html.Li(
                        "Latest center frequency (Hz): "
                        f"{_format_number(latest_row.get(CSV_COLUMNS['center_frequency_hz']))}"
                    ),
                    html.Li(f"Warning: {snapshot.warning or 'None'}"),
                ]
            ),
        ]
    )


def _safe_latest_row(data: pd.DataFrame) -> dict:
    if data.empty:
        return {}
    try:
        return data.iloc[-1].to_dict()
    except Exception:  # pylint: disable=broad-except
        return {}


def _format_timestamp(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is None:
            value = value.tz_localize("UTC")
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _format_number(value: object) -> str:
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{number:.3f}"

