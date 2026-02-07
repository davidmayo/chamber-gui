# chamber-gui

GUI for monitoring Anechoic chamber RF antenna chamber test output from CSV files.

## Run The App

From the repository root:

```sh
uv run chamber-gui
```

The Dash server starts at:

- `http://127.0.0.1:8050/` by default

If port `8050` is busy, set another port:

```sh
$env:CHAMBER_GUI_PORT="8051"
uv run chamber-gui
```

## Configuration

Optional environment variables:

- `CHAMBER_GUI_CSV`
  - Path to the input CSV file.
  - Default: `sample_data/run_data.csv`
- `CHAMBER_GUI_POLL_MS`
  - Poll interval in milliseconds.
  - Default: `1000`
- `CHAMBER_GUI_HOST`
  - Bind host for the Dash server.
  - Default: `127.0.0.1`
- `CHAMBER_GUI_PORT`
  - Bind port for the Dash server.
  - Default: `8050`

Example with custom CSV and faster refresh:

```sh
$env:CHAMBER_GUI_CSV="sample_data/run_data.csv"
$env:CHAMBER_GUI_POLL_MS="500"
uv run chamber-gui
```