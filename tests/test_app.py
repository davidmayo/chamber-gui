"""Tests for Dash app factory, helpers, and layout structure."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from chamber_gui.app import (
    _build_info_panel,
    _build_modal_groups,
    _build_modal_items,
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
    )
    info = _build_info_panel(snapshot)
    assert info[0].children == "Run Info"
    items = info[1].children
    assert any("Latest cut: fine-pan" in item.children for item in items)
    assert any("Latest peak power (dBm): -15.100" in item.children for item in items)
    assert any("Warning: None" in item.children for item in items)
