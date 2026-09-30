"""
Unit tests for VideoSynthesizer thumbnail generation and visualizer configuration.
"""

from pathlib import Path
from computers_after_all.models import MixPlan, MixSegment, Track, VideoConfig
from computers_after_all.visualizer import VideoSynthesizer


def test_thumbnail_generation(tmp_path):
    synthesizer = VideoSynthesizer()
    tracks = [
        Track(path=tmp_path / "t1.mp3", title="Track 1", artist="Artist 1", duration_seconds=180, bpm=128, camelot_key="11A"),
        Track(path=tmp_path / "t2.mp3", title="Track 2", artist="Artist 2", duration_seconds=200, bpm=128, camelot_key="11B")
    ]
    plan = MixPlan(
        tracks=tracks,
        transitions=[],
        segments=[
            MixSegment(track=tracks[0], start_time=0.0, end_time=180.0, audio_start_offset=0, audio_end_offset=180),
            MixSegment(track=tracks[1], start_time=150.0, end_time=350.0, audio_start_offset=0, audio_end_offset=200)
        ],
        total_duration_seconds=350.0,
        master_bpm=128.0
    )

    thumb_path = tmp_path / "THUMBNAIL.png"
    synthesizer.generate_thumbnail(plan, thumb_path, mix_title="Test Mix")

    assert thumb_path.exists()
    assert thumb_path.stat().st_size > 1000


def test_base_hud_rendering():
    synthesizer = VideoSynthesizer(config=VideoConfig(width=640, height=360))
    tracks = [Track(path=Path("t1.mp3"), title="T1", artist="A1", duration_seconds=100, bpm=128, camelot_key="8A")]
    plan = MixPlan(tracks=tracks, transitions=[], segments=[], total_duration_seconds=100, master_bpm=128)

    img = synthesizer._render_base_hud(640, 360, plan)
    assert img.size == (640, 360)


def test_track_card_rendering():
    synthesizer = VideoSynthesizer()
    track = Track(path=Path("t1.mp3"), title="Dark Cyber", artist="Shed", duration_seconds=300, bpm=128, camelot_key="11A")
    card = synthesizer._render_track_card(0, 10, track)
    assert card.size[0] > 0
    assert card.size[1] > 0
