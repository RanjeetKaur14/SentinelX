"""
risk_engine.py (FIXED)
-----------------------
The original risk_engine.py in the risk_engine module does NOT match
its own models.py. calculate_risk(data: Analytics) reads:

    data.density            <- doesn't exist (density lives at
                               data.crowd_metrics.normalized_density,
                               a Dict[str, float], not a scalar)
    data.opposite_flow      <- doesn't exist at all
    data.exit_blocked       <- doesn't exist at all
    data.stationary_people  <- doesn't exist (it's
                               data.crowd_metrics.stationary_tracks,
                               a List[int] of track IDs, not a count)
    data.average_speed      <- doesn't exist (it's
                               data.crowd_metrics.average_speed)
    data.people_count       <- doesn't exist (it's
                               data.crowd_metrics.people_count)

sample_data.json is also written in this old flat shape, which is why
GET /risk/sample would also crash -- Analytics(**raw_data) itself fails
pydantic validation, since sample_data.json has no `frame`/`tracks`/
`crowd_metrics` keys at all.

This means risk_engine.py was written against an EARLIER, flatter
version of the analytics contract (the "v1" shape analytics_engine.py's
docstring mentions), before crowd_analysis moved to the nested v2
`crowd_metrics` block. It was never updated after that breaking change.

Below is a drop-in replacement that reads from the real nested
Analytics/CrowdMetrics shape crowd_analysis actually emits, keeping the
same scoring weights/behavior as the original wherever a like-for-like
field exists, and adding clearly-labeled heuristics where the old rule
depended on a signal (opposite_flow, exit_blocked) that crowd_analysis
deliberately does NOT compute (by design -- see CrowdMetrics docstring:
that interpretation is meant to live here, in the Risk Engine).

TUNE THE THRESHOLDS marked below against your own camera's footage --
they're reasonable starting points, not measured constants.
"""

from models import Analytics


def calculate_risk(data: Analytics):
    score = 0
    reasons = []

    cm = data.crowd_metrics

    # ---- Rule 1: Crowd density -----------------------------------
    # FIXED (v2): the original approach here compared the busiest zone
    # to the *average* zone across the whole grid. That blows up on any
    # camera where part of the frame is naturally empty (wall, sky,
    # doorway background) -- which is nearly all real footage -- because
    # a grid full of legitimate zero-zones drags the average near zero
    # and inflates the ratio to 4-5x on completely ordinary frames. That
    # was confirmed against real logged frames: it fired on 869/869
    # frames regardless of actual crowd behavior, i.e. it measured
    # nothing.
    #
    # Fixed metric: what FRACTION of all currently-visible people are
    # packed into the single busiest zone. This is scale-invariant
    # (doesn't care how many zones are empty) and only responds to
    # actual clustering of the people who exist, not to camera framing.
    raw_vals = list(cm.density.values())
    people_count = cm.people_count
    concentration = (max(raw_vals) / people_count) if raw_vals and people_count > 0 else 0.0

    if concentration > 0.65:           # TUNE: >65% of the crowd in one zone
        score += 30
        reasons.append("High crowd density")
    elif concentration > 0.5:          # TUNE
        score += 15
        reasons.append("Moderate crowd density")

    # ---- Rule 2: People count -----------------------------------
    # RECALIBRATED for the head detector @ imgsz=960 (was tuned
    # against the old full-body detector's much lower counts).
    # Measured on real calm footage (v1.mp4/v2.mp4, 581 frames,
    # corrected timestamps -- see frame_timestamp() in adapter.py):
    #   people_count  p50=132  p90=144  p97=149  max=159
    # The old thresholds (150/80) sat BELOW the calm-footage p50/p90,
    # so "Large crowd size" was firing on nearly every frame of normal
    # footage. New thresholds sit with real headroom above the p97 of
    # calm footage. TUNE against YOUR deployment camera's own calm
    # baseline before relying on this for a real venue -- raw head
    # count is very sensitive to camera framing/distance, so these
    # numbers are a starting point from two hackathon test clips, not
    # a universal constant.
    if cm.people_count > 260:
        score += 20
        reasons.append("Very high number of people")
    elif cm.people_count > 200:
        score += 10
        reasons.append("Large crowd size")

    # ---- Rule 3: Average speed --------------------------------------
    # cm.average_speed is pixels/second (not the old 0..1-ish scale).
    # A near-zero speed across a crowd this size is what actually
    # signals "stuck", so gate this on there being people around at all.
    if cm.people_count > 0 and cm.average_speed < 5.0:   # TUNE: px/sec
        score += 15
        reasons.append("Crowd movement is very slow")

    # ---- Rule 4: Opposing flow --------------------------------------
    # crowd_analysis exposes a raw direction_histogram (counts per
    # compass bin) instead of a boolean -- deciding what counts as
    # "opposing" is exactly the judgment call left to this engine.
    hist = cm.flow.direction_histogram
    opposite_pairs = [("N", "S"), ("NE", "SW"), ("E", "W"), ("SE", "NW")]
    opposing_threshold = 5   # TUNE: min tracks in each opposing bin
    opposite_flow = any(
        hist.get(a, 0) >= opposing_threshold and hist.get(b, 0) >= opposing_threshold
        for a, b in opposite_pairs
    )
    if opposite_flow:
        score += 20
        reasons.append("Opposing movement detected")

    # ---- Rule 5: Exit blocked -----------------------------------------
    # No direct "blocked" signal exists upstream. Heuristic: people are
    # entering but nobody is exiting, and the crowd isn't moving --
    # i.e. accumulating with nowhere to go. Needs an "exit" line to be
    # configured in crowd_analysis's EntryExitConfig to mean anything;
    # if you haven't set one up, total_exit will just always be 0 and
    # this will fire on any one-way entry flow -- disable this rule
    # (or add a real exit-line check) until that's wired up.
    exit_blocked = (
        cm.entry_exit.total_entry > 10
        and cm.entry_exit.total_exit == 0
        and cm.average_speed < 5.0
    )
    if exit_blocked:
        score += 25
        reasons.append("Exit blocked")

    # ---- Rule 6: Stationary people ------------------------------------
    # stationary_tracks is a list of track IDs -- use its length as the count.
    if len(cm.stationary_tracks) > 20:
        score += 10
        reasons.append("Large number of stationary people")

    # Cap score at 100
    if score > 100:
        score = 100

    # Decide risk level based on score (unchanged)
    if score >= 80:
        level = "Red"
    elif score >= 50:
        level = "Orange"
    elif score >= 25:
        level = "Yellow"
    else:
        level = "Green"

    return score, level, reasons
