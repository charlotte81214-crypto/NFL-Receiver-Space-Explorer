"""
route_comparison.py  --  Route Runner Nearest-Defender Distance Tool
=====================================================================
Shows nearest-defender distance for every Pass Route player in one play,
from ball_snap through pass_forward, frame by frame.

Usage
-----
    .venv/bin/python route_comparison.py <gameId> <playId>

    Example:
        .venv/bin/python route_comparison.py 2021090900 97

Output (saved to outputs/<gameId>_<playId>/)
----------------------------------------------
    route_comparison.png          -- two-panel figure
    route_comparison_all_frames.csv  -- per-frame data, all receivers
    route_comparison_at_release.csv  -- one row per receiver at pass_forward

Limitations (printed at runtime and embedded in figures)
---------------------------------------------------------
    Nearest-defender distance is a geometric measurement only.
    It does NOT measure:
      - passing lane clearance
      - route depth or timing
      - quarterback pressure or pocket position
      - whether a defender is in man or zone coverage
    A larger value means more space from the nearest defender at that frame.
    It does not indicate a better or more likely passing option.

Notes
-----
    - Frame rate is not documented in this dataset; frame numbers are used
      throughout. Seconds are not shown.
    - x/y coordinates are in yards (field 0-120 x 0-53.3 per README).
    - Missing frames and NaN coordinates are reported and skipped, never filled.
    - Pass Route players and defensive team are read directly from the data;
      no hard-coded IDs or team names.
    - "nearest defender" = DAL/opposing player with smallest Euclidean distance
      to the receiver at that frame. May change frame-to-frame.
"""

import sys, math, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# ---- 0. Command-line arguments ----------------------------------------------
def usage_and_exit():
    print("Usage: .venv/bin/python route_comparison.py <gameId> <playId>")
    print("Example: .venv/bin/python route_comparison.py 2021090900 97")
    sys.exit(1)

if len(sys.argv) != 3:
    usage_and_exit()
try:
    GAME_ID = int(sys.argv[1])
    PLAY_ID = int(sys.argv[2])
except ValueError:
    print(f"Error: gameId and playId must be integers. Got: {sys.argv[1]!r}, {sys.argv[2]!r}")
    usage_and_exit()

DATA_DIR = "data"
OUT_DIR  = f"outputs/{GAME_ID}_{PLAY_ID}"
os.makedirs(OUT_DIR, exist_ok=True)

print(f"\n{'='*60}")
print(f"Route Comparison  --  gameId={GAME_ID}  playId={PLAY_ID}")
print(f"Output directory  :  {OUT_DIR}")
print(f"{'='*60}")

# ---- 1. Load data -----------------------------------------------------------
print("\nLoading data ...")
tracking_file = f"{DATA_DIR}/tracking/tracking_{GAME_ID}.csv"
if not os.path.exists(tracking_file):
    print(f"ERROR: tracking file not found: {tracking_file}")
    sys.exit(1)

tracking  = pd.read_csv(tracking_file)
players   = pd.read_csv(f"{DATA_DIR}/players.csv")
pff       = pd.read_csv(f"{DATA_DIR}/pffScoutingData.csv")
plays_df  = pd.read_csv(f"{DATA_DIR}/plays.csv")

# ---- 2. Verify this play exists --------------------------------------------
play_matches = plays_df[(plays_df["gameId"]==GAME_ID) & (plays_df["playId"]==PLAY_ID)]
if play_matches.empty:
    print(f"ERROR: gameId={GAME_ID}, playId={PLAY_ID} not found in plays.csv")
    sys.exit(1)
play_row    = play_matches.iloc[0]
desc        = play_row["playDescription"].strip()
pass_result = play_row["passResult"]
offense     = play_row["possessionTeam"]
defense     = play_row["defensiveTeam"]

print(f"\nPlay description : {desc}")
print(f"possessionTeam   : {offense}")
print(f"defensiveTeam    : {defense}  (used to identify defenders)")
print(f"passResult       : {pass_result}")

# ---- 3. Isolate tracking rows for this play --------------------------------
play_track = tracking[
    (tracking["gameId"]==GAME_ID) & (tracking["playId"]==PLAY_ID)
].copy()

