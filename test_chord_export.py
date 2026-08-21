from models.detected_chord import DetectedChord
from export.musicxml_exporter import MusicXMLExporter


if __name__ == "__main__":
    chord = DetectedChord(
        names=["C4", "E4", "G4"],
        start_time=0.0,
        duration=1.0
    )

    exporter = MusicXMLExporter()
    exporter.export([chord], "test_audio/c_major_chord.musicxml")

    print("Created: test_audio/c_major_chord.musicxml")
