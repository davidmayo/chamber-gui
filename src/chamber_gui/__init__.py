"""Package entrypoint for chamber GUI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from chamber_gui.app import create_app


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses CLI args for chamber-gui."""
    parser = argparse.ArgumentParser(prog="chamber-gui")
    parser.add_argument(
        "--path",
        help="CSV file or folder path to monitor.",
    )
    args, _ = parser.parse_known_args(argv)
    return args


def main() -> None:
    """Runs the chamber GUI app."""
    default_csv = Path("sample_data") / "run_data.csv"
    args = _parse_args(sys.argv[1:])
    if args.path:
        csv_path = Path(args.path)
    else:
        csv_path = Path(os.getenv("CHAMBER_GUI_CSV", str(default_csv)))
    poll_ms = int(os.getenv("CHAMBER_GUI_POLL_MS", "1000"))
    host = os.getenv("CHAMBER_GUI_HOST", "127.0.0.1")
    port = int(os.getenv("CHAMBER_GUI_PORT", "8050"))
    app = create_app(csv_path=csv_path, poll_interval_ms=poll_ms)
    app.run(host=host, port=port, debug=False, use_reloader=False)
