from models.detected_note import DetectedNote
from detection.detector_errors import DetectorBackendError
from detection.pitch_detector import PitchDetector


class LivePitchDetector(PitchDetector):
    HOP_LENGTH = 512
    FRAME_LENGTH = 2048
    MIN_VOICED_PROBABILITY = 0.60

    def detect_notes_with_time(self, file_path: str) -> list[DetectedNote]:
        try:
            import librosa
            import numpy as np
        except ImportError as error:
            raise DetectorBackendError(
                "The live tuner detector needs librosa with pyin support. "
                "Install project requirements, then try again."
            ) from error

        audio, sample_rate = librosa.load(file_path, sr=None, mono=True)

        if audio.size == 0:
            return []

        f0, voiced_flag, voiced_probabilities = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sample_rate,
            frame_length=self.FRAME_LENGTH,
            hop_length=self.HOP_LENGTH,
        )

        frame_observations = []

        for frame_index, frequency in enumerate(f0):
            if not voiced_flag[frame_index] or not np.isfinite(frequency):
                continue

            confidence = float(voiced_probabilities[frame_index])
            if confidence < self.MIN_VOICED_PROBABILITY:
                continue

            time = librosa.frames_to_time(
                frame_index,
                sr=sample_rate,
                hop_length=self.HOP_LENGTH,
            )

            frame_observations.append(
                {
                    "name": librosa.hz_to_note(float(frequency), unicode=False),
                    "time": float(time),
                    "frequency": float(frequency),
                    "magnitude": confidence,
                }
            )

        frame_duration = librosa.frames_to_time(
            1,
            sr=sample_rate,
            hop_length=self.HOP_LENGTH,
        )
        notes = self.collapse_stable_frames(
            frame_observations,
            float(frame_duration),
            global_peak=1.0,
        )

        return notes[:1]
