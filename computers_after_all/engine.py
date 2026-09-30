"""
Autonomous DJ Engine: Orchestrates track ingestion, harmonic sequencing,
continuous DSP transitions, master rendering, and export dispatch.
"""

from pathlib import Path
import subprocess
from typing import List, Optional, Tuple
import numpy as np
import soundfile as sf

from .analyzer import AudioAnalyzer
from .curator import SetlistCurator
from .dsp import master_ebu_r128_limiter
from .models import MixPlan, MixResult, MixSegment, Track, TransitionPlan, VideoConfig
from .transitions import TransitionEngine


class AutonomousDJ:
    """The central Autonomous DJ operator: from raw tracks to club mix & YouTube video."""

    def __init__(self, sample_rate: int = 44100, default_transition_bars: int = 32):
        self.sr = sample_rate
        self.default_transition_bars = default_transition_bars
        self.analyzer = AudioAnalyzer()
        self.curator = SetlistCurator()
        self.transition_engine = TransitionEngine(sample_rate=self.sr)

    def prepare_set(
        self,
        track_paths: List[Path],
        optimize_order: bool = True,
        transition_bars: Optional[int] = None
    ) -> MixPlan:
        """Analyzes, sequences, and plans timeline for the entire set."""
        bars = transition_bars or self.default_transition_bars

        # 1. Analyze all tracks
        tracks: List[Track] = []
        for p in track_paths:
            t = self.analyzer.analyze_track(Path(p))
            tracks.append(t)

        if not tracks:
            raise ValueError("No valid tracks provided to AutonomousDJ")

        # 2. Optimize harmonic and energy sequence
        if optimize_order and len(tracks) > 2:
            tracks = self.curator.optimize_sequence(tracks)

        # 3. Plan transitions and timeline
        transitions: List[TransitionPlan] = []
        segments: List[MixSegment] = []

        master_bpm = float(np.mean([t.bpm for t in tracks]))

        # Calculate transition parameters
        current_time = 0.0
        track_starts = [0.0] * len(tracks)

        for i in range(len(tracks) - 1):
            t1 = tracks[i]
            t2 = tracks[i + 1]

            t_plan = self.transition_engine.plan_transition(
                t1, t2, idx1=i, idx2=i + 1, default_bars=bars
            )

            # Cap transition duration so it never exceeds 45% of either track
            max_allowed_dur = min(t1.duration_seconds * 0.45, t2.duration_seconds * 0.45)
            if t_plan.duration_seconds > max_allowed_dur:
                t_plan.duration_seconds = max_allowed_dur
                t_plan.swap_time_offset = max_allowed_dur * 0.5

            transitions.append(t_plan)
            # Next track starts when transition starts
            track_starts[i + 1] = track_starts[i] + t1.duration_seconds - t_plan.duration_seconds

        # Compute segments and total timeline
        for i, t in enumerate(tracks):
            start = track_starts[i]
            end = start + t.duration_seconds
            segments.append(MixSegment(
                track=t,
                start_time=start,
                end_time=end,
                audio_start_offset=0.0,
                audio_end_offset=t.duration_seconds
            ))

        total_duration = segments[-1].end_time

        return MixPlan(
            tracks=tracks,
            transitions=transitions,
            segments=segments,
            total_duration_seconds=total_duration,
            master_bpm=master_bpm
        )

    def render_mix(
        self,
        plan: MixPlan,
        output_dir: Path,
        mix_title: str = "COMPUTERS_AFTER_ALL_MIX"
    ) -> Tuple[Path, Path]:
        """
        Renders the planned mix to high-resolution WAV and MP3 files.
        Returns (mp3_path, wav_path).
        """
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        wav_path = out_dir / f"{mix_title}.wav"
        mp3_path = out_dir / f"{mix_title}.mp3"

        total_samples = int(plan.total_duration_seconds * self.sr) + (self.sr * 2)
        mix_buffer = np.zeros((total_samples, 2), dtype=np.float32)

        # 1. Load all track audios into memory
        track_audios = []
        for t in plan.tracks:
            data, _ = sf.read(str(t.path), always_2d=True)
            if data.shape[1] == 1:
                data = np.repeat(data, 2, axis=1)
            track_audios.append(data)

        # 2. Render solo regions and transitions
        for i, seg in enumerate(plan.segments):
            data = track_audios[i]
            t_start = seg.start_time
            t_len = seg.track.duration_seconds

            # Solo start offset in track data
            in_offset_sec = 0.0
            if i > 0:
                in_offset_sec = plan.transitions[i - 1].duration_seconds

            # Solo end offset in track data
            out_offset_sec = t_len
            if i < len(plan.transitions):
                out_offset_sec = t_len - plan.transitions[i].duration_seconds

            # Render solo portion
            if out_offset_sec > in_offset_sec:
                solo_start_samp = int(in_offset_sec * self.sr)
                solo_end_samp = int(out_offset_sec * self.sr)
                solo_data = data[solo_start_samp:solo_end_samp]

                mix_start_samp = int((t_start + in_offset_sec) * self.sr)
                mix_end_samp = mix_start_samp + len(solo_data)

                if mix_end_samp <= len(mix_buffer):
                    mix_buffer[mix_start_samp:mix_end_samp] = solo_data

            # Render transition with next track
            if i < len(plan.transitions):
                trans_plan = plan.transitions[i]
                next_data = track_audios[i + 1]

                trans_samples = int(trans_plan.duration_seconds * self.sr)

                # Tail of current track
                out_slice = data[-trans_samples:]
                # Head of next track
                in_slice = next_data[:trans_samples]

                # Match lengths if needed
                common_len = min(len(out_slice), len(in_slice))
                out_slice = out_slice[:common_len]
                in_slice = in_slice[:common_len]

                blended = self.transition_engine.execute_transition(
                    audio_out=out_slice,
                    audio_in=in_slice,
                    plan=trans_plan,
                    bpm=plan.master_bpm
                )

                # Transition start time on timeline
                trans_start_time = plan.segments[i + 1].start_time
                trans_start_samp = int(trans_start_time * self.sr)
                trans_end_samp = trans_start_samp + len(blended)

                if trans_end_samp <= len(mix_buffer):
                    mix_buffer[trans_start_samp:trans_end_samp] = blended

        # Trim to exact total duration
        actual_samples = int(plan.total_duration_seconds * self.sr)
        final_audio = mix_buffer[:actual_samples]

        # Apply EBU R128 Master Limiter (-14.0 LUFS)
        mastered = master_ebu_r128_limiter(final_audio, target_lufs=-14.0, peak_ceiling_db=-1.0)

        # Write WAV
        sf.write(str(wav_path), mastered, self.sr, subtype="PCM_16")

        # Encode MP3 via ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-b:a", "320k",
            str(mp3_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return mp3_path, wav_path
