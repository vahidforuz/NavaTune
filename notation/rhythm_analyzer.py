from dataclasses import dataclass
from typing import Optional

import numpy as np
import soundfile as sf

from models.detected_note import DetectedNote


UNKNOWN_NOTE_NAME = "Unknown"


@dataclass(frozen=True)
class RhythmDuration:
    name: str
    seconds: float


@dataclass(frozen=True)
class RhythmAnalysisConfig:
    quantize_tolerance_ratio: float = 0.35
    min_confidence: float = 0.65
    max_pitch_instability_cents: float = 35.0
    smoothing_window: int = 3
    short_gap_ratio_of_sixteenth: float = 0.50
    false_note_ratio_of_sixteenth: float = 0.50
    min_rest_ratio_of_sixteenth: float = 0.75


def get_quarter_duration(tempo):
    return 60.0 / max(1, int(float(tempo)))


def get_allowed_note_durations(tempo):
    quarter = get_quarter_duration(tempo)
    return [
        RhythmDuration("sixteenth", quarter / 4.0),
        RhythmDuration("eighth", quarter / 2.0),
        RhythmDuration("quarter", quarter),
        RhythmDuration("half", quarter * 2.0),
        RhythmDuration("whole", quarter * 4.0),
    ]


def quantize_duration(duration, tempo, tolerance_ratio=0.35):
    if duration <= 0:
        return None

    candidates = get_allowed_note_durations(tempo)
    nearest = min(candidates, key=lambda candidate: abs(candidate.seconds - duration))
    tolerance = nearest.seconds * tolerance_ratio

    if abs(nearest.seconds - duration) <= tolerance:
        return nearest.seconds

    return None


def is_unknown_note(note):
    if note.is_rest():
        return False

    name = note.name.strip().lower()
    return name in {"unknown", "uncertain", ""}


