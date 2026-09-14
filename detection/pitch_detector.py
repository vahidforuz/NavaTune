import math

from models.detected_note import DetectedNote


class PitchDetector:
    HOP_LENGTH = 512
    FRAME_LENGTH = 2048
    MIN_STABLE_FRAMES = 3
    MIN_DURATION = 0.05
    MIN_GLOBAL_MAGNITUDE_RATIO = 0.08
    MIN_RMS_RATIO = 0.03

    def detect_notes(self, file_path: str) -> list[str]:
        return [note.name for note in self.detect_notes_with_time(file_path)]

    def detect_notes_with_time(self, file_path: str) -> list[DetectedNote]:
        import librosa

        audio, sample_rate = librosa.load(file_path, sr=None, mono=True)

        if audio.size == 0:
            return []

        pitches, magnitudes = librosa.piptrack(
            y=audio,
            sr=sample_rate,
            hop_length=self.HOP_LENGTH,
        )

        rms = librosa.feature.rms(
            y=audio,
            frame_length=self.FRAME_LENGTH,
            hop_length=self.HOP_LENGTH,
        )[0]

        frame_observations = []
        magnitude_threshold = self.magnitude_threshold(magnitudes)
        rms_threshold = self.rms_threshold(rms)

        for frame_index in range(pitches.shape[1]):
            magnitude_column = magnitudes[:, frame_index]
            pitch_column = pitches[:, frame_index]
            frame_rms = rms[min(frame_index, len(rms) - 1)] if len(rms) else 0.0

            max_index = magnitude_column.argmax()
            frequency = pitch_column[max_index]
            magnitude = magnitude_column[max_index]

            time = librosa.frames_to_time(
                frame_index,
                sr=sample_rate,
                hop_length=self.HOP_LENGTH,
            )

            if (
                frequency > 0
                and magnitude >= magnitude_threshold
                and frame_rms >= rms_threshold
            ):
                note_name = librosa.hz_to_note(frequency, unicode=False)
                frame_observations.append(
                    {
                        "name": note_name,
                        "time": float(time),
                        "frequency": float(frequency),
                        "magnitude": float(magnitude),
                    }
                )

        frame_duration = librosa.frames_to_time(
            1,
            sr=sample_rate,
            hop_length=self.HOP_LENGTH,
        )

        return self.collapse_stable_frames(
            frame_observations,
            float(frame_duration),
            global_peak=float(magnitudes.max()) if magnitudes.size else 0.0,
        )

    def magnitude_threshold(self, magnitudes):
        nonzero_magnitudes = [
            float(magnitude)
            for magnitude in magnitudes.ravel()
            if magnitude > 0
        ]

        if not nonzero_magnitudes:
            return float("inf")

        global_peak = max(nonzero_magnitudes)
        noise_floor = self.percentile(nonzero_magnitudes, 65)
        return max(global_peak * self.MIN_GLOBAL_MAGNITUDE_RATIO, noise_floor)

    def rms_threshold(self, rms):
        nonzero_rms = [float(rms_value) for rms_value in rms if rms_value > 0]

        if not nonzero_rms:
            return float("inf")

        peak = max(nonzero_rms)
        median = self.percentile(nonzero_rms, 50)
        return max(peak * self.MIN_RMS_RATIO, median * 0.50)

    def percentile(self, values, percentile):
        sorted_values = sorted(values)

        if not sorted_values:
            return 0.0

        index = (len(sorted_values) - 1) * percentile / 100.0
        lower_index = int(math.floor(index))
        upper_index = int(math.ceil(index))

        if lower_index == upper_index:
            return sorted_values[lower_index]

        lower_weight = upper_index - index
        upper_weight = index - lower_index
        return (
            sorted_values[lower_index] * lower_weight
            + sorted_values[upper_index] * upper_weight
        )

    def collapse_stable_frames(
        self,
        frame_observations,
        frame_duration,
        global_peak=0.0,
    ):
        detected_notes = []
        current = None
        pending = None

        for observation in frame_observations:
            if current is None:
                pending = self.update_pending(pending, observation)

                if pending["count"] >= self.MIN_STABLE_FRAMES:
                    current = self.start_segment(pending)
                    pending = None

                continue

            if observation["name"] == current["name"]:
                current["last_time"] = observation["time"]
                current["frequencies"].append(observation["frequency"])
                current["magnitudes"].append(observation["magnitude"])
                pending = None
                continue

            pending = self.update_pending(pending, observation)

            if pending["count"] >= self.MIN_STABLE_FRAMES:
                self.append_segment(
                    detected_notes,
                    current,
                    frame_duration,
                    global_peak,
                )
                current = self.start_segment(pending)
                pending = None

        if current is not None:
            self.append_segment(
                detected_notes,
                current,
                frame_duration,
                global_peak,
            )

        return detected_notes

    def update_pending(self, pending, observation):
        if pending is None or pending["name"] != observation["name"]:
            return {
                "name": observation["name"],
                "start_time": observation["time"],
                "last_time": observation["time"],
                "frequencies": [observation["frequency"]],
                "magnitudes": [observation["magnitude"]],
                "count": 1,
            }

        pending["last_time"] = observation["time"]
        pending["frequencies"].append(observation["frequency"])
        pending["magnitudes"].append(observation["magnitude"])
        pending["count"] += 1
        return pending

    def start_segment(self, pending):
        return {
            "name": pending["name"],
            "start_time": pending["start_time"],
            "last_time": pending["last_time"],
            "frequencies": list(pending["frequencies"]),
            "magnitudes": list(pending["magnitudes"]),
        }

    def append_segment(self, detected_notes, segment, frame_duration, global_peak):
        duration = segment["last_time"] + frame_duration - segment["start_time"]

        if duration < self.MIN_DURATION:
            return

        note = DetectedNote(
            name=segment["name"],
            start_time=segment["start_time"],
            duration=duration,
        )

        if global_peak > 0 and segment["magnitudes"]:
            average_magnitude = (
                sum(segment["magnitudes"]) / len(segment["magnitudes"])
            )
            note.confidence = min(1.0, average_magnitude / global_peak)

        if segment["frequencies"]:
            note.pitch_instability_cents = self.pitch_instability_cents(
                segment["frequencies"]
            )

        detected_notes.append(note)

    def pitch_instability_cents(self, frequencies):
        frequency_values = [
            float(frequency)
            for frequency in frequencies
            if frequency > 0
        ]

        if not frequency_values:
            return 0.0

        cent_deviations = []

        for frequency in frequency_values:
            midi_value = 69.0 + 12.0 * math.log2(frequency / 440.0)
            cent_deviations.append((midi_value - round(midi_value)) * 100.0)

        average_deviation = sum(cent_deviations) / len(cent_deviations)
        variance = sum(
            (deviation - average_deviation) ** 2
            for deviation in cent_deviations
        ) / len(cent_deviations)
        return math.sqrt(variance)
