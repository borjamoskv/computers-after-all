"""
Unit tests for Pioneer Rekordbox XML, CUE sheet, and M3U8 exports.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
from computers_after_all.models import CuePoint, MixPlan, MixSegment, Track, TransitionPlan, TransitionType
from computers_after_all.rekordbox import ClubExporter


def test_rekordbox_xml_structure(tmp_path):
    exporter = ClubExporter()
    tracks = [
        Track(
            path=tmp_path / "track1.mp3",
            title="Berlin Dub",
            artist="Shed",
            duration_seconds=360,
            bpm=128.0,
            camelot_key="11A",
            cues=[CuePoint(name="Intro", time_seconds=0.0)]
        ),
        Track(
            path=tmp_path / "track2.mp3",
            title="Enoha",
            artist="Kassem Mosse",
            duration_seconds=400,
            bpm=126.0,
            camelot_key="11B"
        )
    ]
    plan = MixPlan(
        tracks=tracks,
        transitions=[],
        segments=[
            MixSegment(track=tracks[0], start_time=0.0, end_time=360.0, audio_start_offset=0, audio_end_offset=360),
            MixSegment(track=tracks[1], start_time=330.0, end_time=730.0, audio_start_offset=0, audio_end_offset=400)
        ],
        total_duration_seconds=730.0,
        master_bpm=127.0
    )

    xml_path = tmp_path / "output_rekordbox.xml"
    exporter.export_rekordbox_xml(plan, xml_path, playlist_name="Test Set")

    assert xml_path.exists()
    root = ET.parse(str(xml_path)).getroot()
    assert root.tag == "DJ_PLAYLISTS"
    assert root.attrib["Version"] == "1.0.0"

    product = root.find("PRODUCT")
    assert product is not None
    assert product.attrib["Name"] == "rekordbox"

    collection = root.find("COLLECTION")
    assert collection is not None
    assert collection.attrib["Entries"] == "2"

    tracks_xml = collection.findall("TRACK")
    assert len(tracks_xml) == 2
    assert tracks_xml[0].attrib["Artist"] == "Shed"
    assert tracks_xml[0].attrib["Tonality"] == "11A"


def test_cue_sheet_export(tmp_path):
    exporter = ClubExporter()
    tracks = [
        Track(path=tmp_path / "t1.mp3", title="Title 1", artist="Artist 1", duration_seconds=120, bpm=128, camelot_key="8A")
    ]
    plan = MixPlan(
        tracks=tracks,
        transitions=[],
        segments=[MixSegment(track=tracks[0], start_time=0.0, end_time=120.0, audio_start_offset=0, audio_end_offset=120)],
        total_duration_seconds=120.0,
        master_bpm=128.0
    )

    cue_path = tmp_path / "test.cue"
    exporter.export_cue_sheet(plan, cue_path, audio_filename="mix.mp3")

    content = cue_path.read_text()
    assert 'FILE "mix.mp3" MP3' in content
    assert 'TITLE "Title 1"' in content
    assert 'INDEX 01 00:00:00' in content