class RhythmAnalyzer:
    def __init__(self, bpm=60, config=None):
        self.bpm = max(1, int(float(bpm)))
        self.config = config or RhythmAnalysisConfig()

    @property
    def quarter_duration(self):
        return get_quarter_duration(self.bpm)

    @property
    def sixteenth_duration(self):
        return self.quarter_duration / 4.0

    @property
    def short_gap_threshold(self):
        return self.sixteenth_duration * self.config.short_gap_ratio_of_sixteenth

    @property
    def false_note_threshold(self):
        return self.sixteenth_duration * self.config.false_note_ratio_of_sixteenth

    @property
    def min_rest_duration(self):
        return self.sixteenth_duration * self.config.min_rest_ratio_of_sixteenth

    def analyze_audio_file(self, notes, file_path):
        audio_profile = RmsAudioProfile.from_file(file_path)
        return self.analyze(
            notes,
            total_duration=audio_profile.duration,
            silence_checker=audio_profile.is_low_energy,
        )

    def analyze(
        self,
        notes,
        total_duration: Optional[float] = None,
        silence_checker=None,
    ):
        accepted_notes = self.reject_uncertain_notes(notes)
        smoothed_notes = self.smooth_note_names(accepted_notes)
        merged_notes = self.merge_short_gaps(smoothed_notes)
        cleaned_notes = self.remove_short_pitch_glitches(merged_notes)
        quantized_notes = self.quantize_note_durations(cleaned_notes)
        return self.add_tempo_quantized_rests(
            quantized_notes,
            total_duration,
            silence_checker=silence_checker,
        )

    def reject_uncertain_notes(self, notes):
        accepted = []

        for note in sorted(notes, key=lambda item: item.start_time):
            if note.is_rest():
                accepted.append(note)
                continue

            if is_unknown_note(note):
                continue

            confidence = getattr(note, "confidence", None)
            if confidence is not None and confidence < self.config.min_confidence:
                continue

            instability = getattr(note, "pitch_instability_cents", None)
            if (
                instability is not None
                and instability > self.config.max_pitch_instability_cents
            ):
                continue

            quantized_duration = self.quantize(note.duration)
            if quantized_duration is None:
                continue

            accepted.append(self.copy_note(note, duration=quantized_duration))

        return accepted

    def smooth_note_names(self, notes):
        window = self.config.smoothing_window

        if window < 3 or window % 2 == 0 or len(notes) < window:
            return list(notes)

        smoothed = list(notes)
        radius = window // 2

        for index in range(radius, len(notes) - radius):
            current = notes[index]

            if current.is_rest():
                continue

            neighbors = notes[index - radius:index] + notes[index + 1:index + radius + 1]
            neighbor_names = [
                note.name
                for note in neighbors
                if not note.is_rest()
            ]

            if not neighbor_names:
                continue

            replacement_name = max(
                set(neighbor_names),
                key=neighbor_names.count,
            )

            if (
                current.duration <= self.false_note_threshold
                and neighbor_names.count(replacement_name) > len(neighbor_names) / 2
            ):
                smoothed[index] = self.copy_note(current, name=replacement_name)

        return smoothed

    def merge_short_gaps(self, notes):
        if not notes:
            return []

        merged = [notes[0]]

        for note in notes[1:]:
            previous = merged[-1]

            if previous.is_rest() or note.is_rest():
                merged.append(note)
                continue

            gap = note.start_time - self.note_end(previous)

            if (
                previous.name == note.name
                and 0 <= gap <= self.short_gap_threshold
            ):
                merged[-1] = self.copy_note(
                    previous,
                    duration=self.note_end(note) - previous.start_time,
                )
            else:
                merged.append(note)

        return merged

    def remove_short_pitch_glitches(self, notes):
        cleaned = list(notes)
        changed = True

        while changed:
            changed = False

            for index in range(1, len(cleaned) - 1):
                previous = cleaned[index - 1]
                current = cleaned[index]
                next_note = cleaned[index + 1]

                if previous.is_rest() or current.is_rest() or next_note.is_rest():
                    continue

                if (
                    previous.name == next_note.name
                    and current.name != previous.name
                    and current.duration <= self.false_note_threshold
                ):
                    cleaned[index - 1] = self.copy_note(
                        previous,
                        duration=self.note_end(next_note) - previous.start_time,
                    )
                    del cleaned[index:index + 2]
                    changed = True
                    break

        return cleaned

    def add_tempo_quantized_rests(
        self,
        notes,
        total_duration=None,
        silence_checker=None,
    ):
        events = []
        previous_end = 0.0

        for note in sorted(notes, key=lambda item: item.start_time):
            gap = note.start_time - previous_end
            rest = self.rest_for_gap(
                previous_end,
                gap,
                silence_checker=silence_checker,
            )

            if rest is not None:
                events.append(rest)

            events.append(note)
            previous_end = max(previous_end, self.note_end(note))

        if total_duration is not None:
            gap = total_duration - previous_end
            rest = self.rest_for_gap(
                previous_end,
                gap,
                silence_checker=silence_checker,
            )

            if rest is not None:
                events.append(rest)

        return events

    def quantize_note_durations(self, notes):
        quantized_notes = []

        for note in notes:
            if note.is_rest():
                quantized_notes.append(note)
                continue

            duration = self.quantize(note.duration)

            if duration is None:
                continue

            quantized_notes.append(self.copy_note(note, duration=duration))

        return quantized_notes

    def rest_for_gap(self, start_time, gap, silence_checker=None):
        if gap < self.min_rest_duration:
            return None

        if silence_checker is not None and not silence_checker(start_time, start_time + gap):
            return None

        duration = self.quantize(gap)

        if duration is None:
            return None

        return DetectedNote(
            name="Rest",
            start_time=start_time,
            duration=duration,
        )

    def quantize(self, duration):
        return quantize_duration(
            duration,
            self.bpm,
            tolerance_ratio=self.config.quantize_tolerance_ratio,
        )

    def note_end(self, note):
        return note.start_time + note.duration

    def copy_note(self, note, **changes):
        data = {
            "name": note.name,
            "start_time": note.start_time,
            "duration": note.duration,
            "staff": getattr(note, "staff", "auto"),
            "raw_start_time": getattr(note, "raw_start_time", None),
            "raw_duration": getattr(note, "raw_duration", None),
            "start_units": getattr(note, "start_units", None),
            "duration_units": getattr(note, "duration_units", None),
        }
        data.update(changes)
        copied_note = DetectedNote(**data)

        for attr in ("confidence", "pitch_instability_cents"):
            if hasattr(note, attr):
                setattr(copied_note, attr, getattr(note, attr))

        return copied_note


@dataclass
class RmsAudioProfile:
    audio: np.ndarray
    sample_rate: int
    silence_threshold: float

    @classmethod
    def from_file(cls, file_path):
        audio, sample_rate = sf.read(file_path, always_2d=True)
        mono_audio = audio.mean(axis=1)
        absolute_audio = np.abs(mono_audio)

        if absolute_audio.size == 0:
            silence_threshold = 0.0
        else:
            max_level = float(np.max(absolute_audio))
            median_level = float(np.median(absolute_audio))
            silence_threshold = max(0.0001, max_level * 0.03, median_level * 0.50)

        return cls(
            audio=mono_audio,
            sample_rate=sample_rate,
            silence_threshold=silence_threshold,
        )

    @property
    def duration(self):
        if self.sample_rate <= 0:
            return 0.0

        return len(self.audio) / self.sample_rate

    def is_low_energy(self, start_time, end_time):
        start_index = max(0, int(start_time * self.sample_rate))
        end_index = min(len(self.audio), int(end_time * self.sample_rate))

        if end_index <= start_index:
            return False

        interval = self.audio[start_index:end_index]
        rms = float(np.sqrt(np.mean(np.square(interval))))
        return rms <= self.silence_threshold
