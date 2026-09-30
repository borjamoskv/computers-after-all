"""
Command Line Interface for Computers After All:
Autonomous DJ System & Reactive YouTube Video Synthesizer.
"""

import argparse
from pathlib import Path
import sys
from typing import List

from .analyzer import AudioAnalyzer
from .downloader import TrackDownloader
from .engine import AutonomousDJ
from .models import MixPlan, VideoConfig
from .rekordbox import ClubExporter
from .visualizer import VideoSynthesizer
from .youtube import YouTubeMetadataGenerator


DEFAULT_EXPORT_DIR = Path.home() / "Music" / "Computers After All Exports"


def parse_args():
    parser = argparse.ArgumentParser(
        prog="computers-after-all",
        description="Computers After All · Autonomous DJ System & Reactive YouTube Video Synthesizer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. 'mix' command
    mix_p = subparsers.add_parser("mix", help="Create an autonomous DJ set and YouTube reactive video")
    mix_p.add_argument("-t", "--tracks", nargs="+", help="Audio file paths or search queries", default=[])
    mix_p.add_argument("-d", "--dir", type=str, help="Directory containing audio tracks to mix")
    mix_p.add_argument("-q", "--query", action="append", help="Track name to fetch via yt-dlp", default=[])
    mix_p.add_argument("-b", "--bars", type=int, default=32, help="Transition length in bars (default: 32)")
    mix_p.add_argument("--title", type=str, default="COMPUTERS_AFTER_ALL_MIX", help="Mix title")
    mix_p.add_argument("-o", "--out", type=str, default=str(DEFAULT_EXPORT_DIR), help="Output directory")
    mix_p.add_argument("--video", action="store_true", default=True, help="Render audio-reactive YouTube video")
    mix_p.add_argument("--no-video", dest="video", action="store_false", help="Skip video rendering")
    mix_p.add_argument("--no-optimize", action="store_true", help="Preserve input track order (skip Camelot TSP)")
    mix_p.add_argument("--theme", type=str, default="cyber_noir", choices=["cyber_noir", "industrial_terminal", "acid_minimal"])

    # 2. 'analyze' command
    analyze_p = subparsers.add_parser("analyze", help="Inspect BPM, Camelot Key, and Cue Points of an audio track")
    analyze_p.add_argument("file", type=str, help="Path to audio file")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "analyze":
        analyzer = AudioAnalyzer()
        p = Path(args.file).resolve()
        if not p.exists():
            print(f"Error: File not found: {p}", file=sys.stderr)
            sys.exit(1)
        track = analyzer.analyze_track(p)
        print(f"\n🎧 Track Analysis: {track.display_name}")
        print(f"   • Duration:    {track.duration_seconds:.1f} s")
        print(f"   • BPM:         {track.bpm:.1f}")
        print(f"   • Camelot Key: {track.camelot_key} ({track.musical_key})")
        print(f"   • Energy:      {track.energy:.2f}")
        print("   • Cue Points:")
        for c in track.cues:
            print(f"     [{c.num}] {c.name}: {c.time_seconds:.2f} s")
        sys.exit(0)

    if args.command == "mix":
        input_paths: List[Path] = []

        # Collect from --dir
        if args.dir:
            d = Path(args.dir).resolve()
            if d.exists() and d.is_dir():
                for ext in ["*.mp3", "*.wav", "*.aif", "*.aiff", "*.flac"]:
                    input_paths.extend(d.glob(ext))
            else:
                print(f"Warning: Directory not found: {d}", file=sys.stderr)

        # Collect from --tracks (could be paths or queries)
        downloader = TrackDownloader()
        for item in args.tracks:
            p = Path(item).resolve()
            if p.exists() and p.is_file():
                input_paths.append(p)
            else:
                print(f"🔍 Searching & downloading track: '{item}'...")
                dl_path = downloader.fetch_track(item)
                if dl_path:
                    input_paths.append(dl_path)
                else:
                    print(f"⚠️ Could not resolve track query: '{item}'", file=sys.stderr)

        # Collect from --query
        for q in args.query:
            print(f"🔍 Fetching query: '{q}'...")
            dl_path = downloader.fetch_track(q)
            if dl_path:
                input_paths.append(dl_path)

        if len(input_paths) < 2:
            print("Error: Need at least 2 tracks to generate a DJ mix.", file=sys.stderr)
            sys.exit(1)

        out_dir = Path(args.out).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n🎛️ COMPUTERS AFTER ALL · AUTONOMOUS DJ SYSTEM")
        print(f"   • Ingesting {len(input_paths)} tracks...")
        print(f"   • Transition phrasing: {args.bars} bars (Linkwitz-Riley 4th Order LR4)")
        print(f"   • Low-End Strategy: Zero-Overlap Bass Swap at Beat 1.1")

        dj = AutonomousDJ(default_transition_bars=args.bars)
        plan = dj.prepare_set(
            track_paths=input_paths,
            optimize_order=not args.no_optimize,
            transition_bars=args.bars
        )

        print(f"\n📋 Planned Setlist Sequence ({len(plan.tracks)} tracks):")
        for i, t in enumerate(plan.tracks):
            print(f"   {i+1:02d}. [{t.camelot_key}] {t.bpm:.1f} BPM | {t.display_name}")

        print(f"\n⚡ Rendering Master Mix ({plan.total_duration_seconds / 60.0:.1f} min)...")
        mp3_path, wav_path = dj.render_mix(plan, output_dir=out_dir, mix_title=args.title)
        print(f"   ✓ MP3 Master: {mp3_path}")
        print(f"   ✓ WAV Master: {wav_path}")

        # Exporters
        club_exporter = ClubExporter()
        xml_path = out_dir / f"{args.title}_REKORDBOX.xml"
        club_exporter.export_rekordbox_xml(plan, xml_path, playlist_name=args.title)
        print(f"   ✓ Pioneer Rekordbox XML: {xml_path}")

        cue_path = out_dir / f"{args.title}.cue"
        club_exporter.export_cue_sheet(plan, cue_path, audio_filename=mp3_path.name)
        print(f"   ✓ CUE Sheet: {cue_path}")

        m3u8_path = out_dir / f"{args.title}.m3u8"
        club_exporter.export_m3u8(plan, m3u8_path)
        print(f"   ✓ M3U8 Playlist: {m3u8_path}")

        yt_gen = YouTubeMetadataGenerator()
        yt_meta_path = out_dir / f"{args.title}_YOUTUBE_METADATA.md"
        yt_gen.generate_metadata_file(plan, yt_meta_path, set_title=args.title)
        print(f"   ✓ YouTube Chapters & Metadata: {yt_meta_path}")

        # YouTube Video Synthesis
        if args.video:
            print(f"\n🎬 Synthesizing YouTube Reactive Video (1080p / 30fps)...")
            v_config = VideoConfig(theme=args.theme)
            synthesizer = VideoSynthesizer(config=v_config)

            thumb_path = out_dir / f"{args.title}_THUMBNAIL.png"
            synthesizer.generate_thumbnail(plan, thumb_path, mix_title=args.title)
            print(f"   ✓ YouTube Thumbnail: {thumb_path}")

            video_path = out_dir / f"{args.title}_VIDEO.mp4"
            synthesizer.render_youtube_video(audio_path=mp3_path, plan=plan, output_video_path=video_path)
            print(f"   ✓ YouTube Video: {video_path}")

        print(f"\n🎉 Done! All assets successfully created in: {out_dir}\n")


if __name__ == "__main__":
    main()
