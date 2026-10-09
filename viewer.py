"""
viewer.py  --  Route Comparison Viewer with Coach Review Mode
=============================================================
Local web app (Flask) for exploring nearest-defender distance
across plays 97, 410, and 349 from game 2021090900 (2021 season).

NOTE ON DATASET SEASON:
  The tracking data gameId 2021090900 is from Sep 9, 2021 (2021 NFL season).
  If this event's slide deck says "2023", that is a discrepancy in the event
  materials. The actual data supplied is 2021.

Two modes
---------
  Standard Mode  : existing viewer — play, slider, field, table.
  Coach Review   : hides target/outcome/description before reveal.
                   Designed to let a reviewer examine receiver space
                   before seeing the actual outcome (less hindsight).
                   This is a design intention, not a proven training benefit.

Nearest-defender distance
-------------------------
  Euclidean distance to the closest opposing-team player at each frame.
  Does NOT measure passing lanes, route depth, or QB pressure.
  A larger value is not labelled as a better passing option.
  Nearest defender may change frame-to-frame and is not the
  scheme-assigned coverage defender.

5-frame trend
-------------
  Change in nearest-defender distance from (frameId - 5) to frameId.
  Descriptive only. Defender identity may differ between the two frames.
  Reported as N/A if either frame is outside the analyzed window.

Frame rate
----------
  Undocumented in the supplied dataset README.
  Frame numbers are used throughout; seconds are not shown.

Coordinates: yards (x 0-120, y 0-53.3 per dataset README).

Launch:
    .venv/bin/python viewer.py
Then open:  http://127.0.0.1:5050

Dependencies (all in .venv): flask, pandas
"""

import math, json, re
import pandas as pd
from flask import Flask, jsonify, render_template_string

# ── Data paths ────────────────────────────────────────────────────────────────
DATA_DIR  = "data"
GAME_ID   = 2021090900
PLAY_IDS  = [97, 410, 349]
TREND_GAP = 5          # frames back for the distance-change calculation

# Colourblind-friendly palette; consistent per nflId across all plays
PALETTE = ["#FF6B6B","#E69F00","#56B4E9","#009E73","#CC79A7",
           "#F0E442","#0072B2","#D55E00"]

# ── Pre-load all data once at startup ─────────────────────────────────────────
print("Loading data ...")
_tracking = pd.read_csv(f"{DATA_DIR}/tracking/tracking_{GAME_ID}.csv")
_players  = pd.read_csv(f"{DATA_DIR}/players.csv")
_pff      = pd.read_csv(f"{DATA_DIR}/pffScoutingData.csv")
_plays    = pd.read_csv(f"{DATA_DIR}/plays.csv")

def _name(nfl_id):
    rows = _players[_players["nflId"] == nfl_id]
    return str(rows["displayName"].iloc[0]) if len(rows) else f"#{nfl_id}"

def _identify_target(desc, route_names):
    """
    Try to match the play description to a route runner unambiguously.
    Looks for patterns like 'to C.Godwin' or 'to A.Cooper'.
    Returns (display_name, nflId) if exactly one match; None otherwise.
    Caller must pass route_names as list of (displayName, nflId).
    """
    # Extract 'FirstInitial.LastName' tokens from description
    tokens = re.findall(r'[A-Z]\.[A-Z][a-zA-Z\'\-]+', desc)
    matches = []
    for tok in tokens:
        initial = tok[0]
        last    = tok[2:]
        for name, nid in route_names:
            parts = name.split()
            if len(parts) >= 2:
                if parts[-1].lower() == last.lower() and parts[0][0].upper() == initial:
                    matches.append((name, nid))
    # Deduplicate
    seen = set()
    unique = []
    for m in matches:
        if m[1] not in seen:
            seen.add(m[1])
            unique.append(m)
    if len(unique) == 1:
        return unique[0]
    return None   # ambiguous or no match

