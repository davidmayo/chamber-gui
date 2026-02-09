"""Browser E2E tests for modal interactions and panel updates."""

from __future__ import annotations

from pathlib import Path

import pytest

from chamber_gui.app import create_app
from chamber_gui.models import PANEL_IDS

pytestmark = pytest.mark.e2e


def _start_app(dash_duo, csv_path: Path) -> None:
    app = create_app(csv_path=csv_path, poll_interval_ms=10_000)
    dash_duo.start_server(app)
    dash_duo.wait_for_element("#hamburger-btn", timeout=10)
    dash_duo.wait_for_element("#panel-az-peak", timeout=10)
    dash_duo.wait_for_element("#panel-info", timeout=10)


def _open_modal(dash_duo) -> None:
    hamburger_button = dash_duo.find_element("#hamburger-btn")
    dash_duo.driver.execute_script("arguments[0].click();", hamburger_button)
    open_button = dash_duo.wait_for_element("#open-config-btn", timeout=5)
    dash_duo.driver.execute_script("arguments[0].click();", open_button)
    dash_duo.wait_for_element_by_css_selector(
        "#config-modal-overlay.modal-overlay:not(.hidden)",
        timeout=10,
    )
    dash_duo.wait_for_element(".modal-items", timeout=5)


def test_e2e_layout_renders_expected_panels(dash_duo, sample_csv_path: Path) -> None:
    _start_app(dash_duo, sample_csv_path)
    assert dash_duo.find_element("#hamburger-btn").is_displayed()
    assert dash_duo.find_element("#panel-az-peak").is_displayed()
    assert dash_duo.find_element("#panel-info").is_displayed()
    assert "hidden" in dash_duo.find_element("#config-modal-overlay").get_attribute(
        "class"
    )


def test_e2e_modal_group_toggle_and_reorder_updates_layout(
    dash_duo, sample_csv_path: Path
) -> None:
    _start_app(dash_duo, sample_csv_path)
    _open_modal(dash_duo)
    groups = dash_duo.find_elements(".group-item")
    items = dash_duo.find_elements(".modal-item")
    assert len(groups) == 5
    assert len(items) == len(PANEL_IDS)

    dash_duo.wait_for_style_to_equal("#panel-az-peak", "order", "0", timeout=10)

    peak_group = dash_duo.find_element(".group-item[data-group-id='peak']")
    peak_group.click()
    dash_duo.wait_for_style_to_equal("#panel-az-peak", "display", "none", timeout=10)
    dash_duo.wait_for_style_to_equal("#panel-pan-peak", "display", "none", timeout=10)

    peak_group.click()
    dash_duo.wait_for_style_to_equal("#panel-az-peak", "display", "block", timeout=10)
    dash_duo.wait_for_style_to_equal("#panel-pan-peak", "display", "block", timeout=10)

    dash_duo.driver.execute_script(
        """
        const list = document.querySelector("#modal-body .modal-items");
        const source = list.querySelector(".modal-item[data-panel-id='az-peak']");
        const target = list.querySelector(".modal-item[data-panel-id='power-time']");
        list.insertBefore(source, target.nextSibling);
        const config = Array.from(
            document.querySelectorAll("#modal-body .modal-item")
        ).map((el, index) => {
            const panelId = el.getAttribute("data-panel-id");
            const cb = el.querySelector(".modal-checkbox");
            return {
                id: panelId,
                enabled: cb ? cb.classList.contains("modal-checkbox--on") : true,
                order: index,
            };
        });
        window._pendingConfig = config;
        document.getElementById("config-sync-btn").click();
        """,
    )

    dash_duo.wait_for_style_to_equal("#panel-az-peak", "order", "5", timeout=10)
