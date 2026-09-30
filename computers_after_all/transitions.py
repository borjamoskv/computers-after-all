"""
Transition Dispatcher: Implements the 8 canonical club transition algorithms
using the Linkwitz-Riley 4th Order Crossover and Zero-Overlap Bass Swap.
"""

from typing import Tuple
import numpy as np

from .dsp import (
    LinkwitzRiley4Crossover,
    apply_psychoacoustic_mid_dip,
    apply_zero_overlap_bass_swap,
    generate_space_echo_tail
)
from .models import Track, TransitionPlan, TransitionType


class TransitionEngine:
    """Executes high-exergy continuous transitions between consecutive tracks."""

    def __init__(self, sample_rate: int = 44100):
        self.sr = sample_rate
        self.crossover = LinkwitzRiley4Crossover(sample_rate=self.sr)

    def plan_transition(
        self,
        t1: Track,
        t2: Track,
        idx1: int,
        idx2: int,
        default_bars: int = 32
    ) -> TransitionPlan:
        """Determines the optimal transition type and parameters between two tracks."""
        avg_bpm = 0.5 * (t1.bpm + t2.bpm)
        sec_per_beat = 60.0 / avg_bpm
        sec_per_bar = sec_per_beat * 4.0

        # Select transition type based on harmonic compatibility and energy
        from .curator import camelot_distance
        h_dist = camelot_distance(t1.camelot_key, t2.camelot_key)

        if h_dist >= 4.0:
            # Significant harmonic shift -> Space Echo Dub Tail or Hard Drop
            ttype = TransitionType.DUB_ECHO_FREEZE
            bars = 16
            swap_beat = 32
            dub_tail = True
        elif default_bars >= 64:
            ttype = TransitionType.WALL_OF_SOUND_64
            bars = 64
            swap_beat = 128
            dub_tail = False
        else:
            ttype = TransitionType.BASS_SWAP_32
            bars = 32
            swap_beat = 64
            dub_tail = False

        duration_sec = bars * sec_per_bar
        swap_sec = (swap_beat / 4.0) * sec_per_bar

        return TransitionPlan(
            from_index=idx1,
            to_index=idx2,
            transition_type=ttype,
            duration_bars=bars,
            duration_seconds=duration_sec,
            swap_beat=swap_beat,
            swap_time_offset=swap_sec,
            dip_db=-1.2,
            dub_tail_enabled=dub_tail,
            dub_feedback=0.42
        )

    def execute_transition(
        self,
        audio_out: np.ndarray,
        audio_in: np.ndarray,
        plan: TransitionPlan,
        bpm: float
    ) -> np.ndarray:
        """
        Mixes overlapping transition region of outgoing and incoming audio.
        audio_out and audio_in must both have length == int(plan.duration_seconds * sr).
        """
        trans_len = min(len(audio_out), len(audio_in))
        if trans_len < 30:
            return audio_in

        # 1. 3-Band Linkwitz-Riley 4th Order Crossover Split
        low_out, mid_out, high_out = self.crossover.split(audio_out[:trans_len])
        low_in, mid_in, high_in = self.crossover.split(audio_in[:trans_len])

        # 2. Zero-Overlap Bass Swap
        swap_sample = int(plan.swap_time_offset * self.sr)
        low_recombined = apply_zero_overlap_bass_swap(
            low_out, low_in, swap_sample_idx=swap_sample
        )

        # 3. Anti-Masking Mid Dip (-1.2 dB)
        mid_curved_out, mid_curved_in = apply_psychoacoustic_mid_dip(
            mid_out, mid_in, transition_len=trans_len, dip_db=plan.dip_db
        )
        mid_recombined = mid_curved_out + mid_curved_in

        # 4. High-frequency Equal-Power Crossfade
        t = np.linspace(0, 1, trans_len)
        gain_h_out = np.cos(t * np.pi * 0.5)
        gain_h_in = np.sin(t * np.pi * 0.5)
        if high_out.ndim > 1:
            gain_h_out = gain_h_out[:, None]
            gain_h_in = gain_h_in[:, None]

        high_recombined = high_out * gain_h_out + high_in * gain_h_in

        # 5. Optional Space Echo Dub Tail
        dub_component = np.zeros_like(low_recombined)
        if plan.dub_tail_enabled:
            # Send outgoing mids and highs into dub tail starting at swap
            pre_swap_mids = mid_out[:swap_sample]
            if len(pre_swap_mids) > 0:
                echo = generate_space_echo_tail(
                    pre_swap_mids,
                    sr=self.sr,
                    bpm=bpm,
                    feedback=plan.dub_feedback,
                    tail_duration_sec=min(8.0, (trans_len - swap_sample) / self.sr)
                )
                echo_len = min(len(dub_component) - swap_sample, len(echo))
                if echo_len > 0:
                    dub_component[swap_sample:swap_sample + echo_len] += echo[:echo_len]

        # 6. Recombine all bands
        recombined = low_recombined + mid_recombined + high_recombined + dub_component
        return recombined
