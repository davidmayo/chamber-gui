"""Tests for Dash app factory and layout."""

from __future__ import annotations

from pathlib import Path

from chamber_gui.app import create_app
from chamber_gui.models import GRAPH_IDS


def test_create_app_layout_contains_expected_ids() -> None:
    app = create_app(csv_path=Path("sample_data") / "run_data.csv")
    layout_repr = str(app.layout)
    for graph_id in GRAPH_IDS:
        assert graph_id in layout_repr
    assert "poll-interval" in layout_repr
    assert "info-panel" in layout_repr


def test_create_app_disables_update_title() -> None:
    app = create_app(csv_path=Path("sample_data") / "run_data.csv")
    assert app.config.update_title is None

