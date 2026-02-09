"""Tests for replay CSV tool."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

import pandas as pd
import pytest

from chamber_gui.models import CSV_COLUMNS
import chamber_gui.replay_csv as replay_csv_module
from chamber_gui.replay_csv import replay_csv


def _write_sample_csv(path: Path) -> None:
    data = pd.DataFrame(
        [
            {
                CSV_COLUMNS["timestamp"]: "2026-02-01T12:00:00+00:00",
                CSV_COLUMNS["cut_id"]: "a",
                CSV_COLUMNS["peak_power_dbm"]: -10.0,
            },
            {
                CSV_COLUMNS["timestamp"]: "2026-02-01T12:00:10+00:00",
                CSV_COLUMNS["cut_id"]: "b",
                CSV_COLUMNS["peak_power_dbm"]: -11.0,
            },
        ]
    )
    data.to_csv(path, index=False)


def test_replay_csv_updates_timestamps(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    _write_sample_csv(input_path)
    output_path = tmp_path / "out" / "replay.csv"
    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)

    replay_csv(
        input_path=input_path,
        output_path=output_path,
        pave=False,
        speed=1.0,
        now=now,
        sleep_fn=lambda _: None,
    )

    result = pd.read_csv(output_path)
    timestamps = pd.to_datetime(result[CSV_COLUMNS["timestamp"]], utc=True)
    assert timestamps.iloc[0] == pd.Timestamp(now)
    assert timestamps.iloc[1] == pd.Timestamp(now) + pd.Timedelta(seconds=10)


def test_replay_csv_raises_when_output_exists_without_pave(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    _write_sample_csv(input_path)
    output_path = tmp_path / "out.csv"
    output_path.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        replay_csv(
            input_path=input_path,
            output_path=output_path,
            pave=False,
            now=datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC),
            sleep_fn=lambda _: None,
        )


def test_replay_csv_overwrites_when_pave(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    _write_sample_csv(input_path)
    output_path = tmp_path / "out.csv"
    output_path.write_text("existing", encoding="utf-8")

    replay_csv(
        input_path=input_path,
        output_path=output_path,
        pave=True,
        now=datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC),
        sleep_fn=lambda _: None,
    )

    result = pd.read_csv(output_path)
    assert len(result.index) == 2


def test_replay_csv_sleeps_for_timestamp_deltas(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    _write_sample_csv(input_path)
    output_path = tmp_path / "out.csv"
    sleeps: list[float] = []

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    replay_csv(
        input_path=input_path,
        output_path=output_path,
        pave=False,
        now=datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC),
        sleep_fn=_sleep,
    )

    assert sleeps == [10.0]


def test_replay_csv_scales_sleep_by_speed(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    _write_sample_csv(input_path)
    output_path = tmp_path / "out.csv"
    sleeps: list[float] = []

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    replay_csv(
        input_path=input_path,
        output_path=output_path,
        pave=False,
        speed=4.0,
        now=datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC),
        sleep_fn=_sleep,
    )

    assert sleeps == [2.5]


@pytest.mark.parametrize(
    "speed",
    [0.0, -1.0, float("nan"), float("inf")],
)
def test_replay_csv_rejects_invalid_speed(tmp_path: Path, speed: float) -> None:
    input_path = tmp_path / "input.csv"
    _write_sample_csv(input_path)
    output_path = tmp_path / "out.csv"

    with pytest.raises(ValueError, match="finite positive number"):
        replay_csv(
            input_path=input_path,
            output_path=output_path,
            pave=False,
            speed=speed,
            now=datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC),
            sleep_fn=lambda _: None,
        )


def test_main_passes_speed_to_replay_csv(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_replay_csv(**kwargs: object) -> None:
        captured.update(kwargs)

    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "replay-csv",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--speed",
            "4",
        ],
    )
    monkeypatch.setattr(replay_csv_module, "replay_csv", _fake_replay_csv)

    replay_csv_module.main()

    assert captured["input_path"] == input_path
    assert captured["output_path"] == output_path
    assert captured["speed"] == 4.0
