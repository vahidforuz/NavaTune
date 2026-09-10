from pathlib import Path

from export.musicxml_exporter import MusicXMLExporter
from models.detected_note import DetectedNote


def export_musicxml(tmp_path, tonality):
    output_path = tmp_path / "score.musicxml"
    MusicXMLExporter().export(
        [DetectedNote("C4", 0.0, 1.0)],
        str(output_path),
        bpm=60,
        time_signature="4/4",
        use_tempo_quantization=True,
        tonality=tonality,
    )
    return Path(output_path).read_text(encoding="utf-8")


def assert_fifths(xml, fifths):
    assert f"<fifths>{fifths}</fifths>" in xml


def test_musicxml_major_key_signatures(tmp_path):
    expected = {
        "C major": 0,
        "G major": 1,
        "D major": 2,
        "F major": -1,
        "Bb major": -2,
        "Eb major": -3,
        "Ab major": -4,
    }

    for key, fifths in expected.items():
        assert_fifths(export_musicxml(tmp_path, key), fifths)


def test_musicxml_minor_key_signatures(tmp_path):
    expected = {
        "A minor": 0,
        "E minor": 1,
        "B minor": 2,
        "F# minor": 3,
        "D minor": -1,
        "G minor": -2,
        "C minor": -3,
    }

    for key, fifths in expected.items():
        assert_fifths(export_musicxml(tmp_path, key), fifths)


def test_musicxml_automatic_unknown_has_no_accidentals(tmp_path):
    assert_fifths(export_musicxml(tmp_path, "Automatic / Unknown"), 0)
