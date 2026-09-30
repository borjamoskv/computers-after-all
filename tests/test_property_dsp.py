"""
Property-based invariant testing for DSP engine using Hypothesis.
"""

from hypothesis import given, settings, strategies as st
import numpy as np
from scipy.signal import butter

from computers_after_all.dsp import (
    LinkwitzRiley4Crossover,
    apply_zero_overlap_bass_swap,
    master_ebu_r128_limiter,
    safe_filtfilt
)


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=0, max_value=250))
def test_property_safe_filtfilt_length_invariance(length: int):
    """Property: safe_filtfilt never raises an exception for ANY array length >= 0."""
    b, a = butter(2, 0.2)
    x = np.random.randn(length).astype(np.float32)
    res = safe_filtfilt(b, a, x)
    assert len(res) == length
    assert res.dtype == np.float32 or len(res) == 0


@settings(max_examples=40, deadline=None)
@given(
    st.floats(min_value=-18.0, max_value=12.0),
    st.floats(min_value=-6.0, max_value=-0.1)
)
def test_property_limiter_brickwall_guarantee(gain_boost: float, ceiling_db: float):
    """Property: master_ebu_r128_limiter strictly guarantees peak <= ceiling under extreme dynamics."""
    # Generate hot input signal
    np.random.seed(0)
    raw = np.random.randn(2000, 2).astype(np.float32) * (10.0 ** (gain_boost / 20.0))
    limited = master_ebu_r128_limiter(raw, target_lufs=-14.0, peak_ceiling_db=ceiling_db)

    ceiling_linear = 10.0 ** (ceiling_db / 20.0)
    max_peak = float(np.max(np.abs(limited)))

    assert max_peak <= ceiling_linear + 1e-4, f"Peak {max_peak} exceeded ceiling {ceiling_linear}"


@settings(max_examples=30, deadline=None)
@given(st.integers(min_value=100, max_value=800))
def test_property_zero_overlap_bass_swap_temporal_isolation(swap_point: int):
    """Property: low_a is zero after swap_point and low_b is zero before swap_point."""
    total_samples = 1000
    low_a = np.ones((total_samples, 2), dtype=np.float32) * 5.0
    low_b = np.ones((total_samples, 2), dtype=np.float32) * 10.0

    fade_samples = 32
    swapped = apply_zero_overlap_bass_swap(
        low_a, low_b, swap_sample_idx=swap_point, fade_len_samples=fade_samples
    )

    # Invariant: sufficiently before swap point, audio must reflect only low_a
    safe_pre = max(0, swap_point - fade_samples - 5)
    if safe_pre > 0:
        np.testing.assert_allclose(swapped[:safe_pre], 5.0, atol=1e-3)

    # Invariant: sufficiently after swap point, audio must reflect only low_b
    safe_post = min(total_samples, swap_point + fade_samples + 5)
    if safe_post < total_samples:
        np.testing.assert_allclose(swapped[safe_post:], 10.0, atol=1e-3)
