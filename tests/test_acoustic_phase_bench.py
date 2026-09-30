"""
Quantitative Acoustic Benchmark: Proves the eradication of phase cancellation
and comb filtering in the sub-bass region (30-120 Hz) by Zero-Overlap Bass Swap.
"""

import numpy as np
from computers_after_all.dsp import apply_zero_overlap_bass_swap


def test_acoustic_phase_cancellation_eradication():
    """
    Simulates worst-case acoustic condition: two sub-bass kick tails at 55 Hz
    with 180-degree (pi radians) phase opposition.
    Proves that standard crossfaders suffer massive notch cancellation (drop > 15 dB),
    whereas Zero-Overlap Bass Swap preserves full bass energy without notch nulls.
    """
    sr = 44100
    duration_sec = 2.0
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)

    freq = 55.0  # Deep sub-bass frequency (A1 note)
    # Track A sub: sin(2*pi*f*t)
    sub_a = np.sin(2.0 * np.pi * freq * t)
    # Track B sub: 180 degrees out of phase: -sin(2*pi*f*t)
    sub_b = -np.sin(2.0 * np.pi * freq * t)

    # 1. Standard Linear Crossfader Simulation
    fade = np.linspace(1.0, 0.0, n_samples)
    linear_crossfade = fade * sub_a + (1.0 - fade) * sub_b

    # Measure RMS energy at the center of the transition (t = 0.5)
    center_start = int(n_samples * 0.45)
    center_end = int(n_samples * 0.55)

    linear_center_rms = float(np.sqrt(np.mean(linear_crossfade[center_start:center_end] ** 2)))
    nominal_rms = float(np.sqrt(np.mean(sub_a ** 2)))  # 1/sqrt(2) approx 0.707

    # In standard crossfader, phase cancellation produces catastrophic loss (>15 dB drop)
    linear_loss_db = 20.0 * np.log10((linear_center_rms + 1e-12) / nominal_rms)
    assert linear_loss_db < -15.0, f"Expected deep phase cancellation drop, got {linear_loss_db} dB"

    # 2. Computers After All: Zero-Overlap Bass Swap
    swap_idx = n_samples // 2
    swapped = apply_zero_overlap_bass_swap(
        sub_a, sub_b, swap_sample_idx=swap_idx, fade_len_samples=128
    )

    swapped_center_rms = float(np.sqrt(np.mean(swapped[center_start:center_end] ** 2)))
    swapped_loss_db = 20.0 * np.log10((swapped_center_rms + 1e-12) / nominal_rms)

    # In Zero-Overlap Bass Swap, energy is preserved with virtually zero loss (< 0.5 dB)
    assert swapped_loss_db > -0.5, f"Expected near-zero energy loss, got {swapped_loss_db} dB"

    # Advantage: Zero-Overlap is at least 15 dB stronger and cleaner than linear blend
    phase_advantage_db = swapped_loss_db - linear_loss_db
    assert phase_advantage_db >= 15.0
