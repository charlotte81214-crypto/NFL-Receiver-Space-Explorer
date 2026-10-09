# Run Instructions

## Requirements

- Python 3.11 or later
- The data files supplied with the competition (see Data section below)

## Fresh-machine setup

Run these commands from the project root. This creates a virtual
environment, installs dependencies from `requirements.txt`, and starts the
viewer. The setup does not assume `.venv` already exists.

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python viewer.py
```

Then open your browser to:

    http://127.0.0.1:5050

To stop the server: press **Ctrl+C** in the terminal.

## Dependencies

`requirements.txt` lists three third-party packages:

- `pandas` — used by all scripts
- `matplotlib` — used by `plot_play.py`, `separation_explorer.py`, `route_comparison.py`
- `flask` — used by `viewer.py` only

No other external dependencies are needed. (Standard-library modules used:
`math`, `json`, `re`, `sys`, `os`.)

## Data files required

The code reads exactly four CSV files. They must be present at these paths
relative to the project root:

```
data/
  plays.csv
  players.csv
  pffScoutingData.csv
  tracking/
    tracking_2021090900.csv   (required for all three demonstrated plays)
```

These are confirmed from the `pd.read_csv` calls in `viewer.py`,
`route_comparison.py`, `separation_explorer.py`, and `plot_play.py`.
`games.csv` is **not** read by any script; it appears only in the dataset
documentation (DATA_DICTIONARY.md).

These are the original competition data files. They are not included in the
submission package. Place them in the `data/` folder before running.

## Launch the interactive viewer

From inside the project folder:

```
.venv/bin/python viewer.py
```

Then open your browser to:

    http://127.0.0.1:5050

To stop the server: press **Ctrl+C** in the terminal.

If the server is already running from a previous session, press Ctrl+C first
to stop it, then run the command above again.

### If port 5050 is occupied

Launch the same app on port 5051 instead:

```
.venv/bin/python -c 'from viewer import app; app.run(host="127.0.0.1", port=5051, debug=False)'
```

Then open:

    http://127.0.0.1:5051

## Run the static analysis scripts

These produce the figures and CSV files in `outputs/`:

```
.venv/bin/python plot_play.py
.venv/bin/python separation_explorer.py
.venv/bin/python route_comparison.py 2021090900 97
.venv/bin/python route_comparison.py 2021090900 410
.venv/bin/python route_comparison.py 2021090900 349
```

Each script must be run from the project root folder (the same folder that
contains `data/`).

## Notes

- Python version: confirmed working with 3.11.
- The `route_comparison.py` script accepts any gameId and playId as
  arguments, provided the tracking file for that game exists in `data/tracking/`.
- Frame rate is not documented in the supplied dataset. Frame numbers are
  used throughout; no conversion to seconds is applied.
- All coordinates are in yards (field 0–120 × 0–53.3 per dataset README).
