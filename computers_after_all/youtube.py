"""
YouTube Metadata Architect: Generates ready-to-publish chapter markers,
SEO descriptions, and metadata files for YouTube uploads.
"""

from pathlib import Path
from typing import List
from .models import MixPlan


def format_timestamp(seconds: float) -> str:
    """Formats seconds into MM:SS or HH:MM:SS format."""
    total_sec = int(round(seconds))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class YouTubeMetadataGenerator:
    """Produces YouTube Studio ready titles, descriptions, and chapters."""

    def generate_metadata_file(
        self,
        plan: MixPlan,
        output_path: Path,
        set_title: str = "COMPUTERS AFTER ALL"
    ) -> Path:
        """Writes comprehensive YouTube metadata markdown file."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        lines: List[str] = []

        # 1. Video Title
        video_title = f"{set_title.upper()} · Underground Techno Continuous Mix [{plan.master_bpm:.1f} BPM / Camelot Harmonic Flow]"
        lines.append(f"# YouTube Upload Metadata: {set_title}\n")
        lines.append(f"## Recommended Video Title\n```text\n{video_title}\n```\n")

        # 2. Description & Chapters
        lines.append("## Description (Copy & Paste to YouTube Studio)\n```text")
        lines.append(f"{set_title} — Autonomous DJ Set compiled and rendered in silicon.")
        lines.append("Acoustically calibrated with 3-Band Linkwitz-Riley 4th Order Crossover (LR4),")
        lines.append("Zero-Overlap Bass Swap at Beat 1.1, and EBU R128 (-14.0 LUFS) Broadcast Master.\n")
        lines.append("--- TRACKLIST & CHAPTERS ---")

        for i, seg in enumerate(plan.segments):
            t = seg.track
            ts = format_timestamp(seg.start_time)
            key_tag = f"[{t.camelot_key}]" if t.camelot_key else ""
            lines.append(f"{ts} {t.artist} - {t.title} {key_tag}")

        lines.append("\n--- TECHNICAL SPECIFICATIONS ---")
        lines.append(f"• Total Duration: {format_timestamp(plan.total_duration_seconds)}")
        lines.append(f"• Master BPM: {plan.master_bpm:.1f}")
        lines.append("• Crossover Filters: 24 dB/oct Linkwitz-Riley 4th Order (LR4)")
        lines.append("• Low-End Strategy: Zero-Overlap Bass Swap (30-160 Hz)")
        lines.append("• Mid Band Strategy: -1.2 dB Anti-Masking Dip")
        lines.append("• Tape Delay: 3/16 Dotted Dub Echo (42% Feedback)")
        lines.append("• Loudness Target: -14.0 LUFS Integrated (-1.0 dBTP True Peak)")
        lines.append("• Engine: Computers After All (C5-REAL Silicon DJ)")
        lines.append("```\n")

        # 3. Tags
        tags = [
            "underground techno", "dub techno", "continuous dj mix", "computers after all",
            "autonomous dj", "camelot harmonic mixing", "rekordbox", "linkwitz riley",
            "dark techno", "detroit electro", "minimal techno", "berlin techno", "ebu r128"
        ]
        lines.append("## Recommended Tags\n```text")
        lines.append(", ".join(tags))
        lines.append("```\n")

        out.write_text("\n".join(lines), encoding="utf-8")
        return out
