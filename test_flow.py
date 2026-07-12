"""
test_flow.py
------------
Covers FlowClassifier against the four documented synthetic scenarios
(all-East, half-East/half-West, random/chaotic, all-stationary) plus
direction-histogram correctness and low-track-count edge cases.
"""

import math
import random

import pytest

from analytics.config import FlowConfig
from analytics.flow import FlowClassifier
from analytics.models import Track


def moving_track(track_id, direction):
    t = Track(track_id=track_id, bbox=(0, 0, 10, 10), centroid=(0, 0))
    t.direction = direction
    return t


class TestScenario1AllEast:
    def test_uniform_high_confidence_low_entropy(self):
        classifier = FlowClassifier(FlowConfig(min_moving_tracks=2))
        tracks = [moving_track(i, "East") for i in range(6)]
        result = classifier.classify(tracks)
        assert result.label == "Uniform"
        assert result.confidence == pytest.approx(1.0, abs=1e-6)
        assert result.entropy == pytest.approx(0.0, abs=1e-6)
        assert result.dominant_heading == pytest.approx(0.0, abs=1e-6)
        assert result.direction_histogram["East"] == 6


class TestScenario2OpposingStreams:
    def test_half_east_half_west_produces_low_confidence_high_entropy(self):
        """
        NOTE: per the module's own documented design, perfectly
        opposing streams produce mean resultant length R == 0, which
        the circular-std-dev formula classifies as "Chaotic" (maximal
        spread), not "Mixed" -- this is a known, documented limitation
        of circular statistics (it can't distinguish a clean bimodal
        split from fully random scatter on std-dev alone). Directional
        entropy IS the signal that distinguishes them: a clean 50/50
        split gives entropy = ln(2) ~= 0.693, well below the ~2.08 max
        for a fully random 8-way scatter (see TestScenario3 below).
        This test documents actual behavior, not the naive "Mixed"
        expectation -- see QA report for the full discussion.
        """
        classifier = FlowClassifier(FlowConfig(min_moving_tracks=2))
        tracks = [moving_track(i, "East") for i in range(5)]
        tracks += [moving_track(i + 5, "West") for i in range(5)]
        result = classifier.classify(tracks)
        assert result.confidence == pytest.approx(0.0, abs=1e-6)
        assert result.entropy == pytest.approx(math.log(2), abs=1e-3)
        assert result.direction_histogram["East"] == 5
        assert result.direction_histogram["West"] == 5


class TestScenario3RandomChaotic:
    def test_random_directions_low_confidence_high_entropy(self):
        random.seed(9)
        classifier = FlowClassifier(FlowConfig(min_moving_tracks=2))
        directions = ["East", "North-East", "North", "North-West", "West",
                      "South-West", "South", "South-East"]
        tracks = [moving_track(i, random.choice(directions)) for i in range(40)]
        result = classifier.classify(tracks)
        assert result.confidence < 0.5
        # Entropy should be meaningfully higher than the clean-bimodal
        # case (ln(2) ~= 0.693) since it's spread across up to 8 bins.
        assert result.entropy > math.log(2)


class TestScenario4AllStationary:
    def test_all_stationary_produces_safe_defaults(self):
        classifier = FlowClassifier(FlowConfig(min_moving_tracks=2))
        tracks = [moving_track(i, "Stationary") for i in range(8)]
        result = classifier.classify(tracks)
        assert result.label == "Uniform"
        assert result.confidence == 0.0
        assert result.dominant_heading is None
        assert result.entropy == 0.0
        assert result.direction_histogram["Stationary"] == 8

    def test_empty_track_list_does_not_crash(self):
        classifier = FlowClassifier(FlowConfig(min_moving_tracks=2))
        result = classifier.classify([])
        assert result.label == "Uniform"
        assert result.direction_histogram["Stationary"] == 0


class TestBelowMinimumMovingTracks:
    def test_below_threshold_returns_safe_defaults_not_a_crash(self):
        classifier = FlowClassifier(FlowConfig(min_moving_tracks=5))
        tracks = [moving_track(i, "East") for i in range(2)]  # below threshold
        result = classifier.classify(tracks)
        assert result.label == "Uniform"
        assert result.dominant_heading is None
        # Histogram is still populated even below threshold -- it's a
        # raw measurement, not gated by the classification threshold.
        assert result.direction_histogram["East"] == 2


class TestHistogramCompleteness:
    def test_histogram_always_has_all_nine_keys(self):
        classifier = FlowClassifier(FlowConfig())
        result = classifier.classify([moving_track(0, "North")])
        expected_keys = {
            "East", "North-East", "North", "North-West", "West",
            "South-West", "South", "South-East", "Stationary",
        }
        assert set(result.direction_histogram.keys()) == expected_keys
