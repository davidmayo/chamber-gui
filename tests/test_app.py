"""Tests for Dash app factory, helpers, and layout structure."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from chamber_gui.app import (
    _build_experiment_cut_card,
    _build_experiment_modal_body,
    _build_info_panel,
    _build_modal_groups,
    _build_modal_items,
    _build_source_status,
    _cut_axis_labels,
    _default_config,
    _format_number,
    _format_timestamp,
    _graph_panel,
    _normalize_config,
    _safe_latest_row,
    create_app,
)
from chamber_gui.models import CSV_COLUMNS, GRAPH_IDS, PANEL_IDS, CsvSnapshot


def test_create_app_layout_contains_expected_ids() -> None:
    app = create_app(csv_path=Path("sample_data") / "run_data.csv")
    layout_repr = str(app.layout)
    for graph_id in GRAPH_IDS:
        assert graph_id in layout_repr
    assert "poll-interval" in layout_repr
    assert "panel-info" in layout_repr
    assert "open-experiment-btn" in layout_repr
    assert "experiment-modal-overlay" in layout_repr


def test_create_app_disables_update_title() -> None:
    app = create_app(csv_path=Path("sample_data") / "run_data.csv")
    assert app.config.update_title is None


def test_default_config_enables_all_panels_in_order() -> None:
    config = _default_config()
    assert len(config) == len(PANEL_IDS)
    assert [item["id"] for item in config] == list(PANEL_IDS)
    assert all(item["enabled"] for item in config)
    assert [item["order"] for item in config] == list(range(len(PANEL_IDS)))


def test_normalize_config_returns_default_for_invalid_input() -> None:
    config = _normalize_config(data="not-a-list")
    assert len(config) == len(PANEL_IDS)
    assert [item["id"] for item in config] == list(PANEL_IDS)


def test_normalize_config_adds_missing_panels_and_sorts_by_order() -> None:
    config = _normalize_config(
        [
            {"id": "pan-peak", "enabled": False, "order": 5},
            {"id": "az-peak", "enabled": True, "order": 1},
        ]
    )
    assert config[0]["id"] == "az-peak"
    assert config[1]["id"] == "pan-peak"
    assert len({item["id"] for item in config}) == len(PANEL_IDS)


@pytest.mark.xfail(
    reason=(
        "_normalize_config currently preserves duplicate panel IDs from input "
        "instead of enforcing one entry per PANEL_ID."
    ),
    strict=True,
)
def test_normalize_config_returns_unique_entry_per_panel_id() -> None:
    # Known bug: duplicate ids in stored config are not deduplicated by _normalize_config.
    config = _normalize_config(
        [
            {"id": "az-peak", "enabled": True, "order": 0},
            {"id": "az-peak", "enabled": False, "order": 1},
        ]
    )
    assert len(config) == len(PANEL_IDS)
    assert len({item["id"] for item in config}) == len(PANEL_IDS)


def test_build_modal_groups_reflects_enabled_mixed_and_disabled_states() -> None:
    config = _default_config()
    for item in config:
        if item["id"] in {"az-peak", "pan-peak"}:
            item["enabled"] = False

    groups = _build_modal_groups(config)
    group_json = [child.to_plotly_json()["props"] for child in groups.children]
    all_group = next(group for group in group_json if group["data-group-id"] == "all")
    assert all_group["children"][0].className == "modal-checkbox modal-checkbox--mixed"
    peak_group = next(group for group in group_json if group["data-group-id"] == "peak")
    assert peak_group["children"][0].className == "modal-checkbox modal-checkbox--mixed"


def test_build_modal_items_has_expected_shape() -> None:
    items = _build_modal_items(_default_config())
    assert len(items) == len(PANEL_IDS)
    first = items[0].to_plotly_json()["props"]
    assert first["className"] == "modal-item"
    assert first["data-panel-id"] == PANEL_IDS[0]
    assert first["children"][0].className == "drag-handle"
    assert first["children"][2].className == "panel-label"


def test_cut_axis_labels_returns_expected_pan_or_tilt_fields() -> None:
    assert _cut_axis_labels("horizontal") == (
        "Start Pan Angle",
        "End Pan Angle",
        "Step Pan Angle",
        "Fixed Tilt Angle",
    )
    assert _cut_axis_labels("vertical") == (
        "Start Tilt Angle",
        "End Tilt Angle",
        "Step Tilt Angle",
        "Fixed Pan Angle",
    )


def test_build_experiment_cut_card_has_expected_shape() -> None:
    card = _build_experiment_cut_card(index=1)
    props = card.to_plotly_json()["props"]
    assert props["className"] == "experiment-cut-card"
    assert props["draggable"] == "true"
    header = props["children"][0]
    assert header.className == "experiment-cut-card-header"
    assert header.children[0].className == "experiment-cut-drag-handle"
    assert header.children[2].className == "experiment-cut-delete-btn"
    orientation = props["children"][1]
    assert orientation.children[1].to_plotly_json()["props"]["id"] == {
        "type": "exp-cut-orientation",
        "index": 1,
    }
    fields_grid = props["children"][2]
    first_angle_label = fields_grid.children[0].children[0].children
    assert first_angle_label == "Start Pan Angle"


def test_build_experiment_modal_body_contains_cuts_and_parameters_sections() -> None:
    body = _build_experiment_modal_body()
    props = body.to_plotly_json()["props"]
    assert props["id"] == "experiment-modal-body"
    assert props["className"] == "experiment-modal-body"
    cuts_column = props["children"][0]
    params_column = props["children"][1]
    assert cuts_column.children[0].children == "Cuts"
    assert params_column.children[0].children == "Parameters"
    assert cuts_column.children[2].className == "experiment-add-cut-btn"


def test_graph_panel_has_expected_id_and_graph() -> None:
    panel = _graph_panel("az-peak")
    props = panel.to_plotly_json()["props"]
    assert props["id"] == "panel-az-peak"
    assert props["className"] == "panel"
    graph_props = props["children"][0].to_plotly_json()["props"]
    assert graph_props["id"] == "az-peak"
    assert graph_props["config"] == {"displayModeBar": False}


def test_safe_latest_row_handles_empty_and_returns_last_row() -> None:
    assert _safe_latest_row(pd.DataFrame()) == {}
    frame = pd.DataFrame({"value": [1, 2]})
    assert _safe_latest_row(frame) == {"value": 2}


def test_format_timestamp_handles_none_datetime_and_pandas_timestamp() -> None:
    assert _format_timestamp(None) == "N/A"
    assert _format_timestamp(datetime(2026, 2, 8, 12, 0, tzinfo=UTC)).endswith("+00:00")
    value = _format_timestamp(pd.Timestamp("2026-02-08 12:00:00"))
    assert value.endswith("+00:00")


def test_format_number_handles_bad_and_numeric_values() -> None:
    assert _format_number(None) == "N/A"
    assert _format_number("not-a-number") == "N/A"
    assert _format_number(1.23456) == "1.235"


def test_build_info_panel_includes_latest_row_details() -> None:
    data = pd.DataFrame(
        [
            {
                CSV_COLUMNS["timestamp"]: pd.Timestamp("2026-02-06T18:00:41+00:00"),
                CSV_COLUMNS["cut_id"]: "fine-pan",
                CSV_COLUMNS["peak_power_dbm"]: -15.1,
                CSV_COLUMNS["center_power_dbm"]: -19.1,
                CSV_COLUMNS["peak_frequency_hz"]: 10_003_000_000.0,
                CSV_COLUMNS["center_frequency_hz"]: 10_000_000_000.0,
            }
        ]
    )
    snapshot = CsvSnapshot(
        data=data,
        mtime=1.0,
        file_exists=True,
        rows_loaded=1,
        parse_errors_count=0,
        last_update_time=datetime(2026, 2, 8, 12, 0, tzinfo=UTC),
        warning=None,
        data_changed=True,
    )
    info = _build_info_panel(snapshot, source_config=None)
    assert info[0].children == "Run Info"
    items = info[1].children
    assert any("Latest cut: fine-pan" in item.children for item in items)
    assert any("Latest peak power (dBm): -15.100" in item.children for item in items)
    assert any("Warning: None" in item.children for item in items)


def test_build_info_panel_includes_source_details() -> None:
    snapshot = CsvSnapshot(
        data=pd.DataFrame(),
        mtime=None,
        file_exists=False,
        rows_loaded=0,
        parse_errors_count=0,
        last_update_time=datetime(2026, 2, 8, 12, 0, tzinfo=UTC),
        warning=None,
        data_changed=False,
    )
    info = _build_info_panel(
        snapshot,
        source_config={"mode": "folder", "path": "/tmp/runs"},
    )
    items = info[1].children
    assert any("Source mode: folder" in item.children for item in items)
    assert any("Source path: /tmp/runs" in item.children for item in items)


def test_build_source_status_formats_message() -> None:
    status = _build_source_status(
        source_mode="folder",
        source_path=Path("/tmp/runs"),
        resolved_csv=Path("/tmp/runs/run.csv"),
    )
    assert "Source: folder" in status
    assert "Resolved CSV: /tmp/runs/run.csv" in status
