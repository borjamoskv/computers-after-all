"""
Club Exporters: Pioneer Rekordbox XML (DJ_PLAYLISTS 1.0.0), CUE Sheet, and M3U8.
"""

from pathlib import Path
import urllib.parse
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List

from .models import MixPlan
from .youtube import format_timestamp


class ClubExporter:
    """Generates Pioneer Rekordbox XML, CUE sheets, and M3U8 playlists."""

    def export_rekordbox_xml(
        self,
        plan: MixPlan,
        output_path: Path,
        playlist_name: str = "COMPUTERS AFTER ALL"
    ) -> Path:
        """Serializes collection into official Pioneer Rekordbox XML specification."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        ET.SubElement(root, "PRODUCT", Name="rekordbox", Version="6.0.0", Company="Pioneer DJ")

        # Collection node
        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(plan.tracks)))

        for i, t in enumerate(plan.tracks):
            track_id = str(i + 1)
            file_uri = f"file://localhost{urllib.parse.quote(str(t.path.resolve()))}"

            track_elem = ET.SubElement(
                collection,
                "TRACK",
                TrackID=track_id,
                Name=t.title or t.path.stem,
                Artist=t.artist or "Unknown",
                TotalTime=str(int(t.duration_seconds)),
                AverageBpm=f"{t.bpm:.2f}",
                Tonality=t.camelot_key or "8A",
                BitRate="320",
                SampleRate=str(t.sample_rate),
                Location=file_uri
            )

            # Cues
            for c in t.cues:
                ET.SubElement(
                    track_elem,
                    "POSITION_MARK",
                    Name=c.name,
                    Type=str(c.cue_type),
                    Start=f"{c.time_seconds:.3f}",
                    Num=str(c.num)
                )

        # Playlists node
        playlists = ET.SubElement(root, "PLAYLISTS")
        root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT")
        setlist_node = ET.SubElement(
            root_node,
            "NODE",
            Type="1",
            Name=playlist_name,
            KeyType="0",
            Entries=str(len(plan.tracks))
        )

        for i in range(len(plan.tracks)):
            ET.SubElement(setlist_node, "TRACK", Key=str(i + 1))

        # Pretty print XML
        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(raw_xml)
        pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8")

        out.write_bytes(pretty_xml)
        return out

    def export_cue_sheet(
        self,
        plan: MixPlan,
        output_path: Path,
        audio_filename: str = "COMPUTERS_AFTER_ALL_MIX.mp3"
    ) -> Path:
        """Generates standard CUE sheet for CD burning or mix indexing."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        lines: List[str] = [
            f'FILE "{audio_filename}" MP3'
        ]

        for i, seg in enumerate(plan.segments):
            t = seg.track
            track_num = f"{i+1:02d}"
            lines.append(f"  TRACK {track_num} AUDIO")
            lines.append(f'    TITLE "{t.title or t.path.stem}"')
            lines.append(f'    PERFORMER "{t.artist or "Unknown"}"')

            # CUE format: MM:SS:FF (where FF is frames 0-74, 75 fps)
            sec = seg.start_time
            m = int(sec // 60)
            s = int(sec % 60)
            f = int((sec - int(sec)) * 75)
            lines.append(f"    INDEX 01 {m:02d}:{s:02d}:{f:02d}")

        out.write_text("\n".join(lines), encoding="utf-8")
        return out

    def export_m3u8(self, plan: MixPlan, output_path: Path) -> Path:
        """Generates extended M3U8 playlist with track metadata."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = ["#EXTM3U"]
        for t in plan.tracks:
            dur = int(t.duration_seconds)
            name = f"{t.artist} - {t.title}" if t.artist else t.path.stem
            lines.append(f"#EXTINF:{dur},{name}")
            lines.append(str(t.path.resolve()))

        out.write_text("\n".join(lines), encoding="utf-8")
        return out
