from pathlib import Path

from export.musicxml_exporter import MusicXMLExporter
from export.musicxml_importer import MusicXMLImporter
from models.detected_note import DetectedNote


def write_musicxml(tmp_path, content):
    path = tmp_path / "score.musicxml"
    path.write_text(content, encoding="utf-8")
    return path


def test_import_exported_chords_preserves_simultaneous_starts(tmp_path):
    exported_path = tmp_path / "exported.musicxml"
    notes = [
        DetectedNote("F4", 0.0, 1.0),
        DetectedNote("Bb4", 0.0, 1.0),
        DetectedNote("Rest", 1.0, 1.0),
        DetectedNote("G4", 2.0, 1.0),
        DetectedNote("C5", 2.0, 1.0),
        DetectedNote("Rest", 3.0, 1.0),
    ]

    MusicXMLExporter().export(
        notes,
        str(exported_path),
        bpm=60,
        time_signature="4/4",
        use_tempo_quantization=True,
        tonality="F major",
    )

    imported_notes = MusicXMLImporter().import_file(str(exported_path), bpm=60)

    assert [
        (note.name, note.start_time, note.duration)
        for note in imported_notes[:6]
    ] == [
        ("F4", 0.0, 1.0),
        ("Bb4", 0.0, 1.0),
        ("Rest", 1.0, 1.0),
        ("G4", 2.0, 1.0),
        ("C5", 2.0, 1.0),
        ("Rest", 3.0, 1.0),
    ]


def test_import_musicxml_with_namespace(tmp_path):
    input_path = write_musicxml(
        tmp_path,
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise xmlns="http://www.musicxml.org/ns/musicxml" version="4.0">
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>8</divisions>
      </attributes>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>8</duration>
        <staff>1</staff>
      </note>
      <note>
        <chord/>
        <pitch>
          <step>E</step>
          <octave>4</octave>
        </pitch>
        <duration>8</duration>
        <staff>1</staff>
      </note>
      <note>
        <rest/>
        <duration>8</duration>
      </note>
    </measure>
  </part>
</score-partwise>
""",
    )

    imported_notes = MusicXMLImporter().import_file(str(input_path), bpm=60)

    assert [
        (note.name, note.start_time, note.duration, note.staff)
        for note in imported_notes
    ] == [
        ("C4", 0.0, 1.0, "treble"),
        ("E4", 0.0, 1.0, "treble"),
        ("Rest", 1.0, 1.0, "auto"),
    ]
