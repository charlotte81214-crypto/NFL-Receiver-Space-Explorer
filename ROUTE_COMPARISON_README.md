# Route Runner Nearest-Defender Distance Tool

## What it does

For a single NFL play, this tool measures how far each receiver running a
route was from the nearest defensive player — frame by frame, from the snap
through the moment the ball is released.

It produces:

- **A line chart** showing each receiver's nearest-defender distance across
  every frame from `ball_snap` to `pass_forward`.
- **A bar chart** showing that distance at the moment of release
  (`pass_forward`), sorted from smallest to largest.
- **Two CSV files**: one with all per-frame data, one summarising the
  at-release values.

The metric is labelled **nearest-defender distance** throughout.

---

## Run command

```
.venv/bin/python route_comparison.py <gameId> <playId>
```

**Examples run in this project:**

```
.venv/bin/python route_comparison.py 2021090900 97
.venv/bin/python route_comparison.py 2021090900 410
.venv/bin/python route_comparison.py 2021090900 349
```

Each run saves its outputs to `outputs/<gameId>_<playId>/` and does not
overwrite any other play's files.

---

## Output files

```
outputs/<gameId>_<playId>/
    route_comparison.png             two-panel figure
    route_comparison_all_frames.csv  per-frame data for all receivers
    route_comparison_at_release.csv  one row per receiver at pass_forward
    skipped_frames.csv               only created if frames were skipped
```

**CSV columns (at-release file):**

| Column | Description |
|---|---|
| `name` | Receiver display name |
| `nflId` | Unique player identifier |
| `position` | Official position (WR, TE, RB, …) |
| `lineup_pos` | Position lined up at snap per PFF |
| `receiver_x / _y` | Receiver coordinates (yards) |
| `nearest_def_id` | nflId of nearest defensive player |
| `nearest_def_name` | Name of nearest defensive player |
| `nearest_def_x / _y` | Defender coordinates (yards) |
| `nearest_def_dist_yd` | Euclidean distance (yards) |

---

## Who would use this

- **Hackathon analysts** wanting a quick per-play picture of route spacing.
- **Coaching staff** looking at film to see which routes created space at
  the release point.
- **Researchers** building features for pass-outcome models who want a
  starting-point distance metric.

---

## Limitations

**Read these before drawing conclusions.**

1. **Nearest-defender distance is not a passing grade.**
   A larger distance means more space from the closest defender at that frame.
   It does not mean the receiver was open, catchable, or the intended target.
   It does not account for route depth, timing, the ball's air distance, or
   whether the receiver was even in the quarterback's field of view.

2. **It does not measure passing lanes.**
   A defender between the quarterback and receiver would not necessarily
   appear as the nearest defender to the receiver.

3. **It does not measure quarterback pressure.**
   A receiver may have 8 yards of space while the QB is about to be sacked.
   These two facts are independent in the data.

4. **The nearest defender changes frame to frame.**
   The identity of the nearest defender may be different at frame 10 versus
   frame 20. This is reported in the CSV (`nearest_def_name` column) and
   annotated in the line chart.

5. **"Nearest defender" is not the assigned coverage defender.**
   Zone and man assignments are not encoded in this metric. A defender
   nearby may be there because of scheme, pursuit, or coincidence.

6. **Frame rate is undocumented.**
   The README for this dataset does not state a frame rate. Frame numbers
   are used on all axes; seconds are not shown. Do not convert frames to
   time without a verified source.

7. **Plays without `pass_forward` are skipped.**
   The tool exits with an error message for runs, scrambles, sacks, and any
   play where the `pass_forward` event tag is absent from the tracking data.

8. **Coordinate units are yards.**
   Confirmed from the dataset README: x spans 0–120 yards (field length),
   y spans 0–53.3 yards (field width). All distances are in yards.

---

## Data sources used

| File | Purpose |
|---|---|
| `data/tracking/tracking_<gameId>.csv` | Player x/y coordinates per frame |
| `data/pffScoutingData.csv` | Identifies Pass Route players per play |
| `data/plays.csv` | Offensive and defensive team, pass result |
| `data/players.csv` | Player names by nflId |

---

## Reproducing the verified values

The script prints raw coordinates and a step-by-step distance calculation
for every receiver at `pass_forward` on every run. Example output:

```
  Mike Evans  rcvr=(46.61,31.87)  def=(50.26,26.02)
              sqrt(3.65^2 + -5.85^2) = 6.8953  stored=6.8953  [OK]
```

All three plays verified clean on the runs saved in `outputs/`.
