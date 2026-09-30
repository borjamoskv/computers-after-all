"""
Computers After All: Autonomous DJ System & Reactive YouTube Video Synthesizer.
"""

from .analyzer import AudioAnalyzer
from .curator import SetlistCurator, camelot_distance
from .downloader import TrackDownloader
from .dsp import LinkwitzRiley4Crossover, apply_zero_overlap_bass_swap, master_ebu_r128_limiter
from .engine import AutonomousDJ
from .models import CuePoint, MixPlan, MixResult, Track, TransitionPlan, TransitionType, VideoConfig
from .rekordbox import ClubExporter
from .transitions import TransitionEngine
from .visualizer import VideoSynthesizer
from .youtube import YouTubeMetadataGenerator

__version__ = "1.0.0"
__all__ = [
    "AutonomousDJ",
    "AudioAnalyzer",
    "SetlistCurator",
    "TransitionEngine",
    "VideoSynthesizer",
    "YouTubeMetadataGenerator",
    "ClubExporter",
    "TrackDownloader",
    "LinkwitzRiley4Crossover",
    "apply_zero_overlap_bass_swap",
    "master_ebu_r128_limiter",
    "camelot_distance",
    "Track",
    "MixPlan",
    "MixResult",
    "TransitionPlan",
    "TransitionType",
    "VideoConfig",
    "CuePoint",
]
