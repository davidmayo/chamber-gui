"""Tests for replay CSV tool."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from chamber_gui.models import CSV_COLUMNS
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
