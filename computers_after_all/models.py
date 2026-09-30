"""
Core data models and contracts for Computers After All.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TransitionType(str, Enum):
    HARD_DROP = "hard_drop"                     # 1 compás (4 beats)
    BASS_SWAP_32 = "bass_swap_32"               # 32 compases (128 beats) - Standard club
    WALL_OF_SOUND_64 = "wall_of_sound_64"       # 64 compases (256 beats) - Deep blend
    DUB_ECHO_FREEZE = "dub_echo_freeze"         # 16 compases + 8 dub tail
    POLYRHYTHMIC = "polyrhythmic"               # 32 compases métrica desfasada
    TEMPO_RAMP = "tempo_ramp"                   # 32-64 compases rampa de tempo
    PERCUSSION_SWAP = "percussion_swap"         # 16 compases relevo de agudos
    CAMELOT_MODULATION = "camelot_modulation"   # 32 compases modulación con filtro notch


@dataclass
class CuePoint:
    name: str
    time_seconds: float
    num: int = 0
    cue_type: int = 0  # 0 = Standard Cue


@dataclass
class Track:
    path: Path
    title: str
    artist: str
    duration_seconds: float
    bpm: float
    camelot_key: str                            # e.g., "11A"
    musical_key: str = ""                       # e.g., "F#m"
    sample_rate: int = 44100
    channels: int = 2
    energy: float = 0.5                         # [0.0, 1.0]
    beatgrid_offset: float = 0.0                # downbeat start time in seconds
    cues: List[CuePoint] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.path.stem


@dataclass
class TransitionPlan:
    from_index: int
    to_index: int
    transition_type: TransitionType
    duration_bars: int
    duration_seconds: float
    swap_beat: int                              # Beat where bass cuts/opens (e.g. 64)
    swap_time_offset: float                     # Seconds from transition start to bass swap
    dip_db: float = -1.2                        # Psychoacoustic anti-masking mid dip
    dub_tail_enabled: bool = False
    dub_feedback: float = 0.42
    dub_delay_factor: float = 0.75              # 3/16 dotted-eighth note


@dataclass
class MixSegment:
    track: Track
    start_time: float                           # In final mix timeline (seconds)
    end_time: float                             # In final mix timeline (seconds)
    audio_start_offset: float                   # In track source file (seconds)
    audio_end_offset: float                     # In track source file (seconds)


@dataclass
class MixPlan:
    tracks: List[Track]
    transitions: List[TransitionPlan]
    segments: List[MixSegment]
    total_duration_seconds: float
    master_bpm: float
    act_name: str = "El Circuito Disruptor"


@dataclass
class VideoConfig:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    theme: str = "cyber_noir"                   # "cyber_noir", "industrial_terminal", "acid_minimal"
    show_spectrum: bool = True
    show_hud: bool = True
    show_waveform: bool = True
    show_progress: bool = True
    hardware_accel: bool = True                 # macOS videotoolbox


@dataclass
class MixResult:
    audio_path: Path
    wav_path: Optional[Path] = None
    video_path: Optional[Path] = None
    rekordbox_xml_path: Optional[Path] = None
    cue_path: Optional[Path] = None
    m3u8_path: Optional[Path] = None
    youtube_metadata_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    plan: Optional[MixPlan] = None
