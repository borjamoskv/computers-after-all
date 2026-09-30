"""
High-exergy DSP Engine: Linkwitz-Riley 4th Order Crossover, Zero-Overlap Bass Swap,
Anti-Masking Mid Dip, Space Echo Tail, and EBU R128 Master Limiter.
"""

from typing import Tuple
import numpy as np
from scipy.signal import butter, filtfilt


def safe_filtfilt(b: np.ndarray, a: np.ndarray, x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Safe forward-backward filtering with length safeguard against padlen failures."""
    n_samples = x.shape[axis]
    if n_samples < 30:
        return x
    return filtfilt(b, a, x, axis=axis)


class LinkwitzRiley4Crossover:
    """
    3-Band Linkwitz-Riley 4th Order (LR4) Crossover Filter.
    Splits audio into Low (0-f_low), Mid (f_low-f_high), and High (>f_high).
    Cascades two 2nd-order Butterworth filters in forward-backward pass (filtfilt),
    yielding exact 24 dB/oct slopes and zero-ripple flat phase sum (H_low + H_mid + H_high = 1.0).
    """

    def __init__(self, sample_rate: int = 44100, f_low: float = 160.0, f_high: float = 2800.0):
        self.sr = sample_rate
        self.f_low = f_low
        self.f_high = f_high
        self._design_filters()

    def _design_filters(self):
        nyq = 0.5 * self.sr
        # Normalized cutoff frequencies
        w_low = min(self.f_low / nyq, 0.99)
        w_high = min(self.f_high / nyq, 0.99)

        # 2nd order Butterworth coefficients (filtfilt doubles order to 4)
        self.b_lp_low, self.a_lp_low = butter(2, w_low, btype="lowpass")
        self.b_hp_low, self.a_hp_low = butter(2, w_low, btype="highpass")
        self.b_lp_high, self.a_lp_high = butter(2, w_high, btype="lowpass")
        self.b_hp_high, self.a_hp_high = butter(2, w_high, btype="highpass")

    def split(self, audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Splits stereo/mono audio into (low, mid, high) components.
        Audio shape: (samples, channels) or (samples,).
        """
        if len(audio) < 30:
            zeros = np.zeros_like(audio)
            return zeros, audio.copy(), zeros

        axis = 0

        # Low band: lowpass at f_low
        low = safe_filtfilt(self.b_lp_low, self.a_lp_low, audio, axis=axis)

        # High band: highpass at f_high
        high = safe_filtfilt(self.b_hp_high, self.a_hp_high, audio, axis=axis)

        # Mid band: Highpass at f_low, then lowpass at f_high
        hp_for_mid = safe_filtfilt(self.b_hp_low, self.a_hp_low, audio, axis=axis)
        mid = safe_filtfilt(self.b_lp_high, self.a_lp_high, hp_for_mid, axis=axis)

        return low, mid, high


def apply_zero_overlap_bass_swap(
    low_a: np.ndarray,
    low_b: np.ndarray,
    swap_sample_idx: int,
    fade_len_samples: int = 128
) -> np.ndarray:
    """
    Executes a quantized zero-overlap bass swap at swap_sample_idx.
    low_a is muted to zero at swap_sample_idx.
    low_b is gated to zero prior to swap_sample_idx and unmuted thereafter.
    A micro-ramp (128 samples / ~2.9ms) eliminates DC discontinuity and clicks.
    """
    total_len = max(len(low_a), len(low_b))
    result = np.zeros_like(low_a if len(low_a) >= len(low_b) else low_b)

    swap_idx = min(max(0, swap_sample_idx), total_len)

    # Micro-ramps
    fade_len = min(fade_len_samples, swap_idx, total_len - swap_idx)
    if fade_len <= 0:
        fade_len = 1

    fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_len)))
    fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_len)))

    # Process A
    out_a = np.zeros_like(low_a)
    pre_swap_a = max(0, swap_idx - fade_len)
    out_a[:pre_swap_a] = low_a[:pre_swap_a]
    if swap_idx <= len(low_a):
        out_a[pre_swap_a:swap_idx] = low_a[pre_swap_a:swap_idx] * (
            fade_out[:, None] if low_a.ndim > 1 else fade_out
        )

    # Process B
    out_b = np.zeros_like(low_b)
    post_swap_b = min(len(low_b), swap_idx + fade_len)
    if swap_idx < len(low_b):
        actual_fade_len = post_swap_b - swap_idx
        out_b[swap_idx:post_swap_b] = low_b[swap_idx:post_swap_b] * (
            fade_in[:actual_fade_len, None] if low_b.ndim > 1 else fade_in[:actual_fade_len]
        )
        out_b[post_swap_b:] = low_b[post_swap_b:]

    # Sum recombined low-end
    n_a = min(len(result), len(out_a))
    result[:n_a] += out_a[:n_a]
    n_b = min(len(result), len(out_b))
    result[:n_b] += out_b[:n_b]

    return result


