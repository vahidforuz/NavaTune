import xml.etree.ElementTree as ET

from models.detected_note import DetectedNote


class MusicXMLImporter:
    DEFAULT_DIVISIONS = 8
    DEFAULT_BPM = 60

    def import_file(self, input_path: str, bpm: int = DEFAULT_BPM):
        tree = ET.parse(input_path)
        return self.import_root(tree.getroot(), bpm=bpm)

    def import_root(self, root, bpm: int = DEFAULT_BPM):
        quarter_note_seconds = 60.0 / max(1, int(bpm))
        divisions = self.DEFAULT_DIVISIONS
        current_time = 0.0
        previous_note_start = 0.0
        notes = []

        for element in root.iter():
            if self.local_name(element.tag) == "attributes":
                divisions = self.read_divisions(element, divisions)
                continue

            if self.local_name(element.tag) != "note":
                continue

            duration_units = self.read_duration_units(element)
            duration_seconds = duration_units / divisions * quarter_note_seconds
            is_chord_tone = self.find_child(element, "chord") is not None
            start_time = previous_note_start if is_chord_tone else current_time

            rest = self.find_child(element, "rest")
            pitch = self.find_child(element, "pitch")

            if rest is not None:
                notes.append(
                    DetectedNote(
                        name="Rest",
                        start_time=start_time,
                        duration=duration_seconds,
                        staff="auto",
                    )
                )
            elif pitch is not None:
                notes.append(
                    DetectedNote(
                        name=self.read_pitch_name(pitch),
                        start_time=start_time,
                        duration=duration_seconds,
                        staff=self.read_staff(element),
                    )
                )

            if not is_chord_tone:
                previous_note_start = start_time
                current_time += duration_seconds

        return notes

    def read_divisions(self, attributes, current_divisions):
        divisions = self.find_child(attributes, "divisions")

        if divisions is None or not divisions.text:
            return current_divisions

        try:
            return max(1, int(divisions.text.strip()))
        except ValueError:
            return current_divisions

    def read_duration_units(self, note):
        duration = self.find_child(note, "duration")

        if duration is None or not duration.text:
            return self.DEFAULT_DIVISIONS

        try:
            return max(0, int(duration.text.strip()))
        except ValueError:
            return self.DEFAULT_DIVISIONS

    def read_pitch_name(self, pitch):
        step = self.child_text(pitch, "step", "C").upper()
        alter = self.child_text(pitch, "alter", "0")
        octave = self.child_text(pitch, "octave", "4")
        accidental = ""

        if alter == "1":
            accidental = "#"
        elif alter == "-1":
            accidental = "b"

        return f"{step}{accidental}{octave}"

    def read_staff(self, note):
        staff = self.child_text(note, "staff", "")

        if staff == "1":
            return "treble"

        if staff == "2":
            return "bass"

        return "auto"

    def child_text(self, element, child_name, default):
        child = self.find_child(element, child_name)

        if child is None or child.text is None:
            return default

        return child.text.strip()

    def find_child(self, element, child_name):
        for child in element:
            if self.local_name(child.tag) == child_name:
                return child

        return None

    def local_name(self, tag):
        return tag.rsplit("}", 1)[-1]
