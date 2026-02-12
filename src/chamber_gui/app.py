"""Dash application factory and callback wiring."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading

import pandas as pd
import dash
from dash import MATCH, Dash, Input, Output, State, clientside_callback, ctx, dcc, html

from chamber_gui.data_loader import (
    SnapshotCache,
    find_latest_csv,
    get_latest_snapshot,
    infer_source_mode,
)
from chamber_gui.figures import build_cut_color_map, build_dashboard_figures
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
            "el-center",
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
            "tilt-center",
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
        [
            "az-center",
            "el-center",
            "pan-center",
            "tilt-center",
            "az-el-center-heat",
            "pan-tilt-center-heat",
        ],
    ),
]

_DEFAULT_EXPERIMENT_CUT_COUNT = 1


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


def _build_modal_right_panel(current_mode: str, hpbw_enabled: bool) -> html.Div:
    """Builds the right panel of the modal (cut mode + overlays)."""
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
            html.Hr(
                style={
                    "margin": "14px 0",
                    "border": "none",
                    "border-top": "1px solid var(--line)",
                }
            ),
            html.H4("Overlays", className="cut-mode-title"),
            dcc.Checklist(
                id="hpbw-checkbox",
                options=[
                    {"label": "Half Power Beam Width", "value": "enabled"},
                ],
                value=["enabled"] if hpbw_enabled else [],
                className="cut-mode-radio",
                labelClassName="cut-mode-option",
            ),
        ],
    )


def _cut_axis_labels(orientation: str) -> tuple[str, str, str, str]:
    """Returns cut angle labels for the selected orientation."""
    if orientation == "vertical":
        return (
            "Start Tilt Angle",
            "End Tilt Angle",
            "Step Tilt Angle",
            "Fixed Pan Angle",
        )
    return (
        "Start Pan Angle",
        "End Pan Angle",
        "Step Pan Angle",
        "Fixed Tilt Angle",
    )


def _normalize_cut_count(value: object) -> int:
    """Normalizes cut count state to a valid positive integer."""
    try:
        count = int(value)
    except (TypeError, ValueError):
        return _DEFAULT_EXPERIMENT_CUT_COUNT
    return max(_DEFAULT_EXPERIMENT_CUT_COUNT, count)


def _build_experiment_cut_card(index: int) -> html.Div:
    """Builds one mockup cut card for the experiment designer modal."""
    start_label, end_label, step_label, fixed_label = _cut_axis_labels("horizontal")
    return html.Div(
        className="experiment-cut-card",
        draggable="true",
        children=[
            html.Div(
                className="experiment-cut-card-header",
                children=[
                    html.Span("⠿", className="experiment-cut-drag-handle"),
                    html.Label(
                        className="experiment-cut-field experiment-cut-id-field",
                        children=[
                            html.Span("Cut ID", className="experiment-cut-label"),
                            dcc.Input(
                                type="text",
                                className="experiment-cut-input experiment-cut-id-input",
                                placeholder=f"cut-{index + 1}",
                            ),
                        ],
                    ),
                    html.Button(
                        "Delete",
                        type="button",
                        className="experiment-cut-delete-btn",
                    ),
                ],
            ),
            html.Div(
                className="experiment-cut-orientation",
                children=[
                    html.Span("Orientation", className="experiment-cut-label"),
                    dcc.RadioItems(
                        id={"type": "exp-cut-orientation", "index": index},
                        options=[
                            {"label": "Horizontal", "value": "horizontal"},
                            {"label": "Vertical", "value": "vertical"},
                        ],
                        value="horizontal",
                        className="experiment-cut-radio",
                        labelClassName="experiment-cut-radio-option",
                    ),
                ],
            ),
            html.Div(
                className="experiment-cut-fields-grid",
                children=[
                    html.Label(
                        className="experiment-cut-field",
                        children=[
                            html.Span(
                                start_label,
                                id={"type": "exp-cut-start-label", "index": index},
                                className="experiment-cut-label experiment-cut-angle-label",
                            ),
                            dcc.Input(
                                type="text",
                                inputMode="decimal",
                                className="experiment-cut-input experiment-cut-angle-input",
                            ),
                        ],
                    ),
                    html.Label(
                        className="experiment-cut-field",
                        children=[
                            html.Span(
                                end_label,
                                id={"type": "exp-cut-end-label", "index": index},
                                className="experiment-cut-label experiment-cut-angle-label",
                            ),
                            dcc.Input(
                                type="text",
                                inputMode="decimal",
                                className="experiment-cut-input experiment-cut-angle-input",
                            ),
                        ],
                    ),
                    html.Label(
                        className="experiment-cut-field",
                        children=[
                            html.Span(
                                step_label,
                                id={"type": "exp-cut-step-label", "index": index},
                                className="experiment-cut-label experiment-cut-angle-label",
                            ),
                            dcc.Input(
                                type="text",
                                inputMode="decimal",
                                className="experiment-cut-input experiment-cut-angle-input",
                            ),
                        ],
                    ),
                    html.Label(
                        className="experiment-cut-field",
                        children=[
                            html.Span(
                                fixed_label,
                                id={"type": "exp-cut-fixed-label", "index": index},
                                className="experiment-cut-label experiment-cut-angle-label",
                            ),
                            dcc.Input(
                                type="text",
                                inputMode="decimal",
                                className="experiment-cut-input experiment-cut-angle-input",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def _build_experiment_modal_body(
    cut_count: int = _DEFAULT_EXPERIMENT_CUT_COUNT,
) -> html.Div:
    """Builds the mockup body content for the experiment designer modal."""
    normalized_cut_count = _normalize_cut_count(cut_count)
    return html.Div(
        id="experiment-modal-body",
        className="experiment-modal-body",
        children=[
            html.Div(
                className="experiment-cuts-column",
                children=[
                    html.H4("Cuts", className="experiment-column-title"),
                    html.Div(
                        className="experiment-cut-list",
                        children=[
                            _build_experiment_cut_card(index)
                            for index in range(normalized_cut_count)
                        ],
                    ),
                    html.Button(
                        "Add Cut",
                        id="experiment-add-cut-btn",
                        type="button",
                        className="experiment-add-cut-btn",
                    ),
                ],
            ),
            html.Div(
                className="experiment-parameters-column",
                children=[
                    html.H4("Parameters", className="experiment-column-title"),
                    html.Div(
                        className="experiment-parameters-placeholder",
                        children="Experiment parameters mockup placeholder.",
                    ),
                ],
            ),
        ],
    )


def create_app(csv_path: Path, poll_interval_ms: int = 1000) -> Dash:
    """Creates and configures the Dash app."""
    app = Dash(__name__, update_title=None, suppress_callback_exceptions=True)
    app.index_string = APP_INDEX_TEMPLATE
    source_mode = infer_source_mode(csv_path)
    source_config = {"path": str(csv_path), "mode": source_mode}
    app.layout = _build_layout(
        poll_interval_ms=poll_interval_ms,
        source_config=source_config,
    )

    @app.server.after_request
    def _no_cache_dash_api(response):
        """Prevent browser from caching Dash API responses.

        Without this, the browser may serve stale ``_dash-dependencies``
        after the callback graph changes (e.g. adding a new Input),
        causing IndexError in Dash's dispatch.
        """
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        return response

    cache = SnapshotCache()
    cut_color_map: dict[str, str] = {}
    cut_color_lock = threading.Lock()

    @app.callback(
        Output("az-peak", "figure"),
        Output("az-center", "figure"),
        Output("el-peak", "figure"),
        Output("el-center", "figure"),
        Output("path-pan-tilt", "figure"),
        Output("power-time", "figure"),
        Output("pan-peak", "figure"),
        Output("pan-center", "figure"),
        Output("tilt-peak", "figure"),
        Output("tilt-center", "figure"),
        Output("path-az-el", "figure"),
        Output("freq-time", "figure"),
        Output("az-el-peak-heat", "figure"),
        Output("az-el-center-heat", "figure"),
        Output("pan-tilt-peak-heat", "figure"),
        Output("pan-tilt-center-heat", "figure"),
        Output("panel-info", "children"),
        Output("source-status", "children"),
        Input("poll-interval", "n_intervals"),
        Input("cut-mode", "data"),
        Input("graph-config", "data"),
        Input("source-config", "data"),
        Input("hpbw-enabled", "data"),
    )
    def _refresh(
        _interval: int,
        cut_mode_data: str | None,
        _config_data: object,
        source_config_data: object,
        hpbw_data: object,
    ):
        cut_mode = cut_mode_data if cut_mode_data in CUT_MODES else DEFAULT_CUT_MODE
        hpbw_enabled = bool(hpbw_data)
        source_path = csv_path
        source_mode = infer_source_mode(csv_path)
        if isinstance(source_config_data, dict):
            raw_path = source_config_data.get("path")
            raw_mode = source_config_data.get("mode")
            if isinstance(raw_path, str) and raw_path:
                source_path = Path(raw_path)
            if raw_mode in {"file", "folder"}:
                source_mode = raw_mode
        snapshot = get_latest_snapshot(
            cache=cache,
            csv_path=source_path,
            source_mode=source_mode,
        )
        resolved_csv = source_path
        if source_mode == "folder":
            resolved_csv = find_latest_csv(source_path)
        status_line = _build_source_status(
            source_mode=source_mode,
            source_path=source_path,
            resolved_csv=resolved_csv,
        )
        info_panel = _build_info_panel(
            snapshot=snapshot,
            source_config=source_config_data,
        )

        if not snapshot.data_changed and ctx.triggered_id == "poll-interval":
            return (*(dash.no_update for _ in GRAPH_IDS), info_panel, status_line)

        figure_data = snapshot.data.copy()
        cut_ids = (
            figure_data[CSV_COLUMNS["cut_id"]].tolist()
            if CSV_COLUMNS["cut_id"] in figure_data.columns
            else []
        )
        with cut_color_lock:
            cut_color_map.update(
                build_cut_color_map(cut_ids=cut_ids, existing_map=cut_color_map)
            )
            active_color_map = dict(cut_color_map)

        figures = build_dashboard_figures(
            figure_data,
            cut_mode=cut_mode,
            hpbw_enabled=hpbw_enabled,
            color_map=active_color_map,
        )
        return (
            figures.az_peak,
            figures.az_center,
            figures.el_peak,
            figures.el_center,
            figures.path_pan_tilt,
            figures.power_time,
            figures.pan_peak,
            figures.pan_center,
            figures.tilt_peak,
            figures.tilt_center,
            figures.path_az_el,
            figures.freq_time,
            figures.az_el_peak_heat,
            figures.az_el_center_heat,
            figures.pan_tilt_peak_heat,
            figures.pan_tilt_center_heat,
            info_panel,
            status_line,
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
        Output("source-config", "data"),
        Input("open-source-file-btn", "n_clicks"),
        Input("open-source-folder-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _select_source(_file_clicks, _folder_clicks):
        if ctx.triggered_id not in {
            "open-source-file-btn",
            "open-source-folder-btn",
        }:
            return dash.no_update
        try:
            from tkinter import TclError, Tk, filedialog
        except ImportError:
            return dash.no_update

        root = Tk()
        root.withdraw()
        try:
            root.wm_attributes("-topmost", 1)
        except TclError:
            pass

        if ctx.triggered_id == "open-source-file-btn":
            selected = filedialog.askopenfilename(
                title="Select CSV File",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            )
            mode = "file"
        else:
            selected = filedialog.askdirectory(title="Select CSV Folder")
            mode = "folder"

        root.destroy()

        if not selected:
            return dash.no_update
        return {"path": selected, "mode": mode}

    @app.callback(
        Output("config-modal-overlay", "className"),
        Output("modal-body", "children"),
        Output("hamburger-dropdown", "className", allow_duplicate=True),
        Input("open-config-btn", "n_clicks"),
        State("graph-config", "data"),
        State("cut-mode", "data"),
        State("hpbw-enabled", "data"),
        prevent_initial_call=True,
    )
    def _open_modal(_, config_data, cut_mode_data, hpbw_data):
        config = _normalize_config(config_data)
        current_mode = cut_mode_data if cut_mode_data in CUT_MODES else DEFAULT_CUT_MODE
        hpbw_enabled = bool(hpbw_data)
        modal_content = [
            _build_modal_groups(config),
            html.Div(className="modal-items", children=_build_modal_items(config)),
            _build_modal_right_panel(current_mode, hpbw_enabled),
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
        Output("experiment-modal-overlay", "className"),
        Output("hamburger-dropdown", "className", allow_duplicate=True),
        Input("open-experiment-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _open_experiment_modal(_):
        return "experiment-modal-overlay", "hamburger-dropdown hidden"

    @app.callback(
        Output("experiment-cut-count", "data"),
        Input("open-experiment-btn", "n_clicks"),
        Input("experiment-add-cut-btn", "n_clicks"),
        State("experiment-cut-count", "data"),
        prevent_initial_call=True,
    )
    def _set_experiment_cut_count(_open_clicks, _add_clicks, current_cut_count):
        if ctx.triggered_id == "open-experiment-btn":
            return _DEFAULT_EXPERIMENT_CUT_COUNT
        if ctx.triggered_id == "experiment-add-cut-btn":
            return _normalize_cut_count(current_cut_count) + 1
        return dash.no_update

    @app.callback(
        Output("experiment-modal-body", "children"),
        Input("experiment-cut-count", "data"),
    )
    def _render_experiment_modal_body(cut_count_data):
        return _build_experiment_modal_body(
            cut_count=_normalize_cut_count(cut_count_data)
        ).children

    @app.callback(
        Output("experiment-modal-overlay", "className", allow_duplicate=True),
        Input("close-experiment-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _close_experiment_modal(_):
        return "experiment-modal-overlay hidden"

    @app.callback(
        Output({"type": "exp-cut-start-label", "index": MATCH}, "children"),
        Output({"type": "exp-cut-end-label", "index": MATCH}, "children"),
        Output({"type": "exp-cut-step-label", "index": MATCH}, "children"),
        Output({"type": "exp-cut-fixed-label", "index": MATCH}, "children"),
        Input({"type": "exp-cut-orientation", "index": MATCH}, "value"),
    )
    def _update_experiment_cut_labels(orientation):
        return _cut_axis_labels(orientation)

    @app.callback(
        Output("cut-mode", "data"),
        Input("cut-mode-radio", "value"),
        prevent_initial_call=True,
    )
    def _update_cut_mode(value):
        return value

    @app.callback(
        Output("hpbw-enabled", "data"),
        Input("hpbw-checkbox", "value"),
        prevent_initial_call=True,
    )
    def _update_hpbw(value):
        return bool(value)

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


def _build_layout(poll_interval_ms: int, source_config: dict) -> html.Div:
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
                            html.Button(
                                "Design Experiment",
                                id="open-experiment-btn",
                                className="dropdown-item",
                            ),
                            html.Button(
                                "Source CSV",
                                id="open-source-file-btn",
                                className="dropdown-item",
                            ),
                            html.Button(
                                "Source Folder",
                                id="open-source-folder-btn",
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
            html.Div(
                id="experiment-modal-overlay",
                className="experiment-modal-overlay hidden",
                children=[
                    html.Div(
                        className="experiment-modal-dialog",
                        children=[
                            html.Div(
                                className="experiment-modal-header",
                                children=[
                                    html.H3("Design Experiment"),
                                    html.Button(
                                        "Done",
                                        id="close-experiment-btn",
                                        className="experiment-modal-close-btn",
                                    ),
                                ],
                            ),
                            _build_experiment_modal_body(
                                cut_count=_DEFAULT_EXPERIMENT_CUT_COUNT
                            ),
                        ],
                    ),
                ],
            ),
            html.H1("Chamber Monitoring", className="title"),
            html.Div(id="source-status", className="status-line"),
            html.Div(
                className="grid",
                children=[
                    _graph_panel("az-peak"),
                    _graph_panel("az-center"),
                    _graph_panel("el-peak"),
                    _graph_panel("el-center"),
                    _graph_panel("path-pan-tilt"),
                    _graph_panel("power-time"),
                    _graph_panel("pan-peak"),
                    _graph_panel("pan-center"),
                    _graph_panel("tilt-peak"),
                    _graph_panel("tilt-center"),
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
            dcc.Store(id="source-config", storage_type="memory", data=source_config),
            dcc.Store(id="hpbw-enabled", storage_type="local", data=False),
            dcc.Store(
                id="experiment-cut-count",
                storage_type="memory",
                data=_DEFAULT_EXPERIMENT_CUT_COUNT,
            ),
            dcc.Interval(id="poll-interval", interval=poll_interval_ms, n_intervals=0),
        ],
    )


def _graph_panel(graph_id: str) -> html.Div:
    return html.Div(
        id=f"panel-{graph_id}",
        className="panel",
        children=[dcc.Graph(id=graph_id, config={"displayModeBar": False})],
    )


def _build_info_panel(snapshot, source_config: object | None = None) -> list:
    source_mode = "N/A"
    source_path = "N/A"
    if isinstance(source_config, dict):
        mode = source_config.get("mode")
        path = source_config.get("path")
        if isinstance(mode, str):
            source_mode = mode
        if isinstance(path, str) and path:
            source_path = path

    latest_row = _safe_latest_row(snapshot.data)
    return [
        html.H3("Run Info"),
        html.Ul(
            children=[
                html.Li(f"File exists: {snapshot.file_exists}"),
                html.Li(f"Source mode: {source_mode}"),
                html.Li(f"Source path: {source_path}"),
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


def _build_source_status(
    source_mode: str,
    source_path: Path,
    resolved_csv: Path | None,
) -> str:
    resolved_text = str(resolved_csv) if resolved_csv is not None else "N/A"
    return f"Source: {source_mode} ({source_path}) | Resolved CSV: {resolved_text}"


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
