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

You should verify that the tests pass before considering a task complete. If you cannot get the tests to pass, make that abundantly clear to the user.

## git

All work should be done on feature branches. When given a task, you will be on a branch that you should do all your work on.

You should make many git commits, at the completion of a task or a subtask. Creating many intermediate, "wip" commits are allowed and encouraged. You may `git status`, `git add`, `git commit` and `git push` at any point without asking for permission.

You may NEVER run `git push --force`.

You should not submit GitHub pull requests. The user will submit a PR when they think they should.

## pre-commit

We run pre-commit on all commits to do `ruff check --fix` and `ruff format`. Run this on all commits.

## Plan mode

At the start of every new conversation, before any analysis, tool call, or code change, if collaboration mode is not Plan, ask exactly: "Do you want to run this in Plan mode?" and wait for the user’s response. Do not proceed until they answer.