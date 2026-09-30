"""
End-to-End CLI command tests for computers-after-all.
"""

from pathlib import Path
import subprocess
import sys
import numpy as np
import soundfile as sf


def create_mini_track(path: Path, bpm: float = 126.0, duration_sec: float = 6.0, freq: float = 60.0):
    sr = 44100
    n = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n, endpoint=False)
    audio = np.sin(2.0 * np.pi * freq * t) * 0.7
    audio = np.column_stack([audio, audio]).astype(np.float32)
    sf.write(str(path), audio, sr, subtype="PCM_16")


def test_cli_help():
    res = subprocess.run([sys.executable, "-m", "computers_after_all", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "mix" in res.stdout
    assert "analyze" in res.stdout


def test_cli_analyze(tmp_path):
    track_path = tmp_path / "01 - Shed - Boom Room [11A - 128bpm].wav"
    create_mini_track(track_path, bpm=128.0, duration_sec=5.0)

    res = subprocess.run(
        [sys.executable, "-m", "computers_after_all", "analyze", str(track_path)],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "11A" in res.stdout
    assert "128.0" in res.stdout
    assert "Track Analysis" in res.stdout


def test_cli_mix_execution(tmp_path):
    t1 = tmp_path / "01 - ArtistA - TrackA [8A - 126bpm].wav"
    t2 = tmp_path / "02 - ArtistB - TrackB [8B - 126bpm].wav"
    create_mini_track(t1, bpm=126.0, duration_sec=10.0, freq=55.0)
    create_mini_track(t2, bpm=126.0, duration_sec=10.0, freq=65.0)

    out_dir = tmp_path / "cli_output"

    cmd = [
        sys.executable, "-m", "computers_after_all", "mix",
        "-t", str(t1), str(t2),
        "-b", "4",
        "--title", "TEST_CLI_SESSION",
        "-o", str(out_dir),
        "--no-video"
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI mix failed: {res.stderr}"

    # Check generated files
    assert (out_dir / "TEST_CLI_SESSION.mp3").exists()
    assert (out_dir / "TEST_CLI_SESSION.wav").exists()
    assert (out_dir / "TEST_CLI_SESSION_REKORDBOX.xml").exists()
    assert (out_dir / "TEST_CLI_SESSION.cue").exists()
    assert (out_dir / "TEST_CLI_SESSION.m3u8").exists()
    assert (out_dir / "TEST_CLI_SESSION_YOUTUBE_METADATA.md").exists()
