from pathlib import Path
import xml.etree.ElementTree as ET

from export.musicxml_exporter import MusicXMLExporter
from models.detected_chord import DetectedChord
from models.detected_note import DetectedNote
from notation.rhythm_quantizer import RhythmQuantizer
from notation.tonality import spell_notes_for_key


def notation_events(notes, onset_tolerance=0.04):
    score = RhythmQuantizer(
        bpm=60,
        time_signature="4/4",
        onset_tolerance=onset_tolerance,
    ).quantize(notes)
    return score.measures[0].events


def export_xml(tmp_path, notes, tonality="Automatic / Unknown"):
    output_path = tmp_path / "score.musicxml"
    MusicXMLExporter().export(
        notes,
        str(output_path),
        bpm=60,
        time_signature="4/4",
        use_tempo_quantization=True,
        tonality=tonality,
    )
    return Path(output_path).read_text(encoding="utf-8")


def parsed_notes(xml):
    root = ET.fromstring(xml)
    return root.findall(".//note")


def pitched_notes(xml):
    return [
        note
        for note in parsed_notes(xml)
        if note.find("pitch") is not None
    ]


def pitch_names(notes):
    names = []

    for note in notes:
        pitch = note.find("pitch")
        step = pitch.findtext("step")
        alter = pitch.findtext("alter")
        octave = pitch.findtext("octave")
        accidental = ""

        if alter == "1":
            accidental = "#"
        elif alter == "-1":
            accidental = "b"

        names.append(f"{step}{accidental}{octave}")

    return names


def assert_single_chord(notes, expected_names):
    events = notation_events(notes)

    assert isinstance(events[0].note, DetectedChord)
    assert events[0].note.names == expected_names


def assert_musicxml_chord(xml, expected_names):
    notes = pitched_notes(xml)

    assert pitch_names(notes[:len(expected_names)]) == expected_names
    assert notes[0].find("chord") is None
    assert all(
        note.find("chord") is not None
        for note in notes[1:len(expected_names)]
    )


def test_two_simultaneous_notes_become_one_chord(tmp_path):
    notes = [
        DetectedNote("F4", 0.0, 1.0),
        DetectedNote("Bb4", 0.0, 1.0),
    ]

    assert_single_chord(notes, ["F4", "Bb4"])
    assert_musicxml_chord(export_xml(tmp_path, notes), ["F4", "Bb4"])


def test_three_notes_inside_onset_tolerance_become_one_chord(tmp_path):
    notes = [
        DetectedNote("C4", 0.00, 1.0),
        DetectedNote("E4", 0.01, 1.0),
        DetectedNote("G4", 0.02, 1.0),
    ]

    assert_single_chord(notes, ["C4", "E4", "G4"])
    assert_musicxml_chord(export_xml(tmp_path, notes), ["C4", "E4", "G4"])


def test_four_simultaneous_notes_become_one_chord(tmp_path):
    notes = [
        DetectedNote("C4", 0.0, 1.0),
        DetectedNote("E4", 0.0, 1.0),
        DetectedNote("G4", 0.0, 1.0),
        DetectedNote("C5", 0.0, 1.0),
    ]

    assert_single_chord(notes, ["C4", "E4", "G4", "C5"])
    assert_musicxml_chord(export_xml(tmp_path, notes), ["C4", "E4", "G4", "C5"])


def test_five_simultaneous_notes_become_one_chord(tmp_path):
    notes = [
        DetectedNote("C4", 0.0, 1.0),
        DetectedNote("E4", 0.0, 1.0),
        DetectedNote("G4", 0.0, 1.0),
        DetectedNote("B4", 0.0, 1.0),
        DetectedNote("D5", 0.0, 1.0),
    ]

    assert_single_chord(notes, ["C4", "E4", "G4", "B4", "D5"])
    assert_musicxml_chord(
        export_xml(tmp_path, notes),
        ["C4", "E4", "G4", "B4", "D5"],
    )


def test_onset_tolerance_groups_close_starts_and_keeps_separate_groups():
    events = notation_events([
        DetectedNote("C4", 1.000, 1.0),
        DetectedNote("E4", 1.018, 1.0),
        DetectedNote("G4", 1.030, 1.0),
        DetectedNote("C5", 2.000, 1.0),
    ])

    note_events = [event for event in events if event.kind == "note"]

    assert isinstance(note_events[0].note, DetectedChord)
    assert note_events[0].note.names == ["C4", "E4", "G4"]
    assert note_events[1].note.name == "C5"


def test_rests_are_preserved_between_chords():
    events = notation_events([
        DetectedNote("F4", 0.0, 1.0),
        DetectedNote("Bb4", 0.0, 1.0),
        DetectedNote("Rest", 1.0, 1.0),
        DetectedNote("G4", 2.0, 1.0),
        DetectedNote("C5", 2.0, 1.0),
        DetectedNote("Rest", 3.0, 1.0),
    ])

    assert [
        (
            event.kind,
            getattr(event.note, "names", None),
            getattr(event.note, "name", None),
            event.duration_units,
        )
        for event in events[:4]
    ] == [
        ("note", ["F4", "Bb4"], None, 8),
        ("rest", None, None, 8),
        ("note", ["G4", "C5"], None, 8),
        ("rest", None, None, 8),
    ]


def test_tonality_spelling_is_preserved_for_chords(tmp_path):
    notes = spell_notes_for_key([
        DetectedNote("F4", 0.0, 1.0),
        DetectedNote("A#4", 0.0, 1.0),
    ], "F major")

    xml = export_xml(tmp_path, notes, tonality="F major")

    assert "<fifths>-1</fifths>" in xml
    assert_musicxml_chord(xml, ["F4", "Bb4"])


def test_monophonic_rendering_still_uses_sequential_notes(tmp_path):
    notes = [
        DetectedNote("C4", 0.0, 1.0),
        DetectedNote("D4", 1.0, 1.0),
        DetectedNote("E4", 2.0, 1.0),
    ]

    events = notation_events(notes)
    xml = export_xml(tmp_path, notes)

    assert [
        (event.kind, getattr(event.note, "name", None), event.duration_units)
        for event in events[:3]
    ] == [
        ("note", "C4", 8),
        ("note", "D4", 8),
        ("note", "E4", 8),
    ]
    assert "<chord/>" not in xml
