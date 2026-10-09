# NFL Route Comparison Viewer — Submission README

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
