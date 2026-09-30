"""
Unit tests for DSP Linkwitz-Riley crossover, bass swap, and limiter.
"""

import numpy as np
from scipy.signal import butter
from computers_after_all.dsp import (
    LinkwitzRiley4Crossover,
    apply_psychoacoustic_mid_dip,
    apply_zero_overlap_bass_swap,
    master_ebu_r128_limiter,
    safe_filtfilt
)


def test_safe_filtfilt_short_input():
    b, a = butter(2, 0.2)
    short_x = np.ones(10)
    # Should not raise ValueError due to padlen
    res = safe_filtfilt(b, a, short_x)
    assert len(res) == 10
    np.testing.assert_array_equal(res, short_x)


def test_safe_filtfilt_normal_input():
    b, a = butter(2, 0.2)
    x = np.sin(np.linspace(0, 10, 200))
    res = safe_filtfilt(b, a, x)
    assert len(res) == 200


def test_linkwitz_riley_crossover_recombination():
    sr = 44100
    crossover = LinkwitzRiley4Crossover(sample_rate=sr, f_low=160.0, f_high=2800.0)

    # 1 second of stereo white noise
    np.random.seed(42)
    noise = np.random.randn(sr, 2).astype(np.float32)

    low, mid, high = crossover.split(noise)
    assert low.shape == noise.shape
    assert mid.shape == noise.shape
    assert high.shape == noise.shape

    # Interior region recombination (ignoring filter edge transients)
    recombined = low + mid + high
    margin = int(sr * 0.05)
    np.testing.assert_allclose(recombined[margin:-margin], noise[margin:-margin], atol=1e-2)


def test_zero_overlap_bass_swap():
    sr = 44100
    n_samples = 44100  # 1s
    low_a = np.ones((n_samples, 2), dtype=np.float32)
    low_b = np.full((n_samples, 2), 2.0, dtype=np.float32)

    swap_idx = 22050  # 0.5s
    res = apply_zero_overlap_bass_swap(low_a, low_b, swap_sample_idx=swap_idx, fade_len_samples=64)

    # Well before swap: purely track A
    assert np.allclose(res[:20000], 1.0)
    # Well after swap: purely track B
    assert np.allclose(res[24000:], 2.0)


def test_psychoacoustic_mid_dip():
    n = 1000
    mid_a = np.ones(n)
    mid_b = np.ones(n)

    out_a, out_b = apply_psychoacoustic_mid_dip(mid_a, mid_b, transition_len=n, dip_db=-1.2)
    assert len(out_a) == n
    assert len(out_b) == n

    # Midpoint should reflect -1.2 dB dip (< 1.0)
    midpoint_sum = out_a[n // 2] + out_b[n // 2]
    assert midpoint_sum < 1.4142


def test_master_ebu_r128_limiter():
    sr = 44100
    audio = np.random.randn(sr, 2) * 5.0  # Excessive level
    limited = master_ebu_r128_limiter(audio, target_lufs=-14.0, peak_ceiling_db=-1.0)

    ceiling = 10.0 ** (-1.0 / 20.0)
    assert np.max(np.abs(limited)) <= ceiling + 1e-4
