from pathlib import Path
import xml.etree.ElementTree as ET

from export.musicxml_exporter import MusicXMLExporter
from models.detected_note import DetectedNote
from models.score_metadata import ScoreMetadata


def export_musicxml(tmp_path, score_metadata=None):
    output_path = tmp_path / "score.musicxml"
    notes = [
        DetectedNote("F4", 0.0, 1.0),
        DetectedNote("Bb4", 0.0, 1.0),
        DetectedNote("Rest", 1.0, 1.0),
    ]

    MusicXMLExporter().export(
        notes,
        str(output_path),
        bpm=60,
        time_signature="4/4",
        use_tempo_quantization=True,
        tonality="F major",
        score_metadata=score_metadata,
    )

    return Path(output_path).read_text(encoding="utf-8")


def test_default_title_is_exported(tmp_path):
    xml = export_musicxml(tmp_path)
    root = ET.fromstring(xml)

    assert root.findtext("movement-title") == "Untitled"
    assert "font-size=\"26\"" in xml
    assert "<credit-words" in xml
    assert "Untitled" in xml


def test_score_metadata_fields_are_exported(tmp_path):
    xml = export_musicxml(
        tmp_path,
        ScoreMetadata(
            title="Nocturne",
            subtitle="For Piano",
            composer="A. Composer",
            arranger="B. Arranger",
            copyright="Copyright 2026",
        ),
    )

    root = ET.fromstring(xml)

    assert root.findtext("movement-title") == "Nocturne"
    assert root.find("./identification/creator[@type='composer']").text == "A. Composer"
    assert root.find("./identification/creator[@type='arranger']").text == "B. Arranger"
    assert root.find("./identification/rights").text == "Copyright 2026"
    assert "For Piano" in xml
    assert "default-x=\"597\"" in xml
    assert "default-x=\"1124\"" in xml
    assert "Composer: A. Composer" in xml
    assert "Composer: A. Composer&#10;Arranger: B. Arranger" in xml
    assert "&#10;&#10;For Piano" in xml
    assert "font-size=\"26\"" in xml
    assert "font-size=\"11\"" in xml
    assert "justify=\"center\"" in xml
    assert "justify=\"right\"" in xml
    assert "valign=\"bottom\"" in xml
    assert "<top-system-distance>240</top-system-distance>" in xml


def test_optional_score_metadata_fields_can_be_empty(tmp_path):
    xml = export_musicxml(
        tmp_path,
        ScoreMetadata(title="Sketch"),
    )

    assert "<movement-title>Sketch</movement-title>" in xml
    assert "<creator" not in xml
    assert "<rights>" not in xml


def test_score_metadata_is_xml_escaped(tmp_path):
    xml = export_musicxml(
        tmp_path,
        ScoreMetadata(
            title="A & B",
            composer="Composer <Author>",
        ),
    )

    assert "A &amp; B" in xml
    assert "Composer &lt;Author&gt;" in xml


def test_metadata_export_preserves_music_settings_and_chords(tmp_path):
    xml = export_musicxml(
        tmp_path,
        ScoreMetadata(title="Chord Test", composer="NavaTune"),
    )
    root = ET.fromstring(xml)
    notes = root.findall(".//note")
    pitched = [note for note in notes if note.find("pitch") is not None]
    rests = [note for note in notes if note.find("rest") is not None]
    chord_markers = [note for note in notes if note.find("chord") is not None]

    assert "<fifths>-1</fifths>" in xml
    assert "<beats>4</beats>" in xml
    assert "<beat-type>4</beat-type>" in xml
    assert "<per-minute>60</per-minute>" in xml
    assert len(pitched) == 2
    assert len(chord_markers) == 1
    assert rests[0].findtext("duration") == "8"