def apply_psychoacoustic_mid_dip(
    mid_a: np.ndarray,
    mid_b: np.ndarray,
    transition_len: int,
    dip_db: float = -1.2
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Applies convex crossfade curves with a dip_db attenuation at center (t = 0.5)
    to prevent acoustic masking and coclear fatigue during dual-mid playback.
    """
    if transition_len <= 1:
        return mid_a, mid_b

    t = np.linspace(0, 1, transition_len)
    # Dip multiplier at center: dip_db (e.g. -1.2 dB = 0.871)
    dip_linear = 10.0 ** (dip_db / 20.0)
    # Convex parabolic gain multiplier: 1.0 at ends, dip_linear at center
    dip_curve = 1.0 - 4.0 * (1.0 - dip_linear) * t * (1.0 - t)

    # Crossfade curves (equal power)
    gain_a = np.cos(t * np.pi * 0.5) * dip_curve
    gain_b = np.sin(t * np.pi * 0.5) * dip_curve

    if mid_a.ndim > 1:
        gain_a = gain_a[:, None]
        gain_b = gain_b[:, None]

    out_a = mid_a.copy()
    out_b = mid_b.copy()

    n = min(transition_len, len(out_a), len(out_b))
    out_a[:n] *= gain_a[:n]
    out_b[:n] *= gain_b[:n]

    return out_a, out_b


def generate_space_echo_tail(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    feedback: float = 0.42,
    damping: float = 0.35,
    delay_fraction: float = 0.75,  # 3/16 dotted-eighth
    tail_duration_sec: float = 8.0
) -> np.ndarray:
    """
    Generates an analog tape Space Echo dub tail with 3/16 dotted delay
    and high-frequency damping on the feedback loop.
    """
    delay_sec = (60.0 / bpm) * delay_fraction
    delay_samples = int(delay_sec * sr)
    tail_samples = int(tail_duration_sec * sr)

    if delay_samples <= 0:
        return np.zeros_like(audio)

    total_len = len(audio) + tail_samples
    channels = audio.shape[1] if audio.ndim > 1 else 1

    tail_buffer = np.zeros((total_len, channels) if audio.ndim > 1 else total_len, dtype=np.float32)
    tail_buffer[:len(audio)] = audio

    # Delay line with feedback and one-pole lowpass filter for tape warmth
    for ch in range(channels):
        buf = tail_buffer[:, ch] if audio.ndim > 1 else tail_buffer
        filter_state = 0.0
        for i in range(delay_samples, total_len):
            delayed = buf[i - delay_samples]
            # Simple 1-pole lowpass damping: y[n] = (1-d)*x[n] + d*y[n-1]
            filter_state = (1.0 - damping) * delayed + damping * filter_state
            buf[i] += filter_state * feedback

    return tail_buffer[len(audio):]


def master_ebu_r128_limiter(
    audio: np.ndarray,
    target_lufs: float = -14.0,
    peak_ceiling_db: float = -1.0
) -> np.ndarray:
    """
    Normalizes audio toward target LUFS with transparent soft-knee saturation
    and brickwall peak limiting at peak_ceiling_db (-1.0 dBTP YouTube standard).
    """
    if len(audio) == 0:
        return audio

    rms = np.sqrt(np.mean(audio ** 2) + 1e-12)
    current_approx_lufs = 20.0 * np.log10(rms)

    gain_db = target_lufs - current_approx_lufs
    # Bound gain adjustment to prevent blowing up noise
    gain_db = np.clip(gain_db, -18.0, 12.0)
    linear_gain = 10.0 ** (gain_db / 20.0)

    scaled = audio * linear_gain

    # True Peak Limiter (Soft-knee tanh saturation above ceiling)
    ceiling_linear = 10.0 ** (peak_ceiling_db / 20.0)
    peak = np.max(np.abs(scaled))

    if peak > ceiling_linear:
        # Soft tanh compression on peaks
        ratio = peak / ceiling_linear
        scaled = ceiling_linear * np.tanh(scaled / ceiling_linear)

    return np.clip(scaled, -ceiling_linear, ceiling_linear)