if play_track.empty:
    print(f"ERROR: no tracking rows found for gameId={GAME_ID}, playId={PLAY_ID}")
    sys.exit(1)

# ---- 4. Event audit: ball_snap and pass_forward ----------------------------
def canonical_frame(event_name):
    """Return (first_frame, all_frames) for an event tag in this play."""
    rows = play_track[play_track["event"] == event_name]["frameId"]
    if rows.empty:
        return None, []
    return int(rows.min()), sorted(rows.unique().tolist())

snap_frame,  snap_all  = canonical_frame("ball_snap")
throw_frame, throw_all = canonical_frame("pass_forward")
arrival_frame, _       = canonical_frame("pass_arrived")

print(f"\nEvent audit:")
print(f"  ball_snap    : frame(s) {snap_all}  --> canonical = {snap_frame}")
print(f"  pass_forward : frame(s) {sorted(set(throw_all))[:6]}{'...' if len(set(throw_all))>6 else ''}  --> canonical = {throw_frame}")
if arrival_frame:
    print(f"  pass_arrived : frame {arrival_frame}")
else:
    print(f"  pass_arrived : ABSENT from tracking rows (passResult='{pass_result}' per plays.csv)")

# Guard: missing events
if snap_frame is None:
    print("ERROR: ball_snap event not found in tracking data for this play. Cannot proceed.")
    sys.exit(1)
if throw_frame is None:
    print("ERROR: pass_forward event not found in tracking data for this play.")
    print("  This play cannot be analysed with this tool.")
    print("  Possible reasons: play is a run, QB scramble, or event was not tagged.")
    sys.exit(1)

# Guard: pass_forward before snap (data anomaly)
if throw_frame <= snap_frame:
    print(f"ERROR: pass_forward (frame {throw_frame}) is not after ball_snap (frame {snap_frame}).")
    print("  Possible tagging anomaly. Cannot proceed.")
    sys.exit(1)

print(f"\nAnalysis window  : frames {snap_frame} (ball_snap) to {throw_frame} (pass_forward)")
print(f"Frame count      : {throw_frame - snap_frame + 1}")
print(f"Frame rate       : undocumented in dataset -- frame numbers used, not seconds")

# ---- 5. Identify Pass Route players for this play --------------------------
route_pff = pff[
    (pff["gameId"]==GAME_ID) & (pff["playId"]==PLAY_ID) &
    (pff["pff_role"]=="Pass Route")
][["nflId","pff_positionLinedUp"]].copy()

if route_pff.empty:
    print(f"ERROR: no Pass Route players found in pffScoutingData for this play.")
    sys.exit(1)

route_pff = route_pff.merge(
    players[["nflId","displayName","officialPosition"]],
    on="nflId", how="left"
)

print(f"\nPass Route players ({len(route_pff)}):")
for _, r in route_pff.iterrows():
    print(f"  nflId={int(r['nflId'])}  {r['displayName']}  "
          f"pos={r['officialPosition']}  lineup={r['pff_positionLinedUp']}")

# ---- 6. Missing-data audit --------------------------------------------------
expected_frames = set(range(snap_frame, throw_frame + 1))
def_rows = play_track[play_track["team"] == defense][["frameId","nflId","x","y"]]

print(f"\nMissing-data audit (expected frames {snap_frame}-{throw_frame}):")
any_missing = False

for _, rrow in route_pff.iterrows():
    nid = int(rrow["nflId"])
    window_frames_present = set(
        play_track[
            (play_track["nflId"]==nid) &
            (play_track["frameId"]>=snap_frame) &
            (play_track["frameId"]<=throw_frame)
        ]["frameId"].tolist()
    )
    missing = sorted(expected_frames - window_frames_present)
    w = play_track[
        (play_track["nflId"]==nid) &
        (play_track["frameId"]>=snap_frame) &
        (play_track["frameId"]<=throw_frame)
    ]
    nan_x = int(w["x"].isna().sum())
    nan_y = int(w["y"].isna().sum())
    status = "OK" if (not missing and nan_x==0 and nan_y==0) else "WARNING"
    print(f"  {str(rrow['displayName']):20s} frames={len(window_frames_present)}/{len(expected_frames)}"
          f"  missing={missing}  NaN_x={nan_x}  NaN_y={nan_y}  [{status}]")
    if status == "WARNING":
        any_missing = True

