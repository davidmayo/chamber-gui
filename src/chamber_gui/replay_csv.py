"""Replay CSV data with updated timestamps."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys
import csv
import math
import time
from collections.abc import Callable

import pandas as pd

from chamber_gui.models import CSV_COLUMNS


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses CLI args for replay-csv."""
    parser = argparse.ArgumentParser(prog="replay-csv")
    parser.add_argument(
        "--input",
        required=True,
        help="Input CSV path to read.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV path to write.",
    )
    parser.add_argument(
        "--pave",
        action="store_true",
        help="Overwrite output if it already exists.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help=(
            "Replay speed multiplier; >1 is faster, <1 is slower. "
            "Must be a finite positive number."
        ),
    )
    args = parser.parse_args(argv)
    return args


def _read_rows(input_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with input_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    return rows, fieldnames


def _parse_timestamp(value: str) -> pd.Timestamp:
    return pd.to_datetime(value, utc=True)


def _format_timestamp(value: pd.Timestamp) -> str:
    return value.isoformat()


def replay_csv(
    *,
    input_path: Path,
    output_path: Path,
    pave: bool = False,
    speed: float = 1.0,
    now: datetime | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> None:
    """Reads input CSV and writes a replayed CSV with updated timestamps."""
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("Replay speed must be a finite positive number.")

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    print(f"Reading `{input_path}` . . .")
    rows, fieldnames = _read_rows(input_path)
    row_count = len(rows)
    if row_count == 0:
        raise ValueError(f"Input CSV has no rows: {input_path}")

    timestamp_field = CSV_COLUMNS["timestamp"]
    if timestamp_field not in fieldnames:
        raise ValueError(
            f"Missing timestamp column '{timestamp_field}' in {input_path}"
        )

    timestamps = [_parse_timestamp(row[timestamp_field]) for row in rows]
    first_ts = timestamps[0]
    last_ts = timestamps[-1]
    duration = last_ts - first_ts
    duration_seconds = int(duration.total_seconds())
    print(f"Contains {row_count} rows, with a duration of {duration_seconds} seconds.")

    current_time = now or datetime.now(tz=UTC)
    current_ts = pd.Timestamp(current_time)
    offset = current_ts - first_ts
    print(
        "Current time: "
        f"{_format_timestamp(pd.Timestamp(current_time))}. "
        "CSV time: "
        f"{_format_timestamp(first_ts)} "
        f"Time offset: {offset}"
    )

    output_dir = output_path.parent
    if not output_dir.exists():
        print(f"Folder {output_dir} does not exist. Creating it now.")
        output_dir.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        if pave:
            output_path.unlink()
        else:
            raise FileExistsError(f"Output file already exists: {output_path}")

    if not output_path.exists():
        print(f"File {output_path} does not exist. Creating it now.")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

    sleep_impl = sleep_fn or time.sleep
    for idx, row in enumerate(rows, start=1):
        original_ts = timestamps[idx - 1]
        if idx > 1:
            delta_seconds = (original_ts - timestamps[idx - 2]).total_seconds()
            if delta_seconds > 0:
                sleep_impl(delta_seconds / speed)
        new_ts = original_ts + offset
        row[timestamp_field] = _format_timestamp(new_ts)
        with output_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writerow(row)
        print(f"  Replaying line {idx} of {row_count}")


def main() -> None:
    """CLI entrypoint for replay-csv."""
    args = _parse_args(sys.argv[1:])
    replay_csv(
        input_path=Path(args.input),
        output_path=Path(args.output),
        pave=args.pave,
        speed=args.speed,
    )


__all__ = ["main", "replay_csv"]