def _build_play_data(play_id):
    """
    Return a dict with all frame data needed by the viewer.
    Mirrors the verified logic in route_comparison.py exactly.
    Adds: 5-frame trend per receiver, target identification for Coach Review.
    """
    play_row = _plays[(_plays["gameId"]==GAME_ID) & (_plays["playId"]==play_id)].iloc[0]
    defense  = str(play_row["defensiveTeam"])
    offense  = str(play_row["possessionTeam"])
    desc     = str(play_row["playDescription"]).strip()
    pass_res = str(play_row["passResult"])

    track = _tracking[(_tracking["gameId"]==GAME_ID) &
                      (_tracking["playId"]==play_id)].copy()

    def first_frame(ev):
        rows = track[track["event"]==ev]["frameId"]
        return int(rows.min()) if not rows.empty else None

    snap_frame  = first_frame("ball_snap")
    throw_frame = first_frame("pass_forward")

    # Route runners from pffScoutingData — not hard-coded
    route_rows = (_pff[(_pff["gameId"]==GAME_ID) & (_pff["playId"]==play_id) &
                       (_pff["pff_role"]=="Pass Route")]
                  [["nflId","pff_positionLinedUp"]])
    route_ids  = route_rows["nflId"].astype(int).tolist()
    route_names = [(_name(nid), nid) for nid in route_ids]

    # Try to identify target from play description (Coach Review reveal)
    target_match = _identify_target(desc, route_names)
    target_nfl_id   = target_match[1] if target_match else None
    target_name     = target_match[0] if target_match else None
    target_verified = target_match is not None

    # Consistent colours by list position
    color_map = {nid: PALETTE[i % len(PALETTE)] for i, nid in enumerate(route_ids)}

    # PFF roles for non-route players (rendering only)
    role_map = {int(r["nflId"]): str(r["pff_role"])
                for _, r in _pff[(_pff["gameId"]==GAME_ID) &
                                  (_pff["playId"]==play_id)].iterrows()}

    # Defender rows
    def_rows = track[track["team"]==defense][["frameId","nflId","x","y"]]

    # Pre-compute nearest-defender distances for ALL frames in window
    # so we can look up the 5-frame-ago value efficiently
    all_dists = {}   # {(nflId, frameId): dist_or_None}
    for fid in range(snap_frame, throw_frame + 1):
        def_at = def_rows[def_rows["frameId"]==fid].dropna(subset=["x","y"])
        for nid in route_ids:
            rcvr = track[(track["nflId"]==nid) & (track["frameId"]==fid)]
            if rcvr.empty or def_at.empty:
                all_dists[(nid, fid)] = None
                continue
            rx = float(rcvr.iloc[0]["x"])
            ry = float(rcvr.iloc[0]["y"])
            tmp = def_at.copy()
            tmp["dist"] = ((tmp["x"]-rx)**2 + (tmp["y"]-ry)**2).apply(math.sqrt)
            all_dists[(nid, fid)] = float(tmp["dist"].min())

    # Build per-frame snapshots
    frames = {}
    for fid in range(snap_frame, throw_frame + 1):
        fdata = track[track["frameId"]==fid]
        def_at_frame = def_rows[def_rows["frameId"]==fid].dropna(subset=["x","y"])

        # All players + ball
        players_out = []
        for _, row in fdata.iterrows():
            nid_raw = row["nflId"]
            team    = str(row["team"])
            is_ball = (team == "football")
            nid_int = int(nid_raw) if not (isinstance(nid_raw, float) and math.isnan(nid_raw)) else None
            players_out.append({
                "nflId":    nid_int,
                "team":     team,
                "x":        float(row["x"]),
                "y":        float(row["y"]),
                "is_ball":  is_ball,
                "role":     role_map.get(nid_int, "Ball" if is_ball else "Other"),
                "name":     "Ball" if is_ball else _name(nid_int),
                "is_route": (nid_int in route_ids),
                "color":    (color_map[nid_int] if nid_int in color_map else None),
                "is_target": (nid_int == target_nfl_id),
            })

        # Nearest-defender separations + 5-frame trend
        separations = []
        for nid in route_ids:
            rcvr = fdata[fdata["nflId"]==nid]
            if rcvr.empty or def_at_frame.empty:
                separations.append({
                    "nflId": nid, "name": _name(nid),
                    "lineup": str(route_rows[route_rows["nflId"]==nid]["pff_positionLinedUp"].iloc[0]),
                    "color": color_map[nid],
                    "dist": None, "def_x": None, "def_y": None,
                    "def_name": None, "rcvr_x": None, "rcvr_y": None,
                    "skipped": True,
                    "trend": None, "trend_label": "N/A",
                    "is_target": (nid == target_nfl_id),
                })
                continue

            rx = float(rcvr.iloc[0]["x"])
            ry = float(rcvr.iloc[0]["y"])
            tmp = def_at_frame.copy()
            tmp["dist"] = ((tmp["x"]-rx)**2 + (tmp["y"]-ry)**2).apply(math.sqrt)
            nearest = tmp.loc[tmp["dist"].idxmin()]
            dist_now = float(nearest["dist"])

            # 5-frame trend
            prev_fid  = fid - TREND_GAP
            dist_prev = all_dists.get((nid, prev_fid))  # None if outside window
            if dist_prev is None:
                trend       = None
                trend_label = "N/A"
            else:
                trend = round(dist_now - dist_prev, 2)
                if trend > 0:
                    trend_label = f"+{trend:.2f} yd (increasing)"
                elif trend < 0:
                    trend_label = f"{trend:.2f} yd (decreasing)"
                else:
                    trend_label = "0.00 yd (unchanged)"

            separations.append({
                "nflId":      nid,
                "name":       _name(nid),
                "lineup":     str(route_rows[route_rows["nflId"]==nid]["pff_positionLinedUp"].iloc[0]),
                "color":      color_map[nid],
                "dist":       round(dist_now, 2),
                "def_x":      float(nearest["x"]),
                "def_y":      float(nearest["y"]),
                "def_name":   _name(int(nearest["nflId"])),
                "rcvr_x":     rx,
                "rcvr_y":     ry,
                "skipped":    False,
                "trend":      trend,
                "trend_label": trend_label,
                "is_target":  (nid == target_nfl_id),
            })

        frames[fid] = {"players": players_out, "separations": separations}

    return {
        "play_id":         play_id,
        "desc":            desc,
        "offense":         offense,
        "defense":         defense,
        "pass_result":     pass_res,
        "snap_frame":      snap_frame,
        "throw_frame":     throw_frame,
        "route_ids":       route_ids,
        "color_map":       {str(k): v for k, v in color_map.items()},
        "target_nfl_id":   target_nfl_id,
        "target_name":     target_name,
        "target_verified": target_verified,
    }

print("Pre-computing play data ...")
PLAY_DATA = {pid: _build_play_data(pid) for pid in PLAY_IDS}
print("Ready.")

# ── Flask routes ──────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(HTML_PAGE, play_ids=PLAY_IDS)

