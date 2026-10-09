# Submission Checklist

## Python scripts (required)

| File | Purpose |
|---|---|
| `viewer.py` | Interactive Flask viewer — main submission deliverable |
| `route_comparison.py` | Reusable CLI script; generates per-play CSVs and figures |
| `separation_explorer.py` | Single-play (play 97) separation analysis with audit trail |
| `plot_play.py` | Static field snapshot for play 97 at pass_forward |

## Documentation (required)

| File | Purpose |
|---|---|
| `SUBMISSION_README.md` | 5-sentence overview for judges |
| `RUN_INSTRUCTIONS.md` | Dependencies, data paths, exact launch commands |
| `DEMO_SCRIPT.md` | 60-second English walkthrough |
| `SUBMISSION_CHECKLIST.md` | This file |
| `ROUTE_COMPARISON_README.md` | Detailed tool documentation and limitations |

## Pre-generated outputs (include as evidence of prior verified runs)

```
outputs/
  2021090900_97/
    route_comparison.png
    route_comparison_all_frames.csv
    route_comparison_at_release.csv
  2021090900_410/
    route_comparison.png
    route_comparison_all_frames.csv
    route_comparison_at_release.csv
  2021090900_349/
    route_comparison.png
    route_comparison_all_frames.csv
    route_comparison_at_release.csv
  separation_explorer.png
  separation_data.csv
  separation_summary.json
play_97_snapshot.png
```

## Data files (required but NOT included in submission package)

The following files from the competition dataset must be present for the
tool to run. They are not submitted — judges supply their own copy.

```
data/
  games.csv
  plays.csv
  players.csv
  pffScoutingData.csv
  tracking/
    tracking_2021090900.csv
```

## Exclude from submission package

```
.venv/               (virtual environment — not portable)
__pycache__/         (Python bytecode cache)
data/                (competition data — not to be redistributed)
viewer_backup.py     (internal backup — not needed by judges)
```

## Screenshot checklist (take these manually before submitting)

1. Standard Mode — Play 97 at pass_forward (frame 40), showing all 5
   receivers, distance lines, and table with trend values.
2. Coach Review Mode — Play 97 at snap frame, description hidden.
3. Coach Review Mode — Play 97 at release frame, one receiver selected
   (highlighted dot and row).
4. Coach Review Mode — Play 97 after reveal, showing target and outcome.
5. Standard Mode — Play 349 (DAL), showing a different team as offense,
   confirming multi-team support.

## Notes on the dataset

- Data is from the 2021 NFL season (gameId 2021090900 = Sep 9, 2021).
- If event slide materials state "2023", that is a discrepancy in the
  event materials. The actual data supplied is 2021. Both documents
  (SUBMISSION_README.md and viewer.py header) note this.
- Frame rate is not documented in the supplied dataset README.
  Frame numbers are used throughout; no seconds conversion is applied.
- All coordinate distances are in yards (x: 0–120, y: 0–53.3).
