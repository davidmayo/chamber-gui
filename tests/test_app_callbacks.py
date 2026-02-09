"""Tests for Dash callback functions in chamber_gui.app."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from chamber_gui.app import create_app
from chamber_gui.models import PANEL_IDS


def test_app_registers_expected_callback_names() -> None:
    app = create_app(csv_path=Path("sample_data") / "run_data.csv")
    callback_names = {
        callback_def["callback"].__wrapped__.__name__
        for callback_def in app.callback_map.values()
    }
    assert callback_names == {
        "_refresh",
        "_toggle_dropdown",
        "_open_modal",
        "_close_modal",
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
    outputs = callback(0, "auto-include", None, False)
    assert len(outputs) == 17
    for figure in outputs[:-1]:
        assert isinstance(figure, go.Figure)
    info_panel = outputs[-1]
    assert isinstance(info_panel, list)
    assert info_panel[0].children == "Run Info"
    assert len(info_panel[1].children) == 11