@app.route("/api/play/<int:play_id>")
def api_play(play_id):
    if play_id not in PLAY_DATA:
        return jsonify({"error": f"play_id {play_id} not available"}), 404
    d = PLAY_DATA[play_id]
    # Recompute frames on demand from stored data
    # (frames were built during startup; we just re-expose them here)
    play_row = _plays[(_plays["gameId"]==GAME_ID) & (_plays["playId"]==play_id)].iloc[0]
    defense  = str(play_row["defensiveTeam"])
    offense  = str(play_row["possessionTeam"])
    desc     = str(play_row["playDescription"]).strip()
    pass_res = str(play_row["passResult"])
    snap_frame  = d["snap_frame"]
    throw_frame = d["throw_frame"]
    route_ids   = d["route_ids"]
    color_map   = d["color_map"]

    # Re-derive frames (same logic as _build_play_data, already computed)
    # We stored everything in PLAY_DATA during startup; rebuild frames here
    # to keep the startup object clean and JSON-serialisable.
    track = _tracking[(_tracking["gameId"]==GAME_ID) &
                      (_tracking["playId"]==play_id)].copy()
    role_map = {int(r["nflId"]): str(r["pff_role"])
                for _, r in _pff[(_pff["gameId"]==GAME_ID) &
                                  (_pff["playId"]==play_id)].iterrows()}
    route_rows = (_pff[(_pff["gameId"]==GAME_ID) & (_pff["playId"]==play_id) &
                       (_pff["pff_role"]=="Pass Route")]
                  [["nflId","pff_positionLinedUp"]])
    def_rows = track[track["team"]==defense][["frameId","nflId","x","y"]]
    target_nfl_id = d["target_nfl_id"]
    int_color_map = {int(k): v for k, v in color_map.items()}

    # Pre-compute all distances for trend
    all_dists = {}
    for fid in range(snap_frame, throw_frame + 1):
        def_at = def_rows[def_rows["frameId"]==fid].dropna(subset=["x","y"])
        for nid in route_ids:
            rcvr = track[(track["nflId"]==nid) & (track["frameId"]==fid)]
            if rcvr.empty or def_at.empty:
                all_dists[(nid, fid)] = None
                continue
            rx = float(rcvr.iloc[0]["x"])
            ry = float(rcvr.iloc[0]["y"])
            tmp = def_at.copy()
            tmp["dist"] = ((tmp["x"]-rx)**2 + (tmp["y"]-ry)**2).apply(math.sqrt)
            all_dists[(nid, fid)] = float(tmp["dist"].min())

    frames = {}
    for fid in range(snap_frame, throw_frame + 1):
        fdata        = track[track["frameId"]==fid]
        def_at_frame = def_rows[def_rows["frameId"]==fid].dropna(subset=["x","y"])

        players_out = []
        for _, row in fdata.iterrows():
            nid_raw = row["nflId"]
            team    = str(row["team"])
            is_ball = (team == "football")
            nid_int = int(nid_raw) if not (isinstance(nid_raw, float) and math.isnan(nid_raw)) else None
            players_out.append({
                "nflId":     nid_int,
                "team":      team,
                "x":         float(row["x"]),
                "y":         float(row["y"]),
                "is_ball":   is_ball,
                "role":      role_map.get(nid_int, "Ball" if is_ball else "Other"),
                "name":      "Ball" if is_ball else _name(nid_int),
                "is_route":  (nid_int in route_ids),
                "color":     (int_color_map.get(nid_int) if nid_int in route_ids else None),
                "is_target": (nid_int == target_nfl_id),
            })

        separations = []
        for nid in route_ids:
            rcvr = fdata[fdata["nflId"]==nid]
            if rcvr.empty or def_at_frame.empty:
                separations.append({
                    "nflId": nid, "name": _name(nid),
                    "lineup": str(route_rows[route_rows["nflId"]==nid]["pff_positionLinedUp"].iloc[0]),
                    "color": int_color_map.get(nid, "#888"),
                    "dist": None, "def_x": None, "def_y": None,
                    "def_name": None, "rcvr_x": None, "rcvr_y": None,
                    "skipped": True,
                    "trend": None, "trend_label": "N/A",
                    "is_target": (nid == target_nfl_id),
                })
                continue
            rx = float(rcvr.iloc[0]["x"])
            ry = float(rcvr.iloc[0]["y"])
            tmp = def_at_frame.copy()
            tmp["dist"] = ((tmp["x"]-rx)**2 + (tmp["y"]-ry)**2).apply(math.sqrt)
            nearest = tmp.loc[tmp["dist"].idxmin()]
            dist_now  = float(nearest["dist"])
            prev_fid  = fid - TREND_GAP
            dist_prev = all_dists.get((nid, prev_fid))
            if dist_prev is None:
                trend, trend_label = None, "N/A"
            else:
                trend = round(dist_now - dist_prev, 2)
                if trend > 0:
                    trend_label = f"+{trend:.2f} yd (increasing)"
                elif trend < 0:
                    trend_label = f"{trend:.2f} yd (decreasing)"
                else:
                    trend_label = "0.00 yd (unchanged)"
            separations.append({
                "nflId":      nid,
                "name":       _name(nid),
                "lineup":     str(route_rows[route_rows["nflId"]==nid]["pff_positionLinedUp"].iloc[0]),
                "color":      int_color_map.get(nid, "#888"),
                "dist":       round(dist_now, 2),
                "def_x":      float(nearest["x"]),
                "def_y":      float(nearest["y"]),
                "def_name":   _name(int(nearest["nflId"])),
                "rcvr_x":     rx,
                "rcvr_y":     ry,
                "skipped":    False,
                "trend":      trend,
                "trend_label": trend_label,
                "is_target":  (nid == target_nfl_id),
            })
        frames[str(fid)] = {"players": players_out, "separations": separations}

    return jsonify({
        "play_id":         play_id,
        "desc":            desc,
        "offense":         offense,
        "defense":         defense,
        "pass_result":     pass_res,
        "snap_frame":      snap_frame,
        "throw_frame":     throw_frame,
        "route_ids":       route_ids,
        "color_map":       color_map,
        "target_nfl_id":   target_nfl_id,
        "target_name":     d["target_name"],
        "target_verified": d["target_verified"],
        "frames":          frames,
    })