# Defenders
dal_frames_present = set(def_rows[
    (def_rows["frameId"]>=snap_frame) & (def_rows["frameId"]<=throw_frame)
]["frameId"].tolist())
dal_missing = sorted(expected_frames - dal_frames_present)
nan_dx = int(def_rows["x"].isna().sum())
nan_dy = int(def_rows["y"].isna().sum())
status = "OK" if (not dal_missing and nan_dx==0 and nan_dy==0) else "WARNING"
print(f"  {f'{defense} defenders':20s} frames={len(dal_frames_present)}/{len(expected_frames)}"
      f"  missing={dal_missing}  NaN_x={nan_dx}  NaN_y={nan_dy}  [{status}]")

if not any_missing and not dal_missing:
    print("  --> All data complete. No silent fill applied.")
else:
    print("  --> WARNING: gaps detected. Affected frames will be skipped and noted.")

# ---- 7. Compute nearest-defender distance per receiver per frame ------------
print(f"\nComputing nearest-defender distances ...")

all_results   = []
skipped_log   = []   # one entry per skipped (nflId, frame) pair

for _, rrow in route_pff.iterrows():
    nid   = int(rrow["nflId"])
    rname = str(rrow["displayName"])

    receiver_indexed = (
        play_track[
            (play_track["nflId"]==nid) &
            (play_track["frameId"]>=snap_frame) &
            (play_track["frameId"]<=throw_frame)
        ].set_index("frameId")
    )

    frame_skips = []
    for fid in range(snap_frame, throw_frame + 1):
        # Receiver coord check
        if fid not in receiver_indexed.index:
            frame_skips.append((fid, "receiver row absent"))
            continue
        rx = receiver_indexed.loc[fid, "x"]
        ry = receiver_indexed.loc[fid, "y"]
        if pd.isna(rx) or pd.isna(ry):
            frame_skips.append((fid, "receiver coord NaN"))
            continue

        # Defender check
        def_at_frame = def_rows[def_rows["frameId"]==fid].dropna(subset=["x","y"])
        if def_at_frame.empty:
            frame_skips.append((fid, f"no {defense} defenders with coords"))
            continue

        def_at_frame = def_at_frame.copy()
        def_at_frame["dist"] = (
            (def_at_frame["x"]-rx)**2 + (def_at_frame["y"]-ry)**2
        ).apply(math.sqrt)
        nearest = def_at_frame.loc[def_at_frame["dist"].idxmin()]

        all_results.append({
            "nflId":               nid,
            "name":                rname,
            "position":            str(rrow["officialPosition"]),
            "lineup_pos":          str(rrow["pff_positionLinedUp"]),
            "frameId":             fid,
            "receiver_x":          rx,
            "receiver_y":          ry,
            "nearest_def_id":      int(nearest["nflId"]),
            "nearest_def_x":       nearest["x"],
            "nearest_def_y":       nearest["y"],
            "nearest_def_dist_yd": nearest["dist"],
        })

    if frame_skips:
        for fid, reason in frame_skips:
            skipped_log.append({"nflId": nid, "name": rname, "frameId": fid, "reason": reason})
        print(f"  {rname}: SKIPPED {len(frame_skips)} frame(s): {frame_skips}")
    else:
        print(f"  {rname:20s} all {throw_frame-snap_frame+1} frames OK")

results_df = pd.DataFrame(all_results)

# Merge defender display names
def_id_set    = results_df["nearest_def_id"].unique()
def_name_map  = {
    int(r["nflId"]): r["displayName"]
    for _, r in players[players["nflId"].isin(def_id_set)].iterrows()
}
results_df["nearest_def_name"] = results_df["nearest_def_id"].map(def_name_map)

# ---- 8. At-release summary --------------------------------------------------
release_df = (
    results_df[results_df["frameId"]==throw_frame]
    [[
        "name","nflId","position","lineup_pos",
        "receiver_x","receiver_y",
        "nearest_def_id","nearest_def_name","nearest_def_x","nearest_def_y",
        "nearest_def_dist_yd",
    ]]
    .sort_values("nearest_def_dist_yd", ascending=False)
    .reset_index(drop=True)
)

