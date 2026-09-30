"""
YouTube Reactive Video Synthesizer: High-exergy audio-reactive visualizer
with Pillow HUD cards, real-time frequency spectrum, waveform oscilloscope,
and Apple Silicon hardware acceleration (VideoToolbox).
"""

from pathlib import Path
import subprocess
import tempfile
from typing import List, Optional
from PIL import Image, ImageDraw

from .models import MixPlan, VideoConfig


class VideoSynthesizer:
    """Generates broadcast-ready audio-reactive YouTube videos and thumbnails."""

    def __init__(self, config: Optional[VideoConfig] = None):
        self.config = config or VideoConfig()

    def generate_thumbnail(
        self,
        plan: MixPlan,
        output_path: Path,
        mix_title: str = "COMPUTERS AFTER ALL"
    ) -> Path:
        """Renders an aesthetic 1280x720 YouTube thumbnail."""
        out = Path(output_path).resolve()
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), color=(10, 12, 16))
        draw = ImageDraw.Draw(img)

        # Draw dark cyber grid lines
        for y in range(0, h, 40):
            draw.line([(0, y), (w, y)], fill=(20, 24, 32), width=1)
        for x in range(0, w, 40):
            draw.line([(x, 0), (x, h)], fill=(20, 24, 32), width=1)

        # Gradient glow box
        draw.rectangle([60, 60, w - 60, h - 60], outline=(0, 255, 204), width=3)
        draw.rectangle([70, 70, w - 70, h - 70], outline=(40, 60, 80), width=1)

        # Text badges
        draw.text((100, 100), "C5-REAL // AUTONOMOUS DJ SYSTEM", fill=(0, 255, 204))
        draw.text((100, 150), mix_title.upper(), fill=(255, 255, 255))

        subtitle = f"{len(plan.tracks)} TRACKS · {plan.master_bpm:.1f} BPM · CAMELOT HARMONIC MIX"
        draw.text((100, 240), subtitle, fill=(180, 190, 210))

        # Track preview list
        y_pos = 320
        for i, t in enumerate(plan.tracks[:7]):
            draw.text((100, y_pos), f"{i+1:02d}. {t.artist} - {t.title}", fill=(200, 210, 225))
            draw.text((w - 280, y_pos), f"[{t.camelot_key}]", fill=(0, 255, 204))
            y_pos += 45

        if len(plan.tracks) > 7:
            draw.text((100, y_pos), f"... + {len(plan.tracks) - 7} MORE UNDERGROUND GEMS", fill=(120, 140, 160))

        # Bottom branding tag
        draw.text((100, h - 110), "COMPUTERS AFTER ALL · ZERO-OVERLAP BASS SWAP · LR4 CROSSLINK", fill=(100, 120, 140))

        img.save(str(out), "PNG")
        return out

    def _render_base_hud(self, w: int, h: int, plan: MixPlan) -> Image.Image:
        """Creates the static HUD background canvas with cyberpunk branding and frame borders."""
        img = Image.new("RGBA", (w, h), (10, 12, 16, 255))
        draw = ImageDraw.Draw(img)

        # Subtle background grid
        for y in range(0, h, 60):
            draw.line([(0, y), (w, y)], fill=(18, 22, 30, 255), width=1)
        for x in range(0, w, 60):
            draw.line([(x, 0), (x, h)], fill=(18, 22, 30, 255), width=1)

        # Outer cybernetic border
        draw.rectangle([40, 40, w - 40, h - 40], outline=(0, 255, 204, 255), width=2)
        draw.rectangle([46, 46, w - 46, h - 46], outline=(30, 45, 60, 255), width=1)

        # Top Header HUD
        draw.text((80, 70), "COMPUTERS AFTER ALL // AUTONOMOUS DJ SYSTEM", fill=(0, 255, 204, 255))
        draw.text(
            (80, 110),
            f"MASTER TEMPO: {plan.master_bpm:.1f} BPM | 24 dB/OCT LINKWITZ-RILEY 4TH ORDER CROSSLINK",
            fill=(140, 160, 180, 255)
        )

        # Frequency Spectrum Frame
        spec_x = int(w * 0.05)
        spec_y = int(h * 0.22)
        spec_w = int(w * 0.90)
        spec_h = int(h * 0.50)

        draw.rectangle([spec_x, spec_y, spec_x + spec_w, spec_y + spec_h], outline=(40, 60, 80, 255), width=2)
        draw.text((spec_x + 15, spec_y + 12), "REAL-TIME FREQUENCY SPECTRUM & OSCILLOSCOPE (20 Hz - 20 kHz)", fill=(80, 110, 140, 255))

        # Bottom System Telemetry
        draw.text(
            (80, h - 80),
            "ZERO-OVERLAP BASS SWAP · ANTI-MASKING -1.2 dB MID DIP · EBU R128 (-14.0 LUFS) · REKORDBOX XML",
            fill=(100, 120, 140, 255)
        )

        return img

    def _render_track_card(self, track_idx: int, total_tracks: int, track) -> Image.Image:
        """Renders an individual 'Now Playing' card with Camelot badge and typography."""
        card_w = 850
        card_h = 110
        img = Image.new("RGBA", (card_w, card_h), (12, 16, 22, 230))
        draw = ImageDraw.Draw(img)

        # Glowing border
        draw.rectangle([0, 0, card_w - 1, card_h - 1], outline=(0, 255, 204, 255), width=2)
        draw.rectangle([4, 4, card_w - 5, card_h - 5], outline=(255, 0, 119, 160), width=1)

        # Line 1: Track title
        title_str = f"NOW PLAYING [{track_idx+1:02d}/{total_tracks:02d}] · {track.artist} - {track.title}"
        if len(title_str) > 52:
            title_str = title_str[:49] + "..."
        draw.text((25, 22), title_str, fill=(255, 255, 255, 255))

        # Line 2: Camelot Badge and BPM
        badge_str = f"KEY: {track.camelot_key} ({track.musical_key}) | TEMPO: {track.bpm:.1f} BPM | ENERGY: {track.energy:.2f}"
        draw.text((25, 62), badge_str, fill=(0, 255, 204, 255))

        return img

    def render_youtube_video(
        self,
        audio_path: Path,
        plan: MixPlan,
        output_video_path: Path
    ) -> Path:
        """
        Synthesizes an audio-reactive MP4 video using Pillow HUD overlays and FFmpeg.
        Hardware accelerated via h264_videotoolbox on Apple Silicon.
        """
        audio = Path(audio_path).resolve()
        out_video = Path(output_video_path).resolve()
        out_video.parent.mkdir(parents=True, exist_ok=True)

        w, h = self.config.width, self.config.height
        fps = self.config.fps

        spec_x = int(w * 0.05)
        spec_y = int(h * 0.22)
        spec_w = int(w * 0.90)
        spec_h = int(h * 0.50)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)

            # 1. Render Base HUD
            base_hud = self._render_base_hud(w, h, plan)
            base_hud_path = tmp / "base_hud.png"
            base_hud.save(str(base_hud_path), "PNG")

            # 2. Render Track Cards
            card_paths: List[Path] = []
            for i, seg in enumerate(plan.segments):
                card = self._render_track_card(i, len(plan.segments), seg.track)
                c_path = tmp / f"card_{i}.png"
                card.save(str(c_path), "PNG")
                card_paths.append(c_path)

            # 3. Assemble FFmpeg filtergraph
            # Base audio inputs and loops
            input_args = ["-i", str(audio), "-loop", "1", "-i", str(base_hud_path)]
            for cp in card_paths:
                input_args.extend(["-loop", "1", "-i", str(cp)])

            # Filtergraph steps
            fg_parts = [
                # Generate frequency spectrum bars in cyan/blue
                f"[0:a]showfreqs=s={spec_w-4}x{spec_h-40}:mode=bar:ascale=log:fscale=log:colors=0x00FFCC|0x0088AA,format=rgba[freqs];",
                # Generate oscillating waveform in magenta
                f"[0:a]showwaves=s={spec_w-4}x140:mode=line:colors=0xFF0077@0.6,format=rgba[waves];",
                # Overlay spectrum onto base HUD
                f"[1:v][freqs]overlay=x={spec_x+2}:y={spec_y+30}[v_spec];",
                # Overlay waveform
                f"[v_spec][waves]overlay=x={spec_x+2}:y={spec_y + spec_h//2 - 70}[v_waves];"
            ]

            last_stream = "[v_waves]"
            card_x = int(w * 0.05)
            card_y = int(h * 0.76)

            for i, seg in enumerate(plan.segments):
                input_idx = 2 + i
                next_stream = f"[v_card_{i}]" if i < len(plan.segments) - 1 else "[outv]"
                enable_clause = f"between(t,{seg.start_time:.2f},{seg.end_time:.2f})"
                fg_parts.append(
                    f"{last_stream}[{input_idx}:v]overlay=x={card_x}:y={card_y}:enable='{enable_clause}'{next_stream};"
                )
                last_stream = next_stream

            filtergraph = "".join(fg_parts).rstrip(";")

            # 4. Execute FFmpeg
            vcodec = "h264_videotoolbox" if self.config.hardware_accel else "libx264"
            cmd = [
                "ffmpeg", "-y",
                *input_args,
                "-filter_complex", filtergraph,
                "-map", "[outv]",
                "-map", "0:a",
                "-c:v", vcodec,
                "-b:v", "6000k",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "320k",
                "-shortest",
                str(out_video)
            ]

            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                cmd[cmd.index(vcodec)] = "libx264"
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        return out_video
