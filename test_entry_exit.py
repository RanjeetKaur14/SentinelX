"""
test_entry_exit.py
-------------------
Covers EntryExitCounter: single/multiple crossings, hysteresis
(oscillation suppression), simultaneous opposite-direction crossings,
and multiple virtual lines.
"""

import pytest

from analytics.config import EntryExitConfig, EntryExitLine
from analytics.entry_exit import EntryExitCounter
from analytics.models import Track


def track_at(track_id, x, y=500):
    return Track(track_id=track_id, bbox=(x - 10, y - 10, x + 10, y + 10), centroid=(x, y))


class TestSingleCrossing:
    def test_single_left_to_right_crossing_counts_as_entry(self):
        line = EntryExitLine(name="L1", p1=(200, 0), p2=(200, 1000))
        counter = EntryExitCounter(EntryExitConfig(lines=(line,), hysteresis_distance_px=8.0))

        t = track_at(0, 100)
        for x in range(100, 260, 20):
            t.centroid = (x, 500)
            counter.update([t])

        snap = counter.snapshot()
        assert snap["entry_count"] == 1
        assert snap["exit_count"] == 0
        assert snap["per_line"]["L1"]["entry_count"] == 1


class TestMultipleCrossings:
    def test_multiple_people_crossing_same_direction(self):
        line = EntryExitLine(name="L1", p1=(200, 0), p2=(200, 1000))
        counter = EntryExitCounter(EntryExitConfig(lines=(line,), hysteresis_distance_px=8.0))

        tracks = [track_at(i, 100, y=100 + i * 50) for i in range(5)]
        for step in range(20):
            for t in tracks:
                t.centroid = (t.centroid[0] + 20, t.centroid[1])
            counter.update(tracks)

        assert counter.snapshot()["entry_count"] == 5

    def test_simultaneous_opposite_direction_crossings(self):
        line = EntryExitLine(name="L1", p1=(200, 0), p2=(200, 1000))
        counter = EntryExitCounter(EntryExitConfig(lines=(line,), hysteresis_distance_px=8.0))

        a = track_at(0, 100, y=300)  # moving left -> right (entry)
        b = track_at(1, 300, y=500)  # moving right -> left (exit)
        for _ in range(20):
            a.centroid = (a.centroid[0] + 15, a.centroid[1])
            b.centroid = (b.centroid[0] - 15, b.centroid[1])
            counter.update([a, b])

        snap = counter.snapshot()
        assert snap["entry_count"] == 1
        assert snap["exit_count"] == 1


class TestHysteresis:
    def test_oscillation_near_line_does_not_double_count(self):
        """
        Regression test for a hysteresis double-count bug found and
        fixed during an earlier review: a track lingering right at the
        line boundary must not repeatedly trigger entry/exit counts.
        """
        line = EntryExitLine(name="L1", p1=(200, 0), p2=(200, 1000))
        counter = EntryExitCounter(EntryExitConfig(lines=(line,), hysteresis_distance_px=8.0))

        t = track_at(0, 198, y=500)
        offsets = [2, -2, 2, -2, 2, -2, 2, -2] * 5  # stays within the 8px band
        for offset in offsets:
            t.centroid = (198 + offset, 500)
            counter.update([t])

        snap = counter.snapshot()
        assert snap["entry_count"] == 0
        assert snap["exit_count"] == 0

    def test_person_stopping_exactly_on_line_does_not_crash_or_falsely_count(self):
        line = EntryExitLine(name="L1", p1=(200, 0), p2=(200, 1000))
        counter = EntryExitCounter(EntryExitConfig(lines=(line,), hysteresis_distance_px=8.0))

        t = track_at(0, 100, y=500)
        for x in [100, 150, 200, 200, 200, 200]:  # stops exactly on the line
            t.centroid = (x, 500)
            counter.update([t])

        snap = counter.snapshot()
        # Never confidently crossed to the other side, so no crossing
        # should be registered yet.
        assert snap["entry_count"] == 0
        assert snap["exit_count"] == 0

    def test_clears_band_then_crosses_counts_exactly_once(self):
        line = EntryExitLine(name="L1", p1=(200, 0), p2=(200, 1000))
        counter = EntryExitCounter(EntryExitConfig(lines=(line,), hysteresis_distance_px=8.0))

        t = track_at(0, 100, y=500)
        # Jump straight across in a single large step (bigger than the
        # hysteresis band on both sides) -- should count exactly once.
        for x in [100, 100 + 12, 100 + 12 + 200]:
            t.centroid = (x, 500)
            counter.update([t])

        assert counter.snapshot()["entry_count"] == 1


class TestMultipleLines:
    def test_crossing_two_lines_counts_on_each(self):
        lines = (
            EntryExitLine(name="L1", p1=(200, 0), p2=(200, 1000)),
            EntryExitLine(name="L2", p1=(600, 0), p2=(600, 1000)),
        )
        counter = EntryExitCounter(EntryExitConfig(lines=lines, hysteresis_distance_px=8.0))

        t = track_at(0, 100, y=300)
        for _ in range(40):
            t.centroid = (t.centroid[0] + 15, t.centroid[1])
            counter.update([t])

        snap = counter.snapshot()
        assert snap["entry_count"] == 2
        assert snap["per_line"]["L1"]["entry_count"] == 1
        assert snap["per_line"]["L2"]["entry_count"] == 1

    def test_no_lines_configured_never_counts(self):
        counter = EntryExitCounter(EntryExitConfig(lines=()))
        t = track_at(0, 100, y=500)
        for x in range(100, 500, 20):
            t.centroid = (x, 500)
            counter.update([t])
        snap = counter.snapshot()
        assert snap["entry_count"] == 0
        assert snap["exit_count"] == 0
        assert snap["per_line"] == {}