# ---- 9. Verify at-release values --------------------------------------------
print(f"\nCoordinate verification at frame {throw_frame} (pass_forward):")
all_ok = True
for _, row in release_df.iterrows():
    dx = row["nearest_def_x"] - row["receiver_x"]
    dy = row["nearest_def_y"] - row["receiver_y"]
    recalc = math.sqrt(dx**2 + dy**2)
    match  = abs(recalc - row["nearest_def_dist_yd"]) < 1e-9
    status = "OK" if match else "MISMATCH"
    if not match:
        all_ok = False
    print(f"  {str(row['name']):20s}  "
          f"rcvr=({row['receiver_x']:.2f},{row['receiver_y']:.2f})  "
          f"def=({row['nearest_def_x']:.2f},{row['nearest_def_y']:.2f})  "
          f"sqrt({dx:.2f}^2+{dy:.2f}^2)={recalc:.4f}  "
          f"stored={row['nearest_def_dist_yd']:.4f}  [{status}]")
if all_ok:
    print("  --> All values verified.")
else:
    print("  --> MISMATCH detected. Check computation.")

# ---- 10. Print summary table ------------------------------------------------
print(f"\nNearest-defender distance at pass_forward (frame {throw_frame}):")
print(f"{'Receiver':20s}  {'Pos':4s}  {'Lineup':5s}  {'Dist (yd)':>9s}  Nearest defender")
print("-" * 72)
for _, row in release_df.iterrows():
    def_name = str(row["nearest_def_name"]) if pd.notna(row["nearest_def_name"]) else "unknown"
    print(f"  {str(row['name']):18s}  {str(row['position']):4s}  "
          f"{str(row['lineup_pos']):5s}  {row['nearest_def_dist_yd']:>9.2f}  {def_name}")
print()
print("  NOTE: nearest-defender distance does not measure passing lanes,")
print("  route depth, or QB pressure. A larger value does not indicate")
print("  a better or more likely passing option.")

# ---- 11. Save CSV outputs ---------------------------------------------------
full_csv    = f"{OUT_DIR}/route_comparison_all_frames.csv"
release_csv = f"{OUT_DIR}/route_comparison_at_release.csv"

results_df[[
    "nflId","name","position","lineup_pos","frameId",
    "receiver_x","receiver_y",
    "nearest_def_id","nearest_def_name","nearest_def_x","nearest_def_y",
    "nearest_def_dist_yd",
]].to_csv(full_csv, index=False)

release_df.to_csv(release_csv, index=False)

if skipped_log:
    skip_csv = f"{OUT_DIR}/skipped_frames.csv"
    pd.DataFrame(skipped_log).to_csv(skip_csv, index=False)
    print(f"Skipped frames CSV  -> {skip_csv}")

print(f"\nFull frame CSV      -> {full_csv}")
print(f"At-release CSV      -> {release_csv}")

# ---- 12. Colour palette (up to 8 receivers) --------------------------------
PALETTE = [
    "#FF6B6B","#E69F00","#56B4E9","#009E73",
    "#CC79A7","#F0E442","#0072B2","#D55E00",
]
nfl_ids   = route_pff["nflId"].astype(int).tolist()
color_map = {nid: PALETTE[i % len(PALETTE)] for i, nid in enumerate(nfl_ids)}

# ---- 13. Build figure -------------------------------------------------------
print("\nBuilding figure ...")

fig = plt.figure(figsize=(16, 9))
fig.patch.set_facecolor("#1a1a1a")
gs = fig.add_gridspec(1, 2, width_ratios=[1.6, 1.0], wspace=0.35)
ax_line = fig.add_subplot(gs[0])
ax_bar  = fig.add_subplot(gs[1])

# ---- Panel A: line chart ----------------------------------------------------
ax_line.set_facecolor("#121212")

for _, rrow in route_pff.iterrows():
    nid   = int(rrow["nflId"])
    pdata = results_df[results_df["nflId"]==nid].sort_values("frameId")
    if pdata.empty:
        continue
    color = color_map[nid]
    short = str(rrow["displayName"]).split()[-1]
    label = f"{short} ({rrow['pff_positionLinedUp']})"
    ax_line.plot(pdata["frameId"], pdata["nearest_def_dist_yd"],
                 color=color, linewidth=2.0, zorder=4, label=label)
    at_throw = pdata[pdata["frameId"]==throw_frame]
    if not at_throw.empty:
        v = float(at_throw["nearest_def_dist_yd"].iloc[0])
        ax_line.scatter([throw_frame], [v], color=color, s=100,
                        zorder=6, edgecolors="white", linewidths=0.8)

