"""
Acoustic Analyzer: BPM detection, Camelot Key estimation, Energy profiling,
and phrasing anchor identification.
"""

from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import numpy as np
import soundfile as sf

from .models import CuePoint, Track


# Camelot to Musical Key bidirectional mapping
CAMELOT_TO_KEY: Dict[str, str] = {
    "1A": "Abm", "1B": "B",
    "2A": "Ebm", "2B": "F#",
    "3A": "Bbm", "3B": "Db",
    "4A": "Fm",  "4B": "Ab",
    "5A": "Cm",  "5B": "Eb",
    "6A": "Gm",  "6B": "Bb",
    "7A": "Dm",  "7B": "F",
    "8A": "Am",  "8B": "C",
    "9A": "Em",  "9B": "G",
    "10A": "Bm", "10B": "D",
    "11A": "F#m", "11B": "A",
    "12A": "C#m", "12B": "E",
}

KEY_TO_CAMELOT: Dict[str, str] = {v.lower(): k for k, v in CAMELOT_TO_KEY.items()}
KEY_TO_CAMELOT.update({
    "g#m": "1A", "d#m": "2A", "a#m": "3A", "a-flat minor": "1A",
    "f# minor": "11A", "a minor": "8A", "c major": "8B", "d minor": "7A"
})


