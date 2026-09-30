"""
Unit tests for Camelot key math and sequence optimization.
"""

from pathlib import Path
from computers_after_all.curator import SetlistCurator, camelot_distance
from computers_after_all.models import Track


def test_camelot_distance():
    # Exact match
    assert camelot_distance("8A", "8A") == 0.0
    # Relative Major/Minor
    assert camelot_distance("8A", "8B") == 0.5
    # Fifths (neighbors on clock)
    assert camelot_distance("8A", "9A") == 1.0
    assert camelot_distance("8A", "7A") == 1.0
    # Wrap-around 12 to 1
    assert camelot_distance("12A", "1A") == 1.0
    # Energy jump (+2)
    assert camelot_distance("8A", "10A") == 2.5
    # Opposite / Dissonant
    assert camelot_distance("8A", "2A") > 5.0


def test_setlist_curator_optimization():
    curator = SetlistCurator()
    tracks = [
        Track(path=Path("t1.mp3"), title="T1", artist="A1", duration_seconds=300, bpm=126, camelot_key="8A"),
        Track(path=Path("t2.mp3"), title="T2", artist="A2", duration_seconds=300, bpm=128, camelot_key="2A"),  # Far
        Track(path=Path("t3.mp3"), title="T3", artist="A3", duration_seconds=300, bpm=126, camelot_key="8B"),  # Close to 8A
        Track(path=Path("t4.mp3"), title="T4", artist="A4", duration_seconds=300, bpm=127, camelot_key="9A"),  # Close to 8A
    ]

    initial_cost = curator.total_cost(tracks)
    optimized = curator.optimize_sequence(tracks, iterations=500)
    optimized_cost = curator.total_cost(optimized)

    assert optimized_cost <= initial_cost
    assert len(optimized) == len(tracks)
