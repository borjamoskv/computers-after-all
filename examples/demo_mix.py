"""
Quickstart demonstration of Computers After All:
Synthesizes two minimal techno stems, executes an autonomous LR4 zero-overlap mix,
and renders an audio-reactive 1080p YouTube video.
"""

from pathlib import Path
import numpy as np
import soundfile as sf

from computers_after_all import (
    AutonomousDJ,
    ClubExporter,
    VideoConfig,
    VideoSynthesizer,
    YouTubeMetadataGenerator,
)


def generate_synthetic_techno_track(
    file_path: Path,
    bpm: float = 128.0,
    duration_sec: float = 30.0,
    bass_freq: float = 55.0,
    sr: int = 44100
):
    """Generates a punchy minimal techno loop with kick and hi-hats."""
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    audio = np.zeros((n_samples, 2), dtype=np.float32)

    beat_len = int((60.0 / bpm) * sr)
    kick_len = int(sr * 0.18)

    # 4/4 Kick drum with pitch drop
    for start in range(0, n_samples - kick_len, beat_len):
        t_kick = np.linspace(0, 0.18, kick_len)
        freq_env = bass_freq + 160.0 * np.exp(-t_kick * 30.0)
        kick = np.sin(2.0 * np.pi * freq_env * t_kick) * np.exp(-t_kick * 12.0)
        audio[start:start + kick_len, 0] += kick * 0.8
        audio[start:start + kick_len, 1] += kick * 0.8

    # Offbeat Hi-Hats
    hat_len = int(sr * 0.04)
    offbeat = beat_len // 2
    for start in range(offbeat, n_samples - hat_len, beat_len):
        hat = np.random.randn(hat_len).astype(np.float32) * np.exp(-np.linspace(0, 5, hat_len)) * 0.25
        audio[start:start + hat_len, 0] += hat
        audio[start:start + hat_len, 1] += hat

    sf.write(str(file_path), audio, sr, subtype="PCM_16")


def main():
    demo_dir = Path(__file__).parent / "demo_output"
    demo_dir.mkdir(parents=True, exist_ok=True)

    t1_path = demo_dir / "01 - Shed - Dark Cyber [11A - 128bpm].wav"
    t2_path = demo_dir / "02 - Kassem Mosse - Enoha [11B - 128bpm].wav"

    print("⚡ Generating synthetic source tracks for quickstart demo...")
    generate_synthetic_techno_track(t1_path, bpm=128.0, duration_sec=25.0, bass_freq=55.0)
    generate_synthetic_techno_track(t2_path, bpm=128.0, duration_sec=25.0, bass_freq=65.0)

    print("🎛️ Initializing AutonomousDJ...")
    dj = AutonomousDJ(default_transition_bars=8)  # 8 bars (~15s) for quick demo

    plan = dj.prepare_set([t1_path, t2_path], optimize_order=True, transition_bars=8)

    print("⚡ Rendering continuous master mix with LR4 Crossover & Zero-Overlap Bass Swap...")
    mp3_path, wav_path = dj.render_mix(plan, output_dir=demo_dir, mix_title="DEMO_COMPUTERS_AFTER_ALL")
    print(f"   ✓ MP3: {mp3_path}")
    print(f"   ✓ WAV: {wav_path}")

    # Exporters
    club = ClubExporter()
    xml_path = demo_dir / "DEMO_REKORDBOX.xml"
    club.export_rekordbox_xml(plan, xml_path, playlist_name="Demo Set")
    print(f"   ✓ Rekordbox XML: {xml_path}")

    yt_gen = YouTubeMetadataGenerator()
    yt_meta = demo_dir / "DEMO_YOUTUBE.md"
    yt_gen.generate_metadata_file(plan, yt_meta, set_title="Demo Mix")
    print(f"   ✓ YouTube Chapters: {yt_meta}")

    print("🎬 Synthesizing YouTube Reactive Video (1080p)...")
    synthesizer = VideoSynthesizer(config=VideoConfig(width=1280, height=720, fps=30))
    video_path = demo_dir / "DEMO_VIDEO.mp4"
    synthesizer.render_youtube_video(audio_path=mp3_path, plan=plan, output_video_path=video_path)
    print(f"   ✓ YouTube Video: {video_path}")

    thumb_path = demo_dir / "DEMO_THUMBNAIL.png"
    synthesizer.generate_thumbnail(plan, thumb_path, mix_title="DEMO COMPUTERS AFTER ALL")
    print(f"   ✓ YouTube Thumbnail: {thumb_path}")

    print("\n🎉 Quickstart completed successfully!")


if __name__ == "__main__":
    main()