ax_line.axvline(snap_frame,  color="#AAAAAA", linewidth=1.0, linestyle=":",
                alpha=0.8, label=f"ball_snap (frame {snap_frame})")
ax_line.axvline(throw_frame, color="#FFD700", linewidth=1.5, linestyle="--",
                label=f"pass_forward (frame {throw_frame})")

ax_line.set_xlim(snap_frame - 0.5, throw_frame + 0.5)
ax_line.set_ylim(bottom=0)
ax_line.set_xlabel(
    "Frame number  (frame rate undocumented -- seconds not shown)",
    color="white", fontsize=9
)
ax_line.set_ylabel("Nearest-defender distance (yards)", color="white", fontsize=9)
ax_line.tick_params(colors="white")
for spine in ax_line.spines.values():
    spine.set_edgecolor("#555555")
ax_line.legend(loc="upper left", fontsize=8,
               facecolor="#1a1a1a", labelcolor="white", framealpha=0.9)
ax_line.set_title(
    f"Panel A: Nearest-Defender Distance by Frame\n"
    f"Play {PLAY_ID} ({offense} vs {defense})  |  "
    f"ball_snap to pass_forward  |  yards",
    color="white", fontsize=9, pad=8
)

# ---- Panel B: bar chart at pass_forward -------------------------------------
ax_bar.set_facecolor("#121212")

bar_order = release_df.sort_values("nearest_def_dist_yd", ascending=True)
names  = [f"{r['name'].split()[-1]}\n({r['lineup_pos']})"
          for _, r in bar_order.iterrows()]
values = bar_order["nearest_def_dist_yd"].values
colors = [color_map[int(r["nflId"])] for _, r in bar_order.iterrows()]

bars = ax_bar.barh(names, values, color=colors,
                   edgecolor="#333333", linewidth=0.8, height=0.55)

for bar, val in zip(bars, values):
    ax_bar.text(
        val + 0.06, bar.get_y() + bar.get_height()/2,
        f"{val:.2f} yd", va="center", ha="left",
        color="white", fontsize=8.5, fontweight="bold"
    )

for bar, (_, row) in zip(bars, bar_order.iterrows()):
    def_last = (str(row["nearest_def_name"]).split()[-1]
                if pd.notna(row["nearest_def_name"]) else "?")
    ax_bar.text(
        0.1, bar.get_y() + bar.get_height()/2,
        f"vs {def_last}", va="center", ha="left",
        color="#CCCCCC", fontsize=6.8, alpha=0.85
    )

ax_bar.set_xlabel("Nearest-defender distance (yards)", color="white", fontsize=9)
ax_bar.tick_params(colors="white")
ax_bar.tick_params(axis="y", labelsize=8)
for spine in ax_bar.spines.values():
    spine.set_edgecolor("#555555")
ax_bar.set_xlim(0, max(values) * 1.35)
ax_bar.set_title(
    f"Panel B: Nearest-Defender Distance at pass_forward\n"
    f"Frame {throw_frame}  |  sorted ascending  |  yards\n"
    "Larger value = more space from nearest defender only.",
    color="white", fontsize=9, pad=8
)

fig.text(
    0.98, 0.015,
    "Nearest-defender distance does not measure passing lanes,\n"
    "route depth, or QB pressure.",
    ha="right", va="bottom", color="#AAAAAA", fontsize=7, style="italic"
)

plt.suptitle(
    f"Route Runner Comparison  --  Game {GAME_ID}, Play {PLAY_ID}\n"
    f'"{desc}"',
    color="white", fontsize=9.5, y=1.01
)

out_fig = f"{OUT_DIR}/route_comparison.png"
plt.savefig(out_fig, dpi=150, bbox_inches="tight", facecolor="#1a1a1a")
plt.close()
print(f"Figure saved -> {out_fig}")
print(f"\nDone. All outputs in {OUT_DIR}/")
