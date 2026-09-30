"""
Integration test using real underground gems from local ~/Music/ repository.
Fallback to synthetic tracks on remote CI runners.
"""

from pathlib import Path
import pytest
from computers_after_all.analyzer import AudioAnalyzer
from computers_after_all.curator import SetlistCurator
from computers_after_all.engine import AutonomousDJ
from computers_after_all.rekordbox import ClubExporter
from computers_after_all.youtube import YouTubeMetadataGenerator


VAULT_DIR = Path.home() / "Music" / "Alain Elektronische Setlist 20 Gemas"


@pytest.fixture
def real_or_synthetic_tracks(tmp_path):
    """Returns paths to real tracks if available, otherwise synthetic tracks."""
    if VAULT_DIR.exists():
        real_files = sorted(list(VAULT_DIR.glob("*.mp3")))[:3]
        if len(real_files) >= 2:
            return real_files

    # Fallback to generating 3 mini tracks
    from tests.test_cli import create_mini_track
    paths = []
    for i in range(3):
        p = tmp_path / f"synthetic_gem_{i}.wav"
        create_mini_track(p, bpm=126.0 + i, duration_sec=12.0)
        paths.append(p)
    return paths


def test_real_setlist_analysis_and_curation(real_or_synthetic_tracks):
    analyzer = AudioAnalyzer()
    tracks = [analyzer.analyze_track(p) for p in real_or_synthetic_tracks]

    assert len(tracks) >= 2
    for t in tracks:
        assert t.duration_seconds > 0
        assert 60.0 <= t.bpm <= 180.0
        assert len(t.camelot_key) >= 2
        assert len(t.cues) == 4

    curator = SetlistCurator()
    ordered = curator.optimize_sequence(tracks)
    assert len(ordered) == len(tracks)


def test_real_setlist_plan_and_export(tmp_path, real_or_synthetic_tracks):
    dj = AutonomousDJ(default_transition_bars=16)
    plan = dj.prepare_set(real_or_synthetic_tracks, optimize_order=True, transition_bars=16)

    assert len(plan.tracks) == len(real_or_synthetic_tracks)
    assert len(plan.transitions) == len(real_or_synthetic_tracks) - 1
    assert plan.total_duration_seconds > 0

    # Test Rekordbox XML generation
    exporter = ClubExporter()
    xml_path = tmp_path / "REAL_REKORDBOX.xml"
    exporter.export_rekordbox_xml(plan, xml_path, playlist_name="Real Gem Mix")
    assert xml_path.exists()
    assert xml_path.stat().st_size > 500

    # Test YouTube Metadata generation
    yt_gen = YouTubeMetadataGenerator()
    yt_path = tmp_path / "REAL_YOUTUBE.md"
    yt_gen.generate_metadata_file(plan, yt_path, set_title="Real Gem Mix")
    assert yt_path.exists()
    assert "TRACKLIST & CHAPTERS" in yt_path.read_text()
