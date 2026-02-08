"""Tests for package entrypoint in chamber_gui.__init__."""

from __future__ import annotations

from pathlib import Path

import pytest

import chamber_gui


def test_main_uses_default_env_values(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeApp:
        def run(self, **kwargs):
            captured["run_kwargs"] = kwargs

    def _fake_create_app(csv_path: Path, poll_interval_ms: int):
        captured["csv_path"] = csv_path
        captured["poll_interval_ms"] = poll_interval_ms
        return FakeApp()

    monkeypatch.delenv("CHAMBER_GUI_CSV", raising=False)
    monkeypatch.delenv("CHAMBER_GUI_POLL_MS", raising=False)
    monkeypatch.delenv("CHAMBER_GUI_HOST", raising=False)
    monkeypatch.delenv("CHAMBER_GUI_PORT", raising=False)
    monkeypatch.setattr(chamber_gui, "create_app", _fake_create_app)

    chamber_gui.main()

    assert captured["csv_path"] == Path("sample_data") / "run_data.csv"
    assert captured["poll_interval_ms"] == 1000
    assert captured["run_kwargs"] == {
        "host": "127.0.0.1",
        "port": 8050,
        "debug": False,
        "use_reloader": False,
    }


def test_main_uses_custom_env_values(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeApp:
        def run(self, **kwargs):
            captured["run_kwargs"] = kwargs

    def _fake_create_app(csv_path: Path, poll_interval_ms: int):
        captured["csv_path"] = csv_path
        captured["poll_interval_ms"] = poll_interval_ms
        return FakeApp()

    monkeypatch.setenv("CHAMBER_GUI_CSV", "/tmp/custom.csv")
    monkeypatch.setenv("CHAMBER_GUI_POLL_MS", "250")
    monkeypatch.setenv("CHAMBER_GUI_HOST", "0.0.0.0")
    monkeypatch.setenv("CHAMBER_GUI_PORT", "9000")
    monkeypatch.setattr(chamber_gui, "create_app", _fake_create_app)

    chamber_gui.main()

    assert captured["csv_path"] == Path("/tmp/custom.csv")
    assert captured["poll_interval_ms"] == 250
    assert captured["run_kwargs"] == {
        "host": "0.0.0.0",
        "port": 9000,
        "debug": False,
        "use_reloader": False,
    }


def test_main_raises_for_invalid_integer_env(monkeypatch) -> None:
    monkeypatch.setenv("CHAMBER_GUI_POLL_MS", "invalid")
    with pytest.raises(ValueError):
        chamber_gui.main()
