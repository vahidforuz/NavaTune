import os
import tempfile
import subprocess
import pretty_midi

from models.detected_note import DetectedNote


class BasicPitchDetector:
    def detect_notes_with_time(self, file_path: str) -> list[DetectedNote]:
        output_dir = tempfile.mkdtemp(prefix="navatune_basic_pitch_")

        subprocess.run(
            ["basic-pitch", output_dir, file_path],
            check=True
        )

        midi_files = [
            f for f in os.listdir(output_dir)
            if f.endswith(".mid") or f.endswith(".midi")
        ]

        if not midi_files:
            return []

        midi_path = os.path.join(output_dir, midi_files[0])
        midi_data = pretty_midi.PrettyMIDI(midi_path)

        notes = []

        for instrument in midi_data.instruments:
            for midi_note in instrument.notes:
                name = pretty_midi.note_number_to_name(midi_note.pitch)

                notes.append(
                    DetectedNote(
                        name=name,
                        start_time=float(midi_note.start),
                        duration=float(midi_note.end - midi_note.start)
                    )
                )

        notes.sort(key=lambda n: n.start_time)
        return notes