# ── HTML page ─────────────────────────────────────────────────────────────────
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Route Comparison Viewer</title>
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { background:#111; color:#eee; font-family:system-ui,sans-serif; font-size:14px; }
h1 { padding:12px 20px 4px; font-size:16px; color:#fff; }

/* ── top controls bar ── */
#controls {
  display:flex; align-items:center; gap:12px;
  padding:7px 20px; background:#1a1a1a; flex-wrap:wrap;
  border-bottom:1px solid #2a2a2a;
}
#controls label { color:#ccc; font-size:13px; }
select,button { background:#2a2a2a; color:#eee; border:1px solid #444;
                border-radius:4px; padding:5px 10px; cursor:pointer; font-size:13px; }
select:focus,button:focus { outline:2px solid #FFD700; }
#slider-wrap { display:flex; align-items:center; gap:8px; flex:1; min-width:240px; }
#slider { width:100%; accent-color:#FFD700; }
#frame-label { color:#FFD700; font-weight:bold; min-width:76px; font-size:13px; }
#speed-note { color:#777; font-size:11px; font-style:italic;
              border-left:2px solid #333; padding-left:10px; line-height:1.5; }
#mode-btn { background:#1e3a1e; border-color:#2d6b2d; color:#8fcc8f; }
#mode-btn.coach { background:#1e2a3a; border-color:#2d4a6b; color:#8faacc; }

/* ── mode banner ── */
#mode-banner {
  display:none; padding:8px 20px; background:#12203a;
  border-bottom:1px solid #1e3a6b; font-size:13px; color:#8faacc;
  line-height:1.6;
}
#mode-banner.visible { display:block; }
#coach-question {
  font-size:13.5px; color:#c8ddf8; font-weight:bold; margin-bottom:4px;
}

/* ── main layout ── */
#main { display:flex; gap:0; padding:0 20px 16px; margin-top:8px; }
#field-wrap { flex:1 1 auto; min-width:0; }
#sidebar { width:320px; flex-shrink:0; padding-left:16px; }
svg#field { width:100%; height:auto; display:block;
            border:1px solid #333; border-radius:4px; }

/* ── desc box ── */
#desc-box { background:#1a1a1a; border-radius:4px; padding:9px 12px;
            margin-bottom:10px; line-height:1.5; }
#desc-box .lbl { color:#666; font-size:10px; text-transform:uppercase; letter-spacing:.05em; }
#desc-box .desc { color:#ddd; margin-top:3px; font-size:13px; }
#desc-box .meta { color:#777; font-size:11.5px; margin-top:3px; }

/* ── table ── */
#sep-table { width:100%; border-collapse:collapse; font-size:12px; }
#sep-table th { text-align:left; color:#666; font-weight:normal;
                padding:3px 5px; border-bottom:1px solid #2a2a2a;
                font-size:10.5px; text-transform:uppercase; }
#sep-table td { padding:4px 5px; border-bottom:1px solid #1e1e1e; vertical-align:middle; }
#sep-table tr.highlighted td { background:#1e2c1e; }
#sep-table tr.clickable { cursor:pointer; }
#sep-table tr.clickable:hover td { background:#252525; }
.swatch { display:inline-block; width:9px; height:9px;
          border-radius:50%; margin-right:5px; flex-shrink:0; }
