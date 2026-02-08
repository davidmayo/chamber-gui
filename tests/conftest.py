"""Shared pytest fixtures and helpers for chamber GUI tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
from typing import Any

import pandas as pd
import pytest

from chamber_gui.app import create_app
from chamber_gui.models import CSV_COLUMNS


def _has_any_command(commands: tuple[str, ...]) -> bool:
    """Returns True when any command is available in PATH."""
    return any(shutil.which(command) for command in commands)


def _webdriver_available(webdriver_name: str) -> tuple[bool, str]:
    """Checks local browser/driver availability for the selected WebDriver."""
    if webdriver_name == "Firefox":
        has_browser = _has_any_command(("firefox", "firefox.exe"))
        has_driver = _has_any_command(("geckodriver", "geckodriver.exe"))
        if has_browser and has_driver:
            return True, ""
        return (
            False,
            "E2E tests require Firefox and geckodriver on PATH. "
            "Install both or run without e2e tests.",
        )

    if webdriver_name == "Chrome":
        has_browser = _has_any_command(
            (
                "google-chrome",
                "google-chrome-stable",
                "chromium",
                "chromium-browser",
                "chrome",
                "chrome.exe",
            )
        )
        has_driver = _has_any_command(("chromedriver", "chromedriver.exe"))
        if has_browser and has_driver:
            return True, ""
        return (
            False,
            "E2E tests require a Chrome-compatible browser and chromedriver on PATH. "
            "Install both or run with --webdriver Firefox.",
        )

    return (
        False,
        f"Unsupported webdriver '{webdriver_name}'. Use Firefox or Chrome.",
    )


def pytest_collection_modifyitems(config, items) -> None:
    """Skips e2e tests when selected browser/driver stack is unavailable."""
    webdriver_name = config.getoption("webdriver")
    available, reason = _webdriver_available(webdriver_name)
    if available:
        return
    skip_marker = pytest.mark.skip(reason=reason)
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture
def sample_rows_df() -> pd.DataFrame:
    """Returns a deterministic sample dataset with all required columns."""
    rows = [
        {
            CSV_COLUMNS["timestamp"]: "2026-02-06T18:00:38+00:00",
            CSV_COLUMNS["cut_id"]: "coarse-az",
            CSV_COLUMNS["commanded_tilt"]: 0.0,
            CSV_COLUMNS["commanded_pan"]: -180.0,
            CSV_COLUMNS["commanded_elevation"]: 0.0,
            CSV_COLUMNS["commanded_azimuth"]: -180.0,
            CSV_COLUMNS["actual_tilt"]: 0.1,
            CSV_COLUMNS["actual_pan"]: -180.1,
            CSV_COLUMNS["actual_elevation"]: 0.1,
            CSV_COLUMNS["actual_azimuth"]: -180.1,
            CSV_COLUMNS["center_frequency_hz"]: 10_000_000_000.0,
            CSV_COLUMNS["center_power_dbm"]: -21.7,
            CSV_COLUMNS["peak_frequency_hz"]: 9_999_000_000.0,
            CSV_COLUMNS["peak_power_dbm"]: -18.5,
        },
        {
            CSV_COLUMNS["timestamp"]: "2026-02-06T18:00:39+00:00",
            CSV_COLUMNS["cut_id"]: "coarse-az",
            CSV_COLUMNS["commanded_tilt"]: 1.0,
            CSV_COLUMNS["commanded_pan"]: -179.0,
            CSV_COLUMNS["commanded_elevation"]: 1.0,
            CSV_COLUMNS["commanded_azimuth"]: -179.0,
            CSV_COLUMNS["actual_tilt"]: 1.1,
            CSV_COLUMNS["actual_pan"]: -179.1,
            CSV_COLUMNS["actual_elevation"]: 1.1,
            CSV_COLUMNS["actual_azimuth"]: -179.1,
            CSV_COLUMNS["center_frequency_hz"]: 10_000_000_000.0,
            CSV_COLUMNS["center_power_dbm"]: -22.1,
            CSV_COLUMNS["peak_frequency_hz"]: 10_001_000_000.0,
            CSV_COLUMNS["peak_power_dbm"]: -18.1,
        },
        {
            CSV_COLUMNS["timestamp"]: "2026-02-06T18:00:40+00:00",
            CSV_COLUMNS["cut_id"]: "fine-pan",
            CSV_COLUMNS["commanded_tilt"]: 2.0,
            CSV_COLUMNS["commanded_pan"]: -90.0,
            CSV_COLUMNS["commanded_elevation"]: 2.0,
            CSV_COLUMNS["commanded_azimuth"]: -90.0,
            CSV_COLUMNS["actual_tilt"]: 2.1,
            CSV_COLUMNS["actual_pan"]: -90.1,
            CSV_COLUMNS["actual_elevation"]: 2.1,
            CSV_COLUMNS["actual_azimuth"]: -90.1,
            CSV_COLUMNS["center_frequency_hz"]: 10_000_000_000.0,
            CSV_COLUMNS["center_power_dbm"]: -20.1,
            CSV_COLUMNS["peak_frequency_hz"]: 10_002_000_000.0,
            CSV_COLUMNS["peak_power_dbm"]: -16.1,
        },
        {
            CSV_COLUMNS["timestamp"]: "2026-02-06T18:00:41+00:00",
            CSV_COLUMNS["cut_id"]: "fine-pan",
            CSV_COLUMNS["commanded_tilt"]: 3.0,
            CSV_COLUMNS["commanded_pan"]: -45.0,
            CSV_COLUMNS["commanded_elevation"]: 3.0,
            CSV_COLUMNS["commanded_azimuth"]: -45.0,
            CSV_COLUMNS["actual_tilt"]: 3.1,
            CSV_COLUMNS["actual_pan"]: -45.1,
            CSV_COLUMNS["actual_elevation"]: 3.1,
            CSV_COLUMNS["actual_azimuth"]: -45.1,
            CSV_COLUMNS["center_frequency_hz"]: 10_000_000_000.0,
            CSV_COLUMNS["center_power_dbm"]: -19.1,
            CSV_COLUMNS["peak_frequency_hz"]: 10_003_000_000.0,
            CSV_COLUMNS["peak_power_dbm"]: -15.1,
        },
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def sample_csv_path(tmp_path: Path, sample_rows_df: pd.DataFrame) -> Path:
    """Writes sample rows to a temporary CSV and returns its path."""
    path = tmp_path / "run_data.csv"
    sample_rows_df.to_csv(path, index=False)
    return path


@pytest.fixture
def app_instance(sample_csv_path: Path):
    """Creates a Dash app instance for callback tests."""
    return create_app(csv_path=sample_csv_path, poll_interval_ms=250)


@pytest.fixture
def callback_lookup(app_instance) -> Callable[[str], Callable[..., Any]]:
    """Returns a callback function lookup by wrapped function name."""

    def _lookup(name: str) -> Callable[..., Any]:
        for callback_def in app_instance.callback_map.values():
            callback = callback_def["callback"]
            wrapped = getattr(callback, "__wrapped__", None)
            if wrapped is not None and wrapped.__name__ == name:
                return wrapped
        raise KeyError(f"Callback not found: {name}")

    return _lookup
