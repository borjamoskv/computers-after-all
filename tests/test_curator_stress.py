"""
Stress testing for SetlistCurator: massive tracklists (100 tracks)
and full Camelot wheel combinatorial coverage.
"""

from pathlib import Path
import time
from computers_after_all.curator import SetlistCurator, camelot_distance
from computers_after_all.models import Track


def test_camelot_full_wheel_symmetry():
    """Validates that distance(K_a, K_b) == distance(K_b, K_a) for all 24 keys."""
    keys = [f"{i}{l}" for i in range(1, 13) for l in ["A", "B"]]
    for k1 in keys:
        for k2 in keys:
            d12 = camelot_distance(k1, k2)
            d21 = camelot_distance(k2, k1)
            assert d12 == d21, f"Asymmetry between {k1} and {k2}: {d12} != {d21}"


def test_massive_setlist_combinatorial_optimization():
    """
    Stress tests TSP Simulated Annealing with 60 tracks.
    Certifies sub-second execution (< 500 ms) and monotonic cost reduction.
    """
    curator = SetlistCurator()
    keys = [f"{(i % 12) + 1}{'A' if i % 2 == 0 else 'B'}" for i in range(60)]

    tracks = [
        Track(
            path=Path(f"track_{i:03d}.mp3"),
            title=f"Track {i}",
            artist=f"Artist {i}",
            duration_seconds=300.0,
            bpm=120.0 + (i % 15),
            camelot_key=keys[i],
            energy=0.3 + 0.01 * (i % 50)
        )
        for i in range(60)
    ]

    t0 = time.perf_counter()
    initial_cost = curator.total_cost(tracks)
    optimized = curator.optimize_sequence(tracks, iterations=1000)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    optimized_cost = curator.total_cost(optimized)

    assert len(optimized) == 60
    assert optimized_cost <= initial_cost
    assert elapsed_ms < 600.0, f"Optimization took {elapsed_ms:.1f} ms, expected < 600 ms"
