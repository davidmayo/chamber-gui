"""Dash application factory and callback wiring."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import dash
from dash import Dash, Input, Output, State, clientside_callback, ctx, dcc, html

from chamber_gui.data_loader import SnapshotCache, get_latest_snapshot
from chamber_gui.figures import build_dashboard_figures
from chamber_gui.models import (
    CSV_COLUMNS,
    CUT_MODES,
    DEFAULT_CUT_MODE,
    GRAPH_IDS,
    PANEL_IDS,
    PANEL_LABELS,
)
from chamber_gui.theme import APP_INDEX_TEMPLATE


def _default_config() -> list[dict]:
    return [{"id": pid, "enabled": True, "order": i} for i, pid in enumerate(PANEL_IDS)]


def _normalize_config(data: object) -> list[dict]:
    """Validate/fill stored config; always returns one entry per PANEL_ID sorted by order."""
    if not isinstance(data, list):
        return _default_config()
    result = []
    for item in data:
        if isinstance(item, dict) and item.get("id") in set(PANEL_IDS):
            result.append(
                {
                    "id": item["id"],
                    "enabled": bool(item.get("enabled", True)),
                    "order": int(item.get("order", 0)),
                }
            )
    existing_ids = {item["id"] for item in result}
    next_order = max((item["order"] for item in result), default=-1) + 1
    for pid in PANEL_IDS:
        if pid not in existing_ids:
            result.append({"id": pid, "enabled": True, "order": next_order})
            next_order += 1
    result.sort(key=lambda x: x["order"])
    return result


_PANEL_GROUPS = [
    ("all", "All", list(PANEL_IDS)),
    (
        "az-el",
        "Az/El",
        [
            "az-peak",
            "az-center",
            "el-peak",
            "az-el-peak-heat",
            "az-el-center-heat",
            "path-az-el",
        ],
    ),
    (
        "pan-tilt",
        "Pan/Tilt",
        [
            "pan-peak",
            "pan-center",
            "tilt-peak",
            "pan-tilt-peak-heat",
            "pan-tilt-center-heat",
            "path-pan-tilt",
        ],
    ),
    (
        "peak",
        "Peak Power",
        [
            "az-peak",
            "el-peak",
            "pan-peak",
            "tilt-peak",
            "az-el-peak-heat",
            "pan-tilt-peak-heat",
            "power-time",
            "freq-time",
        ],
    ),
    (
        "center",
        "Center Power",
        ["az-center", "pan-center", "az-el-center-heat", "pan-tilt-center-heat"],
    ),
]


def _build_modal_groups(config: list[dict]) -> html.Div:
    enabled_ids = {item["id"] for item in config if item["enabled"]}
    items = []
    for gid, label, members in _PANEL_GROUPS:
        on_count = sum(1 for m in members if m in enabled_ids)
        if on_count == len(members):
            cb_class, cb_text = "modal-checkbox modal-checkbox--on", "✓"
        elif on_count == 0:
            cb_class, cb_text = "modal-checkbox", "✓"
        else:
            cb_class, cb_text = "modal-checkbox modal-checkbox--mixed", "−"
        items.append(
            html.Div(
                className="group-item",
                **{"data-group-id": gid, "data-members": ",".join(members)},
                children=[
                    html.Span(cb_text, className=cb_class),
                    html.Span(label, className="group-label"),
                ],
            )
        )
    return html.Div(className="modal-groups", children=items)


def _build_modal_items(config: list[dict]) -> list:
    items = []
    for item in config:
        pid = item["id"]
        label = PANEL_LABELS.get(pid, pid)
        cb_class = (
            "modal-checkbox modal-checkbox--on" if item["enabled"] else "modal-checkbox"
        )
        items.append(
            html.Div(
                className="modal-item",
                **{"data-panel-id": pid},
                children=[
                    html.Span("⠿", className="drag-handle"),
                    html.Span("✓", className=cb_class, **{"data-panel-id": pid}),
                    html.Span(label, className="panel-label"),
                ],
            )
        )
    return items


def _build_cut_mode_selector(current_mode: str) -> html.Div:
    """Builds the polar cut mode radio selector for the modal."""
    return html.Div(
        className="modal-cut-mode",
        children=[
            html.H4("Polar Cut Selection", className="cut-mode-title"),
            dcc.RadioItems(
                id="cut-mode-radio",
                options=[
                    {"label": "Auto (include unknown)", "value": "auto-include"},
                    {"label": "Auto (exclude unknown)", "value": "auto-exclude"},
                    {"label": "All", "value": "all"},
                ],
                value=current_mode,
                className="cut-mode-radio",
                labelClassName="cut-mode-option",
            ),
        ],
    )


def create_app(csv_path: Path, poll_interval_ms: int = 1000) -> Dash:
    """Creates and configures the Dash app."""
    app = Dash(__name__, update_title=None, suppress_callback_exceptions=True)
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
        Output("panel-info", "children"),
        Input("poll-interval", "n_intervals"),
        Input("cut-mode", "data"),
    )
    def _refresh(_interval: int, cut_mode_data: str | None):
        cut_mode = cut_mode_data if cut_mode_data in CUT_MODES else DEFAULT_CUT_MODE
        snapshot = get_latest_snapshot(cache=cache, csv_path=csv_path)
        info_panel = _build_info_panel(snapshot=snapshot)

        if not snapshot.data_changed and ctx.triggered_id == "poll-interval":
            return (*(dash.no_update for _ in GRAPH_IDS), info_panel)

        figures = build_dashboard_figures(snapshot.data, cut_mode=cut_mode)
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

    @app.callback(
        Output("hamburger-dropdown", "className"),
        Input("hamburger-btn", "n_clicks"),
        State("hamburger-dropdown", "className"),
        prevent_initial_call=True,
    )
    def _toggle_dropdown(_, current_class):
        if current_class and "hidden" in current_class:
            return "hamburger-dropdown"
        return "hamburger-dropdown hidden"

    @app.callback(
        Output("config-modal-overlay", "className"),
        Output("modal-body", "children"),
        Output("hamburger-dropdown", "className", allow_duplicate=True),
        Input("open-config-btn", "n_clicks"),
        State("graph-config", "data"),
        State("cut-mode", "data"),
        prevent_initial_call=True,
    )
    def _open_modal(_, config_data, cut_mode_data):
        config = _normalize_config(config_data)
        current_mode = cut_mode_data if cut_mode_data in CUT_MODES else DEFAULT_CUT_MODE
        modal_content = [
            _build_modal_groups(config),
            html.Div(className="modal-items", children=_build_modal_items(config)),
            _build_cut_mode_selector(current_mode),
        ]
        return "modal-overlay", modal_content, "hamburger-dropdown hidden"

    @app.callback(
        Output("config-modal-overlay", "className", allow_duplicate=True),
        Input("close-config-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _close_modal(_):
        return "modal-overlay hidden"

    @app.callback(
        Output("cut-mode", "data"),
        Input("cut-mode-radio", "value"),
        prevent_initial_call=True,
    )
    def _update_cut_mode(value):
        return value

    clientside_callback(
        """
        function(n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;
            var cfg = window._pendingConfig;
            if (!cfg) return window.dash_clientside.no_update;
            window._pendingConfig = null;
            return cfg;
        }
        """,
        Output("graph-config", "data"),
        Input("config-sync-btn", "n_clicks"),
        prevent_initial_call=True,
    )

    @app.callback(
        *[Output(f"panel-{pid}", "style") for pid in PANEL_IDS],
        Input("graph-config", "data"),
    )
    def _apply_panel_styles(config_data):
        config = _normalize_config(config_data)
        style_by_id = {}
        for item in config:
            style = {"order": item["order"]}
            if not item["enabled"]:
                style["display"] = "none"
            style_by_id[item["id"]] = style
        return tuple(
            style_by_id.get(pid, {"order": i}) for i, pid in enumerate(PANEL_IDS)
        )

    return app


def _build_layout(poll_interval_ms: int) -> html.Div:
    return html.Div(
        className="page",
        children=[
            html.Div(
                id="hamburger-container",
                className="hamburger-container",
                children=[
                    html.Button("☰", id="hamburger-btn", className="hamburger-btn"),
                    html.Div(
                        id="hamburger-dropdown",
                        className="hamburger-dropdown hidden",
                        children=[
                            html.Button(
                                "Select Graphs",
                                id="open-config-btn",
                                className="dropdown-item",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                id="config-modal-overlay",
                className="modal-overlay hidden",
                children=[
                    html.Div(
                        className="modal-dialog",
                        children=[
                            html.Div(
                                className="modal-header",
                                children=[
                                    html.H3("Configure Graphs"),
                                    html.Button(
                                        "Done",
                                        id="close-config-btn",
                                        className="modal-close-btn",
                                    ),
                                ],
                            ),
                            html.Div(id="modal-body", className="modal-body"),
                        ],
                    ),
                ],
            ),
            html.H1("Chamber Monitoring", className="title"),
            html.Div(
                className="grid",
                children=[
                    _graph_panel("az-peak"),
                    _graph_panel("az-center"),
                    _graph_panel("el-peak"),
                    _graph_panel("path-pan-tilt"),
                    _graph_panel("power-time"),
                    _graph_panel("pan-peak"),
                    _graph_panel("pan-center"),
                    _graph_panel("tilt-peak"),
                    _graph_panel("path-az-el"),
                    _graph_panel("freq-time"),
                    _graph_panel("az-el-peak-heat"),
                    _graph_panel("az-el-center-heat"),
                    _graph_panel("pan-tilt-peak-heat"),
                    _graph_panel("pan-tilt-center-heat"),
                    html.Div(id="panel-info", className="info"),
                ],
            ),
            html.Button(id="config-sync-btn", style={"display": "none"}, n_clicks=0),
            dcc.Store(id="graph-config", storage_type="memory", data=_default_config()),
            dcc.Store(id="cut-mode", storage_type="local", data=DEFAULT_CUT_MODE),
            dcc.Interval(id="poll-interval", interval=poll_interval_ms, n_intervals=0),
        ],
    )


def _graph_panel(graph_id: str) -> html.Div:
    return html.Div(
        id=f"panel-{graph_id}",
        className="panel",
        children=[dcc.Graph(id=graph_id, config={"displayModeBar": False})],
    )


def _build_info_panel(snapshot) -> list:
    latest_row = _safe_latest_row(snapshot.data)
    return [
        html.H3("Run Info"),
        html.Ul(
            children=[
                html.Li(f"File exists: {snapshot.file_exists}"),
                html.Li(f"Rows loaded: {snapshot.rows_loaded}"),
                html.Li(f"Parse errors: {snapshot.parse_errors_count}"),
                html.Li(
                    f"Last refresh: {_format_timestamp(snapshot.last_update_time)}"
                ),
                html.Li(
                    f"Latest timestamp: {_format_timestamp(latest_row.get(CSV_COLUMNS['timestamp']))}"
                ),
                html.Li(f"Latest cut: {latest_row.get(CSV_COLUMNS['cut_id'], 'N/A')}"),
                html.Li(
                    f"Latest peak power (dBm): {_format_number(latest_row.get(CSV_COLUMNS['peak_power_dbm']))}"
                ),
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
