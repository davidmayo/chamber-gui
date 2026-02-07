"""Package entrypoint for chamber GUI."""

from __future__ import annotations

import os
from pathlib import Path

from chamber_gui.app import create_app


def main() -> None:
    """Runs the chamber GUI app."""
    default_csv = Path("sample_data") / "run_data.csv"
    csv_path = Path(os.getenv("CHAMBER_GUI_CSV", str(default_csv)))
    poll_ms = int(os.getenv("CHAMBER_GUI_POLL_MS", "1000"))
    host = os.getenv("CHAMBER_GUI_HOST", "127.0.0.1")
    port = int(os.getenv("CHAMBER_GUI_PORT", "8050"))
    app = create_app(csv_path=csv_path, poll_interval_ms=poll_ms)
    app.run(host=host, port=port, debug=False, use_reloader=False)
