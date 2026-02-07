# Overview

We are building a GUI to monitor an industrial RF antenna testing testing device. The device is a turntable that can rotate an antenna and measure its received power at various frequencies.

## Method

The device is controlled by other means. It outputs several constantly updating CSV files as it conducts a test. We will montior these CSV files for changes, and when a change is observed, we will update the GUI. There is a sample of the kind of CSV that will be generated at `sample_data\run_data.csv`

## GUI

The GUI should be mostly graphs using Plotly Dash. There is a `design` folder that has a `design\rough_mockup.png` that shows sort of what the final product should look like, though it's not aesthstically pleasing. It should update as new values are detected in the CSV.

## Miscellaneous

We write Python according to the Google Style Guide.

We use uv to manage dependencies and run the app. `uv add`  for a new dependency, `uv run python /path/to/file.py` to run a Python file, `uv run pytest` to run tests.

You may add Python dependencies as needed.

We target Python 3.14+ only. We target Windows, Linux, and Mac.
