"""
Tests for multi-sample rate (44.1k, 48k, 96k) and channel topologies (mono, stereo).
"""

import numpy as np
from computers_after_all.dsp import LinkwitzRiley4Crossover
from computers_after_all.models import Track, TransitionPlan, TransitionType
from computers_after_all.transitions import TransitionEngine


def test_crossover_at_different_samplerates():
    for sr in [44100, 48000, 88200, 96000]:
        crossover = LinkwitzRiley4Crossover(sample_rate=sr, f_low=160.0, f_high=2800.0)
        audio = np.random.randn(sr, 2).astype(np.float32)

        low, mid, high = crossover.split(audio)
        assert low.shape == audio.shape
        assert mid.shape == audio.shape
        assert high.shape == audio.shape

        recomb = low + mid + high
        margin = int(sr * 0.05)
        np.testing.assert_allclose(recomb[margin:-margin], audio[margin:-margin], atol=1e-2)


def test_transition_engine_mono_and_stereo():
    sr = 48000
    engine = TransitionEngine(sample_rate=sr)

    plan = TransitionPlan(
        from_index=0,
        to_index=1,
        transition_type=TransitionType.BASS_SWAP_32,
        duration_bars=4,
        duration_seconds=4.0,
        swap_beat=8,
        swap_time_offset=2.0
    )

    n_samples = int(4.0 * sr)
    audio_out = np.ones((n_samples, 2), dtype=np.float32)
    audio_in = np.full((n_samples, 2), 2.0, dtype=np.float32)

    blended = engine.execute_transition(audio_out, audio_in, plan=plan, bpm=120.0)
    assert blended.shape == (n_samples, 2)
    assert not np.isnan(blended).any()
    assert not np.isinf(blended).any()