class AudioAnalyzer:
    """Extracts metrical and harmonic telemetry from audio files."""

    def __init__(self, default_bpm: float = 128.0):
        self.default_bpm = default_bpm

    def analyze_track(self, file_path: Path) -> Track:
        """Fully analyzes an audio file and constructs a Track entity."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        # 1. Parse metadata hints from filename
        artist, title, key_hint, bpm_hint = self._parse_filename_hints(path.stem)

        # 2. Inspect audio info (duration, sample rate, channels)
        info = sf.info(str(path))
        sr = info.samplerate
        channels = info.channels
        duration = info.duration

        # 3. Read representative audio slice for signal processing
        # Load up to 60s from middle of track to estimate BPM and key efficiently
        mid_time = max(0.0, (duration / 2.0) - 30.0)
        frames_to_read = int(min(60.0, duration) * sr)
        start_frame = int(mid_time * sr)

        data, _ = sf.read(str(path), start=start_frame, frames=frames_to_read, always_2d=True)

        # Estimate BPM if not in filename
        if bpm_hint and 60.0 <= bpm_hint <= 180.0:
            bpm = bpm_hint
        else:
            bpm = self._estimate_bpm(data, sr)

        # Estimate Camelot key if not in filename
        if key_hint:
            camelot_key = key_hint
            musical_key = CAMELOT_TO_KEY.get(camelot_key, "")
        else:
            camelot_key, musical_key = self._estimate_key(data, sr)

        # Compute energy
        rms = float(np.sqrt(np.mean(data ** 2) + 1e-12))
        energy = float(np.clip(rms * 4.0, 0.1, 1.0))

        # Default phrase cue points based on 32-bar phrasing
        sec_per_bar = (60.0 / bpm) * 4.0
        mix_in_time = min(duration * 0.1, sec_per_bar * 4.0)
        mix_out_time = max(duration * 0.8, duration - (sec_per_bar * 8.0))
        bass_swap_time = mix_in_time + (sec_per_bar * 4.0)

        cues = [
            CuePoint(name="Intro", time_seconds=0.0, num=0),
            CuePoint(name="Mix In", time_seconds=mix_in_time, num=1),
            CuePoint(name="Bass Swap", time_seconds=bass_swap_time, num=2),
            CuePoint(name="Mix Out", time_seconds=mix_out_time, num=3),
        ]

        return Track(
            path=path,
            title=title,
            artist=artist,
            duration_seconds=duration,
            bpm=bpm,
            camelot_key=camelot_key,
            musical_key=musical_key,
            sample_rate=sr,
            channels=channels,
            energy=energy,
            beatgrid_offset=0.0,
            cues=cues
        )

    def _parse_filename_hints(self, stem: str) -> Tuple[str, str, Optional[str], Optional[float]]:
        """Extracts artist, title, camelot key, and BPM from filename strings."""
        artist = ""
        title = stem
        camelot_key = None
        bpm = None

        # Detect Camelot pattern (e.g., "11A", "8B", "4A")
        cam_match = re.search(r"\b([1-9]|1[0-2])[AB]\b", stem, re.IGNORECASE)
        if cam_match:
            camelot_key = cam_match.group(0).upper()

        # Detect BPM pattern (e.g., "128bpm", "128.00 BPM", "126 BPM")
        bpm_match = re.search(r"\b(1[0-9]{2}(?:\.[0-9]+)?)\s*bpm\b", stem, re.IGNORECASE)
        if bpm_match:
            try:
                bpm = float(bpm_match.group(1))
            except ValueError:
                pass

        # Split artist - title if hyphen present
        if " - " in stem:
            parts = stem.split(" - ", 1)
            artist = parts[0].strip()
            title = parts[1].strip()
            # Clean number prefix if present (e.g. "01. Artist" -> "Artist")
            artist = re.sub(r"^\d+[\.\-_]\s*", "", artist)

        return artist, title, camelot_key, bpm

    def _estimate_bpm(self, audio: np.ndarray, sr: int) -> float:
        """Estimates tempo via onset envelope autocorrelation."""
        mono = np.mean(audio, axis=1) if audio.ndim > 1 else audio

        # Subsample to ~1000 Hz for onset envelope
        hop = max(1, sr // 1000)
        sub = mono[::hop]
        sub_sr = sr / hop

        # Envelope via half-wave rectification of first derivative
        env = np.maximum(0, np.diff(np.abs(sub)))
        if len(env) < int(sub_sr * 2):
            return self.default_bpm

        # Autocorrelation of envelope
        corr = np.correlate(env, env, mode="full")
        corr = corr[len(corr) // 2:]

        # Search lags corresponding to 100 to 145 BPM
        min_bpm, max_bpm = 100.0, 145.0
        min_lag = int(sub_sr * 60.0 / max_bpm)
        max_lag = int(sub_sr * 60.0 / min_bpm)

        if max_lag >= len(corr):
            return self.default_bpm

        search_window = corr[min_lag:max_lag]
        if len(search_window) == 0:
            return self.default_bpm

        peak_lag = min_lag + int(np.argmax(search_window))
        detected_bpm = (sub_sr * 60.0) / peak_lag

        # Snap to nearest 0.5 BPM
        rounded_bpm = round(detected_bpm * 2.0) / 2.0
        return float(np.clip(rounded_bpm, 100.0, 145.0))

    def _estimate_key(self, audio: np.ndarray, sr: int) -> Tuple[str, str]:
        """
        Estimates musical key and Camelot code using a 12-pitch chromagram filterbank.
        """
        mono = np.mean(audio, axis=1) if audio.ndim > 1 else audio
        if len(mono) < sr:
            return "8A", "Am"

        # FFT Spectrum
        fft_len = 8192
        spectrum = np.abs(np.fft.rfft(mono[:fft_len]))
        freqs = np.fft.rfftfreq(fft_len, 1.0 / sr)

        # 12 Pitch Classes (A=440Hz standard)
        chroma = np.zeros(12)
        for i, f in enumerate(freqs):
            if 65.4 < f < 2093.0:  # C2 to C7
                midi_note = 69.0 + 12.0 * np.log2(f / 440.0)
                pitch_class = int(round(midi_note)) % 12
                chroma[pitch_class] += spectrum[i]

        # Template matching: Krumhansl-Schmuckler key profiles
        # Major and Minor profiles
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

        pitch_names = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

        best_score = -1e9
        best_key = "Am"

        for p in range(12):
            rotated = np.roll(chroma, -p)
            score_maj = float(np.corrcoef(rotated, major_profile)[0, 1])
            score_min = float(np.corrcoef(rotated, minor_profile)[0, 1])

            if score_maj > best_score:
                best_score = score_maj
                best_key = pitch_names[p]

            if score_min > best_score:
                best_score = score_min
                best_key = f"{pitch_names[p]}m"

        camelot = KEY_TO_CAMELOT.get(best_key.lower(), "8A")
        return camelot, best_key
