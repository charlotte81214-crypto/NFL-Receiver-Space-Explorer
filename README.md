# NFL Route Runner Nearest-Defender Distance Viewer

We built an interactive web tool that visualises nearest-defender distance
for every receiver running a route in a play, frame by frame from the snap
through the moment of release, using player tracking coordinates from the
2021 NFL Big Data Bowl dataset (game 2021090900, Sep 9 2021; note: if event
materials state "2023", that is a discrepancy — the supplied data is 2021).
The tool reveals how much geometric space each receiver had relative to the
closest opposing player at each frame, and whether that space was growing or
shrinking over the preceding five frames, supporting discussion of route
spacing and defensive coverage patterns. It is intended for coaches,
analysts, and educators who want to examine receiver space in a play without
immediately knowing the outcome — a "Coach Review Mode" hides the play
description and result until the user chooses to reveal them, allowing
examination of the spatial picture before hindsight shapes the discussion
(this is a design intention, not a proven training benefit). This is a
prototype demonstrated on three plays from one game; nearest-defender
distance is a geometric measurement only and does not capture passing lanes,
route depth, quarterback pressure, or scheme assignments, so no conclusions
about passing decisions can be drawn from it alone.

---

## Screenshots

**Coach Review Mode — before reveal** (play description, outcome, and defender
names hidden):

![Before reveal](screenshots/before_reveal.png)

**Coach Review Mode — after reveal** (target matched from the play description,
outcome read from `plays.csv`):

![After reveal](screenshots/after_reveal.png)

---

## Features

- **Equal-scale SVG field** — player positions are plotted in yards on a
  proportionally accurate field (120 × 53.3 yd). Field scaling is preserved
  at all window sizes.
- **Nearest-defender distance** — dashed coloured line from each route runner
  to the closest opposing player, with the distance in yards labelled beside
  the line. Receiver names appear above each dot, clear of the distance labels.
- **5-frame trend** — table column showing whether each receiver's distance
  from the nearest defender is increasing, decreasing, or unchanged compared
  to five frames earlier. Reports N/A when the earlier frame is outside the
  analysed window.
- **Frame slider and animation** — scrub manually or click Play to animate
  from snap to release at illustrative speed (not verified real-time).
  Animation auto-pauses at the release frame.
- **Coach Review Mode** — hides the play description, pass outcome, and
  defender names before the user clicks Reveal. Receiver names remain visible.
  Selecting a receiver highlights their dot, distance line, and table row.
  Reveal reads outcome from `plays.csv`; target is matched from the play
  description text (shown as "not verified" if ambiguous).
- **Three demonstrated plays** from game 2021090900 (TB vs DAL, Week 1 2021):

  | Play | Offense | Result | Route runners | Frames analysed |
  |---|---|---|---|---|
  | 97 | TB | Incomplete | 5 | 35 |
  | 410 | TB | Complete | 5 | 17 |
  | 349 | DAL | Incomplete | 4 | 27 |

---

## Setup and launch

Run these commands from the project root (requires Python 3.11 or later).
Place the competition data files in `data/` first (see
[Data requirements](#data-requirements) below).

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python viewer.py
```

Then open your browser to:

```
http://127.0.0.1:5050
```

To stop the server: press **Ctrl+C** in the terminal.

**If port 5050 is occupied**, launch on port 5051 instead:

```
.venv/bin/python -c 'from viewer import app; app.run(host="127.0.0.1", port=5051, debug=False)'
```

Then open:

```
http://127.0.0.1:5051
```

> For full setup instructions including `uv` and running the static
> analysis scripts, see **[RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md)**.

---

## Data requirements

The code reads exactly four CSV files from the competition dataset. They are
not included in this repository and must be placed in `data/` before running:

```
data/
  plays.csv
  players.csv
  pffScoutingData.csv
  tracking/
    tracking_2021090900.csv
```

These are the only files any script opens (confirmed from the `pd.read_csv`
calls in `viewer.py`, `route_comparison.py`, `separation_explorer.py`, and
`plot_play.py`). `games.csv` is **not** read by the code — it is referenced
only in [DATA_DICTIONARY.md](DATA_DICTIONARY.md) as part of the dataset
documentation.

The viewer reads defensive team and Pass Route players directly from
`plays.csv` and `pffScoutingData.csv` — no player IDs or team names are
hard-coded. All coordinates are in yards (x: 0–120, y: 0–53.3).

---

## Limitations

- **Nearest-defender distance is geometric only.** It does not measure
  passing lanes, route depth, quarterback pressure, or whether the
  receiver was reachable from the QB's position.
- **Nearest defender is not the assigned coverage defender.** The closest
  opposing player by distance may be there due to zone coverage, pursuit,
  or coincidence. The nearest defender can also change from frame to frame.
- **5-frame trend is descriptive.** It measures distance change over five
  frame IDs only. The defender involved may differ between the two frames.
  It is not a speed or separation score.
- **Frame rate is undocumented.** The dataset README does not state a frame
  rate. Frame numbers are used throughout; no conversion to seconds is applied.
  Playback speed is for visualisation only and is not verified real-time speed.
- **Prototype scope.** Demonstrated on three plays from one 2021 game. No
  claim is made about generalisability to other games, seasons, or situations.
- **pass_arrived absence.** For incomplete passes, the `pass_arrived` event
  tag does not appear in the tracking rows. The pass outcome is read from
  `plays.csv` as an independent source; the two are not conflated.
- **No causal claims.** Separation distance alone does not explain why a
  pass succeeded or failed. No receiver is labelled as the best passing option.

---

## Project files

| File | Purpose |
|---|---|
| `viewer.py` | Interactive Flask viewer — main deliverable |
| `route_comparison.py` | CLI script; produces per-play CSVs and figures |
| `separation_explorer.py` | Single-play separation analysis with audit trail (play 97) |
| `plot_play.py` | Static field snapshot for play 97 at pass_forward |
| `requirements.txt` | Python package dependencies |

---

## Documentation

| Document | Contents |
|---|---|
| [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) | Dependencies, data paths, exact launch commands |
| [SUBMISSION_README.md](SUBMISSION_README.md) | 5-sentence project summary for judges |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | 60-second English walkthrough |
| [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) | File list, data requirements, screenshot checklist |
| [ROUTE_COMPARISON_README.md](ROUTE_COMPARISON_README.md) | Detailed tool documentation and limitations |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Original competition dataset column definitions |

---

## Pre-generated outputs

The `outputs/` folder contains figures and CSVs from verified prior runs:

```
outputs/
  2021090900_97/    route_comparison.png, *_all_frames.csv, *_at_release.csv
  2021090900_410/   route_comparison.png, *_all_frames.csv, *_at_release.csv
  2021090900_349/   route_comparison.png, *_all_frames.csv, *_at_release.csv
  separation_explorer.png
  separation_data.csv
  separation_summary.json
play_97_snapshot.png
```

Verified distances at pass_forward for play 97, frame 40 (read from saved CSV):

| Receiver | Distance (yd) | Nearest defender |
|---|---|---|
| Mike Evans | 6.90 | Trevon Diggs |
| Giovani Bernard | 5.88 | Osa Odighizuwa |
| Rob Gronkowski | 1.91 | Keanu Neal |
| Antonio Brown | 1.74 | Anthony Brown |
| Chris Godwin | 1.49 | Jourdan Lewis |
