"""Tests for HTML index template configuration."""

from __future__ import annotations

from chamber_gui.theme import APP_INDEX_TEMPLATE


def test_app_index_template_contains_dash_placeholders() -> None:
    for token in (
        "{%metas%}",
        "{%favicon%}",
        "{%css%}",
        "{%app_entry%}",
        "{%config%}",
        "{%scripts%}",
        "{%renderer%}",
    ):
        assert token in APP_INDEX_TEMPLATE


def test_app_index_template_contains_expected_css_hooks() -> None:
    for selector in (
        ".hamburger-container",
        ".hamburger-dropdown",
        ".modal-overlay",
        ".experiment-modal-overlay",
        ".experiment-modal-body",
        ".experiment-cut-card",
        ".experiment-add-cut-btn",
        ".experiment-parameters-scroll",
        ".experiment-parameter-group",
        ".experiment-specan-details-btn",
        ".modal-items",
        ".modal-groups",
        ".modal-item",
        ".panel",
        ".info",
    ):
        assert selector in APP_INDEX_TEMPLATE