.dist-cell { font-weight:bold; font-variant-numeric:tabular-nums; }
.trend-cell { font-size:11px; color:#aaa; }
.trend-inc { color:#7fcf7f; }
.trend-dec { color:#cf7f7f; }
.trend-na  { color:#555; }

/* ── coach review panel ── */
#coach-panel {
  display:none; margin-top:10px; background:#12203a;
  border:1px solid #1e3a6b; border-radius:4px; padding:10px 12px;
}
#coach-panel.visible { display:block; }
#coach-panel .cp-lbl { color:#7f9fc0; font-size:11px; text-transform:uppercase;
                       letter-spacing:.05em; margin-bottom:6px; }
#receiver-btns { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }
.rcvr-btn { font-size:12px; padding:4px 9px; border-radius:3px;
            border:1px solid #333; background:#1a1a1a; color:#ccc; cursor:pointer; }
.rcvr-btn:hover { background:#252525; }
.rcvr-btn.selected { border-width:2px; font-weight:bold; }
#reveal-btn { background:#1e3a1e; border-color:#2d5a2d; color:#8fcc8f;
              padding:5px 12px; font-size:12.5px; margin-right:6px; }
#reset-coach-btn { background:#2a1e1e; border-color:#5a2d2d; color:#cc8f8f;
                   padding:5px 12px; font-size:12.5px; }
#reveal-area { margin-top:10px; font-size:12.5px; line-height:1.7; display:none; }
#reveal-area.visible { display:block; }
#reveal-target { color:#FFD700; font-weight:bold; }
#reveal-result { color:#ccc; }

/* ── misc ── */
#release-note { background:#2a2200; border:1px solid #554400;
                border-radius:4px; padding:5px 9px; font-size:12px;
                color:#FFD700; margin-top:8px; display:none; }
#caveat { color:#555; font-size:11px; margin-top:10px;
          line-height:1.6; font-style:italic; }
#legend { margin-top:10px; font-size:11px; color:#666; line-height:1.8; }
#legend span { display:inline-block; margin-right:10px; }
</style>
</head>
<body>
<h1>Route Runner Nearest-Defender Distance — Game 2021090900 (2021 NFL Season)</h1>

<div id="controls">
  <label>Play:
    <select id="play-select">
      {% for pid in play_ids %}
      <option value="{{ pid }}">Play {{ pid }}</option>
      {% endfor %}
    </select>
  </label>
  <div id="slider-wrap">
    <label>Frame:</label>
    <input type="range" id="slider" min="1" max="40" value="1" step="1">
    <span id="frame-label">Frame —</span>
  </div>
  <button id="play-btn">▶ Play</button>
  <button id="mode-btn">🎓 Coach Review</button>
  <span id="speed-note">Playback speed is for visualization only;<br>real-time timing is not verified.</span>
</div>

<div id="mode-banner">
  <div id="coach-question">Who has the most nearby space, and whose space is shrinking?</div>
  <div style="color:#7f9fc0;font-size:11.5px;">
    Coach Review Mode — play description and outcome are hidden. Receiver names are shown.
    Animation stops at release. Select a receiver to highlight, then reveal.
  </div>
</div>

<div id="main">
  <div id="field-wrap">
    <svg id="field" viewBox="0 0 120 53.3" preserveAspectRatio="xMidYMid meet">
      <rect x="0" y="0" width="120" height="53.3" fill="#3d6e4e"/>
      <rect x="0"   y="0" width="10" height="53.3" fill="#2c5038"/>
      <rect x="110" y="0" width="10" height="53.3" fill="#2c5038"/>
      <g stroke="white" stroke-width="0.25" opacity="0.5">
        <line x1="10"  y1="0" x2="10"  y2="53.3"/>
        <line x1="20"  y1="0" x2="20"  y2="53.3"/>
        <line x1="30"  y1="0" x2="30"  y2="53.3"/>
        <line x1="40"  y1="0" x2="40"  y2="53.3"/>
        <line x1="50"  y1="0" x2="50"  y2="53.3"/>
        <line x1="60"  y1="0" x2="60"  y2="53.3"/>
        <line x1="70"  y1="0" x2="70"  y2="53.3"/>
        <line x1="80"  y1="0" x2="80"  y2="53.3"/>
        <line x1="90"  y1="0" x2="90"  y2="53.3"/>
        <line x1="100" y1="0" x2="100" y2="53.3"/>
      </g>
      <g fill="white" opacity="0.4" font-size="3.2" text-anchor="middle" font-family="sans-serif">
        <text x="10" y="6.5">10</text><text x="10" y="51">10</text>
        <text x="20" y="6.5">20</text><text x="20" y="51">20</text>
        <text x="30" y="6.5">30</text><text x="30" y="51">30</text>
        <text x="40" y="6.5">40</text><text x="40" y="51">40</text>
        <text x="50" y="6.5">50</text><text x="50" y="51">50</text>
        <text x="60" y="6.5">40</text><text x="60" y="51">40</text>
        <text x="70" y="6.5">30</text><text x="70" y="51">30</text>
        <text x="80" y="6.5">20</text><text x="80" y="51">20</text>
        <text x="90" y="6.5">10</text><text x="90" y="51">10</text>
      </g>
      <g id="layer-lines"></g>
      <g id="layer-players"></g>
      <g id="layer-labels"></g>
    </svg>
  </div>

  <div id="sidebar">
    <div id="desc-box">
      <div class="lbl">Play</div>
      <div class="desc" id="desc-text">—</div>
      <div class="meta" id="meta-text">—</div>
    </div>

    <table id="sep-table">
      <thead>
        <tr>
          <th>Receiver</th>
          <th>Pos</th>
          <th>Nearest def.</th>
          <th>Dist (yd)</th>
          <th>vs 5 frames ago</th>
        </tr>
      </thead>
      <tbody id="sep-body"></tbody>
    </table>

    <div id="release-note">★ Release frame (pass_forward)</div>

    <div id="coach-panel">
      <div class="cp-lbl">Select a receiver to highlight</div>
      <div id="receiver-btns"></div>
      <button id="reveal-btn">Reveal actual target &amp; outcome</button>
      <button id="reset-coach-btn">Reset</button>
      <div id="reveal-area">
        <div id="reveal-target"></div>
        <div id="reveal-result"></div>
        <div style="color:#555;font-size:11px;margin-top:4px;">
          Target identified by matching play description to route runners.<br>
          If ambiguous, "Target not verified" is shown.
        </div>
      </div>
    </div>

    <div id="legend">
      <span>● Route runner (coloured)</span>
      <span style="color:#4466AA">● Defender</span>
      <span style="color:#885522">● Blocker/other off.</span>
      <span style="color:#FFD700">⬤ Ball</span>
    </div>

    <div id="caveat">
      Nearest-defender distance: geometric only. Does not measure passing
      lanes, route depth, or QB pressure. A larger value is not a better
      passing option. Nearest defender may change frame-to-frame and is
      not necessarily the assigned coverage defender. Trend = change over
      5 frame IDs; defender identity may differ between frames.
      Frame rate undocumented — frame numbers used, not seconds.
      Dataset: 2021 NFL season (gameId 2021090900).
    </div>
  </div>
</div>

<script>
// ── State ────────────────────────────────────────────────────────────────────
let playData      = null;
let currentFrame  = 1;
let playing       = false;
let animTimer     = null;
let coachMode     = false;
let revealed      = false;
let selectedNflId = null;

// ── DOM refs ─────────────────────────────────────────────────────────────────
const slider        = document.getElementById("slider");
const frameLabel    = document.getElementById("frame-label");
const playSelect    = document.getElementById("play-select");
const playBtn       = document.getElementById("play-btn");
const modeBtn       = document.getElementById("mode-btn");
const modeBanner    = document.getElementById("mode-banner");
const descText      = document.getElementById("desc-text");
const metaText      = document.getElementById("meta-text");
const sepBody       = document.getElementById("sep-body");
const releaseNote   = document.getElementById("release-note");
const coachPanel    = document.getElementById("coach-panel");
const receiverBtns  = document.getElementById("receiver-btns");
const revealBtn     = document.getElementById("reveal-btn");
const resetCoachBtn = document.getElementById("reset-coach-btn");
const revealArea    = document.getElementById("reveal-area");
const revealTarget  = document.getElementById("reveal-target");
const revealResult  = document.getElementById("reveal-result");

const layerLines   = document.getElementById("layer-lines");
const layerPlayers = document.getElementById("layer-players");
const layerLabels  = document.getElementById("layer-labels");

const SVG_NS = "http://www.w3.org/2000/svg";

// ── Load play ────────────────────────────────────────────────────────────────
function loadPlay(playId) {
  stopAnim();
  resetCoachState();
  fetch("/api/play/" + playId)
    .then(r => r.json())
    .then(data => {
      playData     = data;
      slider.min   = data.snap_frame;
      slider.max   = data.throw_frame;
      slider.value = data.snap_frame;
      currentFrame = data.snap_frame;
      updateDescBox();
      buildReceiverButtons();
      renderFrame(currentFrame);
    });
}

function updateDescBox() {
  if (coachMode && !revealed) {
    descText.textContent = "Play " + playData.play_id + " — " +
                           playData.offense + " vs " + playData.defense;
    metaText.textContent = "Description hidden. Reveal to see outcome.";
  } else {
    descText.textContent = playData.desc;
    metaText.textContent =
      playData.offense + " (off) vs " + playData.defense + " (def)" +
      "  |  passResult=" + playData.pass_result +
      "  |  pass_forward=frame " + playData.throw_frame;
  }
}

// ── Coach Review state ────────────────────────────────────────────────────────
function resetCoachState() {
  revealed      = false;
  selectedNflId = null;
  revealArea.classList.remove("visible");
  revealTarget.textContent = "";
  revealResult.textContent = "";
}

function buildReceiverButtons() {
  receiverBtns.innerHTML = "";
  if (!playData) return;
  const fid  = playData.snap_frame;
  const fd   = playData.frames[String(fid)];
  if (!fd) return;
  for (const sep of fd.separations) {
    const btn = document.createElement("button");
    btn.className   = "rcvr-btn";
    btn.dataset.nflid = sep.nflId;
    btn.textContent = sep.name.split(" ").pop();  // last name
    btn.style.borderColor = sep.color;
    btn.style.color       = sep.color;
    btn.addEventListener("click", () => {
      const nid = parseInt(btn.dataset.nflid);
      selectedNflId = (selectedNflId === nid) ? null : nid;
      document.querySelectorAll(".rcvr-btn").forEach(b => b.classList.remove("selected"));
      if (selectedNflId !== null) btn.classList.add("selected");
      renderFrame(currentFrame);
    });
    receiverBtns.appendChild(btn);
  }
}

// ── Mode toggle ───────────────────────────────────────────────────────────────
modeBtn.addEventListener("click", () => {
  stopAnim();
  coachMode = !coachMode;
  resetCoachState();
  if (coachMode) {
    modeBtn.textContent = "📊 Standard Mode";
    modeBtn.classList.add("coach");
    modeBanner.classList.add("visible");
    coachPanel.classList.add("visible");
  } else {
    modeBtn.textContent = "🎓 Coach Review";
    modeBtn.classList.remove("coach");
    modeBanner.classList.remove("visible");
    coachPanel.classList.remove("visible");
  }
  if (playData) {
    updateDescBox();
    renderFrame(currentFrame);
  }
});

// ── Reveal ────────────────────────────────────────────────────────────────────
revealBtn.addEventListener("click", () => {
  if (!playData) return;
  revealed = true;
  updateDescBox();

  if (playData.target_verified) {
    revealTarget.textContent =
      "Intended target: " + playData.target_name + " (matched from play description)";
  } else {
    revealTarget.textContent = "Intended target: not verified (ambiguous or no match in description)";
  }

  const resultMap = { C:"Complete", I:"Incomplete", S:"Sack", IN:"Interception", R:"Scramble" };
  revealResult.textContent =
    "Outcome (plays.csv): " + (resultMap[playData.pass_result] || playData.pass_result);

  revealArea.classList.add("visible");
  renderFrame(currentFrame);
});

// ── Reset Coach ───────────────────────────────────────────────────────────────
resetCoachBtn.addEventListener("click", () => {
  stopAnim();
  resetCoachState();
  if (playData) {
    slider.value = playData.snap_frame;
    currentFrame = playData.snap_frame;
    updateDescBox();
    document.querySelectorAll(".rcvr-btn").forEach(b => b.classList.remove("selected"));
    renderFrame(currentFrame);
  }
});

// ── Render frame ──────────────────────────────────────────────────────────────
function renderFrame(fid) {
  frameLabel.textContent = "Frame " + fid;
  slider.value = fid;

  const fd = playData.frames[String(fid)];
  if (!fd) return;

  layerLines.innerHTML   = "";
  layerPlayers.innerHTML = "";
  layerLabels.innerHTML  = "";

  const isSelected = (nid) => selectedNflId !== null && nid === selectedNflId;
  const dimOthers  = selectedNflId !== null;

  // ── Distance lines ──
  for (const sep of fd.separations) {
    if (sep.skipped || sep.dist === null) continue;
    const dim = dimOthers && !isSelected(sep.nflId);

    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", sep.rcvr_x); line.setAttribute("y1", sep.rcvr_y);
    line.setAttribute("x2", sep.def_x);  line.setAttribute("y2", sep.def_y);
    line.setAttribute("stroke", sep.color);
    line.setAttribute("stroke-width", isSelected(sep.nflId) ? "0.55" : "0.3");
    line.setAttribute("stroke-dasharray", "1.2 0.8");
    line.setAttribute("opacity", dim ? "0.2" : "0.8");
    layerLines.appendChild(line);

    if (!dim) {
      // Place the distance label offset perpendicular to the receiver–defender
      // line so it does not land on top of either dot or the name label.
      // Perpendicular offset: rotate the line direction 90°, shift 2.2 units.
      const dx = sep.def_x - sep.rcvr_x;
      const dy = sep.def_y - sep.rcvr_y;
      const len = Math.sqrt(dx*dx + dy*dy) || 1;
      // Unit perpendicular (rotate 90° CCW: [-dy, dx])
      const px = -dy / len;
      const py =  dx / len;
      // Midpoint + perpendicular offset
      const mx = (sep.rcvr_x + sep.def_x) / 2 + px * 2.2;
      const my = (sep.rcvr_y + sep.def_y) / 2 + py * 2.2;
      const bg = document.createElementNS(SVG_NS, "rect");
      bg.setAttribute("x", mx - 2.4); bg.setAttribute("y", my - 1.8);
      bg.setAttribute("width", "4.8"); bg.setAttribute("height", "2.4");
      bg.setAttribute("rx", "0.4");
      bg.setAttribute("fill", "#111"); bg.setAttribute("opacity", "0.75");
      layerLabels.appendChild(bg);
      const lt = document.createElementNS(SVG_NS, "text");
      lt.setAttribute("x", mx); lt.setAttribute("y", my + 0.4);
      lt.setAttribute("text-anchor", "middle");
      lt.setAttribute("font-size", "1.75");
      lt.setAttribute("font-family", "sans-serif");
      lt.setAttribute("fill", sep.color);
      lt.textContent = sep.dist.toFixed(2) + " yd";
      layerLabels.appendChild(lt);
    }
  }

  // ── Players ──
  for (const p of fd.players) {
    const x = p.x, y = p.y;

    if (p.is_ball) {
      // In coach mode before reveal, hide ball position to avoid hinting target area
      // Actually: ball is kept visible (it shows where the QB is, not the target)
      const c = document.createElementNS(SVG_NS, "ellipse");
      c.setAttribute("cx", x); c.setAttribute("cy", y);
      c.setAttribute("rx", "0.9"); c.setAttribute("ry", "0.6");
      c.setAttribute("fill", "#FFD700");
      c.setAttribute("stroke", "#333"); c.setAttribute("stroke-width", "0.2");
      layerPlayers.appendChild(c);
      continue;
    }

    let fill, radius, strokeCol, strokeW, opacity;
    if (p.is_route) {
      fill      = p.color;
      radius    = isSelected(p.nflId) ? 1.6 : 1.2;
      strokeCol = isSelected(p.nflId) ? "white" : "#ccc";
      strokeW   = isSelected(p.nflId) ? "0.4"   : "0.2";
      opacity   = (dimOthers && !isSelected(p.nflId)) ? "0.3" : "1";
    } else {
      const isDef = (p.team === playData.defense);
      fill      = isDef ? "#4466AA" : "#885522";
      radius    = 0.8;
      strokeCol = "#555";
      strokeW   = "0.15";
      opacity   = "0.6";
    }

    const c = document.createElementNS(SVG_NS, "circle");
    c.setAttribute("cx", x); c.setAttribute("cy", y);
    c.setAttribute("r", radius);
    c.setAttribute("fill", fill);
    c.setAttribute("stroke", strokeCol);
    c.setAttribute("stroke-width", strokeW);
    c.setAttribute("opacity", opacity);
    layerPlayers.appendChild(c);

    // Tooltip: in coach mode before reveal, suppress target/outcome hints
    const titleEl = document.createElementNS(SVG_NS, "title");
    if (coachMode && !revealed && p.is_route) {
      titleEl.textContent = p.name + " (" + p.role + ")";
    } else {
      titleEl.textContent = p.name + " (" + p.role + ", " + p.team + ")";
    }
    c.appendChild(titleEl);

    // Name labels for route runners — placed above the dot to stay clear
    // of the distance labels (which sit beside the receiver–defender line).
    if (p.is_route) {
      const parts = p.name.split(" ");
      const lastName = parts[parts.length - 1];
      const labelX = x;
      const labelY = y - 2.5;   // above the dot, not overlapping it
      // Dark background pill for readability against the green field
      const nameBg = document.createElementNS(SVG_NS, "rect");
      const approxW = lastName.length * 1.1 + 0.8;
      nameBg.setAttribute("x", labelX - approxW / 2);
      nameBg.setAttribute("y", labelY - 1.6);
      nameBg.setAttribute("width",  approxW);
      nameBg.setAttribute("height", "1.9");
      nameBg.setAttribute("rx", "0.4");
      nameBg.setAttribute("fill", "#111");
      nameBg.setAttribute("opacity", (dimOthers && !isSelected(p.nflId)) ? "0.15" : "0.65");
      layerLabels.appendChild(nameBg);
      const lbl = document.createElementNS(SVG_NS, "text");
      lbl.setAttribute("x", labelX);
      lbl.setAttribute("y", labelY);
      lbl.setAttribute("text-anchor", "middle");
      lbl.setAttribute("font-size", "1.85");
      lbl.setAttribute("font-family", "sans-serif");
      lbl.setAttribute("fill", p.color);
      lbl.setAttribute("font-weight", isSelected(p.nflId) ? "bold" : "normal");
      lbl.setAttribute("opacity", (dimOthers && !isSelected(p.nflId)) ? "0.3" : "1");
      lbl.textContent = lastName;
      layerLabels.appendChild(lbl);
    }
  }

  // ── Separation table ──
  sepBody.innerHTML = "";
  for (const sep of fd.separations) {
    const tr = document.createElement("tr");
    tr.classList.add("clickable");
    if (isSelected(sep.nflId)) tr.classList.add("highlighted");

    // Click row to select receiver
    tr.addEventListener("click", () => {
      selectedNflId = (selectedNflId === sep.nflId) ? null : sep.nflId;
      document.querySelectorAll(".rcvr-btn").forEach(b => {
        b.classList.toggle("selected", parseInt(b.dataset.nflid) === selectedNflId);
      });
      renderFrame(currentFrame);
    });

    // Receiver name cell
    const nameTd = document.createElement("td");
    nameTd.innerHTML = `<span class="swatch" style="background:${sep.color}"></span>${sep.name}`;

    // Lineup
    const lineupTd = document.createElement("td");
    lineupTd.textContent = sep.lineup;

    // Nearest defender — hidden in coach mode before reveal
    const defTd = document.createElement("td");
    if (coachMode && !revealed) {
      defTd.textContent = "—";
      defTd.style.color = "#444";
    } else {
      defTd.textContent = sep.skipped ? "—" : (sep.def_name || "—");
    }

    // Distance
    const distTd = document.createElement("td");
    distTd.className = "dist-cell";
    distTd.style.color = sep.color;
    distTd.textContent = sep.skipped ? "skip" : sep.dist.toFixed(2);

    // Trend
    const trendTd = document.createElement("td");
    trendTd.className = "trend-cell";
    if (!sep.trend_label || sep.trend_label === "N/A") {
      trendTd.classList.add("trend-na");
      trendTd.textContent = "N/A";
    } else if (sep.trend && sep.trend > 0) {
      trendTd.classList.add("trend-inc");
      trendTd.innerHTML = "&#8593; " + sep.trend_label;
    } else if (sep.trend && sep.trend < 0) {
      trendTd.classList.add("trend-dec");
      trendTd.innerHTML = "&#8595; " + sep.trend_label;
    } else {
      trendTd.textContent = sep.trend_label;
    }

    tr.appendChild(nameTd);
    tr.appendChild(lineupTd);
    tr.appendChild(defTd);
    tr.appendChild(distTd);
    tr.appendChild(trendTd);
    sepBody.appendChild(tr);
  }

  // Release frame note
  releaseNote.style.display = (fid === playData.throw_frame) ? "block" : "none";
}

// ── Animation ────────────────────────────────────────────────────────────────
function stopAnim() {
  playing = false;
  playBtn.textContent = "▶ Play";
  clearInterval(animTimer);
  animTimer = null;
}

playBtn.addEventListener("click", () => {
  if (playing) { stopAnim(); return; }
  playing = true;
  playBtn.textContent = "⏸ Pause";
  if (currentFrame >= playData.throw_frame) {
    currentFrame = playData.snap_frame;
    renderFrame(currentFrame);
  }
  animTimer = setInterval(() => {
    currentFrame++;
    renderFrame(currentFrame);
    // In coach mode, auto-pause at release frame
    if (currentFrame >= playData.throw_frame) stopAnim();
  }, 120);
});

slider.addEventListener("input", () => {
  stopAnim();
  currentFrame = parseInt(slider.value);
  renderFrame(currentFrame);
});

playSelect.addEventListener("change", () => {
  // Stops animation, resets coach state, resets slider to new play's snap frame
  stopAnim();
  resetCoachState();
  if (coachMode) {
    // Stay in coach mode but clear reveal for new play
    document.querySelectorAll(".rcvr-btn").forEach(b => b.classList.remove("selected"));
    selectedNflId = null;
  }
  loadPlay(parseInt(playSelect.value));
});

// ── Initial load ─────────────────────────────────────────────────────────────
loadPlay(parseInt(playSelect.value));
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("\nStarting viewer at  http://127.0.0.1:5050")
    print("Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=5050, debug=False)
