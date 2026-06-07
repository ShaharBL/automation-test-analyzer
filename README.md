# Automation Test Analyzer

Parses NUnit `.trx` (Test Results XML) files and renders an interactive HTML
dashboard showing the **chronological** order in which tests ran in the pipeline,
so you can see whether a failure happened on its own or after another test left
the system in a bad state (test pollution).

## What you get

- Summary cards: total / passed / failed / skipped / wall-clock duration
- Gantt-style timeline of every test (color-coded by outcome), sorted by start time
- Hover tooltips with test name, outcome, duration, start/end, truncated error
- A failures table below the timeline with full error message + collapsible stack trace
- One tab per `.trx` file when you drop multiple files in `input/`

The output is a single standalone HTML file — no server needed.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS / Linux
pip install -r requirements.txt
```

## Usage

1. Drop one or more `.trx` files into `input/`.
2. Run:

   ```bash
   python -m src.main
   ```

3. The script writes `output/dashboard.html` and opens it in your default browser.

## Project layout

```
input/                  # drop .trx files here
output/                 # generated dashboard.html (gitignored)
src/
  models.py             # TestResult / TestRun dataclasses
  parser.py             # .trx XML → TestRun
  dashboard.py          # Plotly timeline + Jinja2 HTML composition
  templates/
    dashboard.html.j2
  main.py               # entry point
```
