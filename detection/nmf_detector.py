import numpy as np
import librosa

from models.detected_note import DetectedNote


class NMFDetector:
    MIDI_MIN = 21
    MIDI_MAX = 108
    BINS_PER_OCTAVE = 12
    HOP_LENGTH = 512
    MIN_DURATION = 0.08
    MERGE_GAP = 0.20
    ACTIVATION_PERCENTILE = 70
    MIN_GLOBAL_PEAK_RATIO = 0.30
    MAX_SIMULTANEOUS_NOTES = 8

    def detect_notes_with_time(self, file_path: str) -> list[DetectedNote]:
        audio, sample_rate = librosa.load(file_path, sr=22050, mono=True)

        if audio.size == 0:
            return []

        cqt = np.abs(
            librosa.cqt(
                y=audio,
                sr=sample_rate,
                hop_length=self.HOP_LENGTH,
                fmin=librosa.midi_to_hz(self.MIDI_MIN),
                n_bins=self.n_bins,
                bins_per_octave=self.BINS_PER_OCTAVE,
            )
        )

        if cqt.size == 0 or not np.any(cqt):
            return []

        spectrum = librosa.util.normalize(cqt, axis=0)
        templates = self.build_harmonic_templates()
        activations = self.estimate_activations(spectrum, templates)

        return self.activations_to_notes(activations, sample_rate)

    @property
    def n_bins(self) -> int:
        return self.MIDI_MAX - self.MIDI_MIN + 1

    def build_harmonic_templates(self) -> np.ndarray:
        templates = np.zeros((self.n_bins, self.n_bins), dtype=float)

        max_frequency = librosa.midi_to_hz(self.MIDI_MAX)

        for note_index, midi_note in enumerate(range(self.MIDI_MIN, self.MIDI_MAX + 1)):
            fundamental = librosa.midi_to_hz(midi_note)

            for harmonic in range(1, 9):
                harmonic_frequency = fundamental * harmonic

                if harmonic_frequency > max_frequency:
                    break

                harmonic_midi = librosa.hz_to_midi(harmonic_frequency)
                bin_index = int(round(harmonic_midi)) - self.MIDI_MIN

                if 0 <= bin_index < self.n_bins:
                    templates[bin_index, note_index] += 1.0 / harmonic

        column_sums = templates.sum(axis=0, keepdims=True)
        column_sums[column_sums == 0] = 1.0
        return templates / column_sums

    def estimate_activations(
        self,
        spectrum: np.ndarray,
        templates: np.ndarray,
        iterations: int = 5,
    ) -> np.ndarray:
        activations = templates.T @ spectrum + 1e-6

        for _ in range(iterations):
            reconstruction = templates @ activations + 1e-9
            activations *= (templates.T @ (spectrum / reconstruction)) / (
                templates.sum(axis=0, keepdims=True).T + 1e-9
            )

        return activations

    def activations_to_notes(
        self,
        activations: np.ndarray,
        sample_rate: int,
    ) -> list[DetectedNote]:
        if activations.size == 0:
            return []

        activations = self.smooth_activations(activations)
        activations = self.suppress_neighbor_duplicates(activations)
        activations = self.suppress_octave_duplicates(activations)
        activations = self.keep_strongest_notes_per_frame(activations)

        notes = []
        global_peak = float(np.max(activations))
        frame_duration = librosa.frames_to_time(
            1,
            sr=sample_rate,
            hop_length=self.HOP_LENGTH,
        )

        for note_index, activation in enumerate(activations):
            if (
                global_peak <= 0
                or np.max(activation) < global_peak * self.MIN_GLOBAL_PEAK_RATIO
            ):
                continue

            threshold = self.note_threshold(activation)

            if threshold <= 0:
                continue

            active_frames = activation >= threshold
            regions = self.merge_regions(
                self.boolean_regions(active_frames),
                frame_duration,
            )

            for start_frame, end_frame in regions:
                start_time = librosa.frames_to_time(
                    start_frame,
                    sr=sample_rate,
                    hop_length=self.HOP_LENGTH,
                )
                end_time = librosa.frames_to_time(
                    end_frame + 1,
                    sr=sample_rate,
                    hop_length=self.HOP_LENGTH,
                )
                duration = max(float(end_time - start_time), frame_duration)

                if duration < self.MIN_DURATION:
                    continue

                midi_note = self.MIDI_MIN + note_index
                notes.append(
                    DetectedNote(
                        name=librosa.midi_to_note(midi_note, unicode=False),
                        start_time=float(start_time),
                        duration=duration,
                    )
                )

        notes.sort(key=lambda note: (note.start_time, note.name))
        return notes

    def note_threshold(self, activation: np.ndarray) -> float:
        peak = float(np.max(activation))

        if peak <= 0:
            return 0.0

        percentile_threshold = float(
            np.percentile(activation, self.ACTIVATION_PERCENTILE)
        )
        return max(peak * 0.25, percentile_threshold)

    def smooth_activations(self, activations: np.ndarray) -> np.ndarray:
        window = np.ones(5, dtype=float) / 5.0
        return np.apply_along_axis(
            lambda activation: np.convolve(activation, window, mode="same"),
            axis=1,
            arr=activations,
        )

    def suppress_neighbor_duplicates(self, activations: np.ndarray) -> np.ndarray:
        filtered = activations.copy()

        for note_index in range(filtered.shape[0]):
            low = max(0, note_index - 1)
            high = min(filtered.shape[0], note_index + 2)
            local_max = np.max(activations[low:high], axis=0)
            filtered[note_index, activations[note_index] < local_max * 0.98] = 0.0

        return filtered

    def boolean_regions(self, active_frames: np.ndarray) -> list[tuple[int, int]]:
        regions = []
        start_frame = None

        for frame_index, is_active in enumerate(active_frames):
            if is_active and start_frame is None:
                start_frame = frame_index
            elif not is_active and start_frame is not None:
                regions.append((start_frame, frame_index - 1))
                start_frame = None

        if start_frame is not None:
            regions.append((start_frame, len(active_frames) - 1))

        return regions

    def merge_regions(
        self,
        regions: list[tuple[int, int]],
        frame_duration: float,
    ) -> list[tuple[int, int]]:
        if not regions:
            return []

        max_gap_frames = max(1, int(round(self.MERGE_GAP / frame_duration)))
        merged = [regions[0]]

        for start_frame, end_frame in regions[1:]:
            previous_start, previous_end = merged[-1]

            if start_frame - previous_end <= max_gap_frames:
                merged[-1] = (previous_start, end_frame)
            else:
                merged.append((start_frame, end_frame))

        return merged

    def suppress_octave_duplicates(self, activations: np.ndarray) -> np.ndarray:
        filtered = activations.copy()

        for pitch_class in range(self.BINS_PER_OCTAVE):
            note_indices = list(
                range(pitch_class, filtered.shape[0], self.BINS_PER_OCTAVE)
            )

            if len(note_indices) < 2:
                continue

            pitch_class_activations = filtered[note_indices]
            strongest_indices = np.argmax(pitch_class_activations, axis=0)

            for position, note_index in enumerate(note_indices):
                filtered[note_index, strongest_indices != position] = 0.0

        return filtered

    def keep_strongest_notes_per_frame(self, activations: np.ndarray) -> np.ndarray:
        filtered = activations.copy()

        if filtered.shape[0] <= self.MAX_SIMULTANEOUS_NOTES:
            return filtered

        for frame_index in range(filtered.shape[1]):
            frame = filtered[:, frame_index]
            active_count = np.count_nonzero(frame)

            if active_count <= self.MAX_SIMULTANEOUS_NOTES:
                continue

            keep_indices = np.argpartition(
                frame,
                -self.MAX_SIMULTANEOUS_NOTES,
            )[-self.MAX_SIMULTANEOUS_NOTES:]
            mask = np.ones(frame.shape, dtype=bool)
            mask[keep_indices] = False
            filtered[mask, frame_index] = 0.0

        return filtered
