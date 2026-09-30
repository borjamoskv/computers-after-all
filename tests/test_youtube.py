"""
Unit tests for YouTube metadata formatting and chapter generation.
"""

from pathlib import Path
from computers_after_all.models import MixPlan, MixSegment, Track
from computers_after_all.youtube import YouTubeMetadataGenerator, format_timestamp


def test_format_timestamp():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(59) == "00:59"
    assert format_timestamp(65) == "01:05"
    assert format_timestamp(3600) == "01:00:00"
    assert format_timestamp(3665) == "01:01:05"


def test_youtube_metadata_generator(tmp_path):
    gen = YouTubeMetadataGenerator()
    tracks = [
        Track(path=tmp_path / "t1.mp3", title="Track One", artist="Artist One", duration_seconds=180, bpm=126, camelot_key="8A"),
        Track(path=tmp_path / "t2.mp3", title="Track Two", artist="Artist Two", duration_seconds=200, bpm=128, camelot_key="9A")
    ]
    plan = MixPlan(
        tracks=tracks,
        transitions=[],
        segments=[
            MixSegment(track=tracks[0], start_time=0.0, end_time=180.0, audio_start_offset=0, audio_end_offset=180),
            MixSegment(track=tracks[1], start_time=150.0, end_time=350.0, audio_start_offset=0, audio_end_offset=200)
        ],
        total_duration_seconds=350.0,
        master_bpm=127.0
    )

    out_file = tmp_path / "YOUTUBE.md"
    gen.generate_metadata_file(plan, out_file, set_title="Test Mix")

    content = out_file.read_text()
    assert "00:00 Artist One - Track One [8A]" in content
    assert "02:30 Artist Two - Track Two [9A]" in content
    assert "Linkwitz-Riley 4th Order (LR4)" in content
    assert "Zero-Overlap Bass Swap" in content
