import librosa

from models.detected_note import DetectedNote


class PitchDetector:
    def detect_notes(self, file_path: str) -> list[str]:
        audio, sample_rate = librosa.load(file_path, sr=None, mono=True)

        pitches, magnitudes = librosa.piptrack(
            y=audio,
            sr=sample_rate
        )

        detected_notes = []

        for frame_index in range(pitches.shape[1]):
            magnitude_column = magnitudes[:, frame_index]
            pitch_column = pitches[:, frame_index]

            max_index = magnitude_column.argmax()
            frequency = pitch_column[max_index]

            if frequency > 0:
                note = librosa.hz_to_note(frequency)
                if not detected_notes or detected_notes[-1] != note:
                    detected_notes.append(note)

        return detected_notes

    def detect_notes_with_time(self, file_path: str) -> list[DetectedNote]:
        audio, sample_rate = librosa.load(file_path, sr=None, mono=True)

        pitches, magnitudes = librosa.piptrack(
            y=audio,
            sr=sample_rate
        )

        frame_notes = []

        for frame_index in range(pitches.shape[1]):
            magnitude_column = magnitudes[:, frame_index]
            pitch_column = pitches[:, frame_index]

            max_index = magnitude_column.argmax()
            frequency = pitch_column[max_index]

            time = librosa.frames_to_time(
                frame_index,
                sr=sample_rate
            )

            if frequency > 0:
                note_name = librosa.hz_to_note(frequency)
                frame_notes.append((note_name, time))

        detected_notes = []

        if not frame_notes:
            return detected_notes

        current_note = frame_notes[0][0]
        start_time = frame_notes[0][1]
        previous_time = frame_notes[0][1]

        for note_name, time in frame_notes[1:]:
            if note_name == current_note:
                previous_time = time
            else:
                duration = previous_time - start_time

                detected_notes.append(
                    DetectedNote(
                        name=current_note,
                        start_time=start_time,
                        duration=duration
                    )
                )

                current_note = note_name
                start_time = time
                previous_time = time

        duration = previous_time - start_time

        detected_notes.append(
            DetectedNote(
                name=current_note,
                start_time=start_time,
                duration=duration
            )
        )

        return detected_notes
