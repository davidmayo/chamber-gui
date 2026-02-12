"""Tests for Dash callback functions in chamber_gui.app."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from chamber_gui.app import create_app
from chamber_gui.models import CSV_COLUMNS, PANEL_IDS


def test_app_registers_expected_callback_names() -> None:
    app = create_app(csv_path=Path("sample_data") / "run_data.csv")
    callback_names = {
        callback_def["callback"].__wrapped__.__name__
        for callback_def in app.callback_map.values()
    }
    assert callback_names == {
        "_refresh",
        "_toggle_dropdown",
        "_select_source",
        "_open_modal",
        "_close_modal",
        "_open_experiment_modal",
        "_set_experiment_cut_keys",
        "_render_experiment_modal_body",
        "_close_experiment_modal",
        "_update_experiment_cut_labels",
        "_update_cut_mode",
        "_update_hpbw",
        "_apply_panel_styles",
    }


def test_toggle_dropdown_callback(callback_lookup) -> None:
    callback = callback_lookup("_toggle_dropdown")
    assert callback(1, "hamburger-dropdown hidden") == "hamburger-dropdown"
    assert callback(2, "hamburger-dropdown") == "hamburger-dropdown hidden"


def test_open_modal_callback_builds_modal_content(callback_lookup) -> None:
    callback = callback_lookup("_open_modal")
    overlay_class, modal_content, dropdown_class = callback(
        1,
        [{"id": "az-peak", "enabled": False, "order": 0}],
        "auto-include",
        False,
    )
    assert overlay_class == "modal-overlay"
    assert dropdown_class == "hamburger-dropdown hidden"
    assert len(modal_content) == 3
    assert modal_content[0].className == "modal-groups"
    assert modal_content[1].className == "modal-items"
    assert modal_content[2].className == "modal-cut-mode"


def test_close_modal_callback_hides_overlay(callback_lookup) -> None:
    callback = callback_lookup("_close_modal")
    assert callback(1) == "modal-overlay hidden"


def test_open_experiment_modal_callback(callback_lookup) -> None:
    callback = callback_lookup("_open_experiment_modal")
    overlay_class, dropdown_class = callback(1)
    assert overlay_class == "experiment-modal-overlay"
    assert dropdown_class == "hamburger-dropdown hidden"


def test_close_experiment_modal_callback_hides_overlay(callback_lookup) -> None:
    callback = callback_lookup("_close_experiment_modal")
    assert callback(1) == "experiment-modal-overlay hidden"


def test_set_experiment_cut_keys_callback(callback_lookup, monkeypatch) -> None:
    callback = callback_lookup("_set_experiment_cut_keys")

    class _Ctx:
        triggered_id = "open-experiment-btn"

    monkeypatch.setattr("chamber_gui.app.ctx", _Ctx())
    assert callback(1, None, [], [8, 9]) == [0]

    _Ctx.triggered_id = "experiment-add-cut-btn"
    assert callback(1, 1, [], [0]) == [0, 1]
    assert callback(1, 2, [], [0, 4]) == [0, 4, 5]

    _Ctx.triggered_id = {"type": "experiment-delete-cut-btn", "index": 4}
    assert callback(1, 2, [1], [0, 4, 5]) == [0, 5]

    _Ctx.triggered_id = {"type": "experiment-delete-cut-btn", "index": 0}
    assert callback(1, 2, [1], [0]) == [0]


def test_render_experiment_modal_body_callback(callback_lookup) -> None:
    callback = callback_lookup("_render_experiment_modal_body")
    body_children = callback([0, 2, 9])
    cuts_column = body_children[0]
    assert cuts_column.className == "experiment-cuts-column"
    assert len(cuts_column.children[1].children) == 3


def test_update_experiment_cut_labels_callback(callback_lookup) -> None:
    callback = callback_lookup("_update_experiment_cut_labels")
    assert callback("horizontal") == (
        "Start Pan Angle",
        "End Pan Angle",
        "Step Pan Angle",
        "Fixed Tilt Angle",
    )
    assert callback("vertical") == (
        "Start Tilt Angle",
        "End Tilt Angle",
        "Step Tilt Angle",
        "Fixed Pan Angle",
    )


def test_apply_panel_styles_callback_respects_enabled_and_order(
    callback_lookup,
) -> None:
    callback = callback_lookup("_apply_panel_styles")
    styles = callback(
        [
            {"id": "az-peak", "enabled": False, "order": 3},
            {"id": "pan-peak", "enabled": True, "order": 1},
        ]
    )
    assert len(styles) == len(PANEL_IDS)
    style_by_panel = dict(zip(PANEL_IDS, styles, strict=True))
    assert style_by_panel["az-peak"]["order"] == 3
    assert style_by_panel["az-peak"]["display"] == "none"
    assert style_by_panel["pan-peak"]["order"] == 1
    assert "display" not in style_by_panel["pan-peak"]


def test_update_hpbw_callback(callback_lookup) -> None:
    callback = callback_lookup("_update_hpbw")
    assert callback(["enabled"]) is True
    assert callback([]) is False


def test_refresh_callback_returns_figures_and_info_panel(callback_lookup) -> None:
    callback = callback_lookup("_refresh")
    outputs = callback(0, "auto-include", None, None, False)
    assert len(outputs) == 18
    for figure in outputs[:-2]:
        assert isinstance(figure, go.Figure)
    info_panel = outputs[-2]
    assert isinstance(info_panel, list)
    assert info_panel[0].children == "Run Info"
    assert len(info_panel[1].children) == 13
    status_line = outputs[-1]
    assert isinstance(status_line, str)


def test_refresh_callback_preserves_cut_colors_when_new_cut_id_is_added(
    sample_rows_df: pd.DataFrame,
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "run_data.csv"
    cut_col = CSV_COLUMNS["cut_id"]
    initial = sample_rows_df.copy()
    initial[cut_col] = ["A", "A", "B", "B"]
    initial.to_csv(csv_path, index=False)
    os.utime(csv_path, (2, 2))

    app = create_app(csv_path=csv_path, poll_interval_ms=250)
    callback = next(
        callback_def["callback"].__wrapped__
        for callback_def in app.callback_map.values()
        if callback_def["callback"].__wrapped__.__name__ == "_refresh"
    )

    first = callback(0, "auto-include", None, None, False)
    first_colors = {trace.name: trace.marker.color for trace in first[0].data}
    assert first_colors["A"] != first_colors["B"]

    next_row = initial.iloc[-1:].copy()
    next_row[cut_col] = "A-early"
    updated = pd.concat([initial, next_row], ignore_index=True)
    updated.to_csv(csv_path, index=False)
    os.utime(csv_path, (3, 3))

    second = callback(1, "auto-include", None, None, False)
    second_colors = {trace.name: trace.marker.color for trace in second[0].data}
    assert second_colors["A"] == first_colors["A"]
    assert second_colors["B"] == first_colors["B"]
    assert "A-early" in second_colors
