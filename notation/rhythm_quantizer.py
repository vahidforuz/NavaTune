from dataclasses import dataclass
from typing import Optional

from models.detected_note import DetectedNote


@dataclass(frozen=True)
class TimeSignature:
    beats: int
    beat_type: int

    @classmethod
    def parse(cls, value: str) -> "TimeSignature":
        beats, beat_type = value.split("/")
        return cls(beats=int(beats), beat_type=int(beat_type))


@dataclass
class NotationEvent:
    kind: str
    duration_units: int
    note: Optional[DetectedNote] = None
    tie_start: bool = False
    tie_stop: bool = False


@dataclass
class NotationMeasure:
    number: int
    events: list[NotationEvent]


@dataclass
class QuantizedScore:
    notes: list[DetectedNote]
    measures: list[NotationMeasure]
    bpm: int
    time_signature: TimeSignature
    divisions: int


class RhythmQuantizer:
    DIVISIONS = 8
    MIN_DURATION_UNITS = 2
    SUPPORTED_DURATION_UNITS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32)

    def __init__(self, bpm: int = 60, time_signature: str = "4/4"):
        self.bpm = max(1, int(bpm))
        self.time_signature = TimeSignature.parse(time_signature)

    @property
    def quarter_note_seconds(self) -> float:
        return 60.0 / self.bpm

    @property
    def unit_seconds(self) -> float:
        return self.quarter_note_seconds / self.DIVISIONS

    @property
    def measure_units(self) -> int:
        return int(
            self.time_signature.beats
            * self.DIVISIONS
            * 4
            / self.time_signature.beat_type
        )

    def quantize(self, raw_notes: list[DetectedNote]) -> QuantizedScore:
        quantized_notes = self.quantize_notes(raw_notes)
        measures = self.build_measures(quantized_notes)

        return QuantizedScore(
            notes=quantized_notes,
            measures=measures,
            bpm=self.bpm,
            time_signature=self.time_signature,
            divisions=self.DIVISIONS,
        )

    def quantize_notes(self, raw_notes: list[DetectedNote]) -> list[DetectedNote]:
        quantized_notes = []

        for raw_note in sorted(raw_notes, key=lambda note: note.start_time):
            start_units = self.seconds_to_units(raw_note.start_time)
            duration_units = self.quantize_duration_units(raw_note.duration)

            quantized_note = DetectedNote(
                name=raw_note.name,
                start_time=self.units_to_seconds(start_units),
                duration=self.units_to_seconds(duration_units),
                staff=getattr(raw_note, "staff", "auto"),
            )
            quantized_note.raw_start_time = raw_note.start_time
            quantized_note.raw_duration = raw_note.duration
            quantized_note.start_units = start_units
            quantized_note.duration_units = duration_units
            quantized_notes.append(quantized_note)

        return quantized_notes

    def build_measures(self, notes: list[DetectedNote]) -> list[NotationMeasure]:
        events = self.build_timeline_events(notes)

        if not events:
            return [NotationMeasure(number=1, events=[
                NotationEvent(kind="rest", duration_units=self.measure_units)
            ])]

        measures = []
        measure_events = []
        current_measure_number = 1
        position_in_measure = 0

        for event in events:
            remaining_units = event.duration_units
            first_segment = True

            while remaining_units > 0:
                space_in_measure = self.measure_units - position_in_measure
                segment_units = min(remaining_units, space_in_measure)

                for chunk_units in self.decompose_duration_units(segment_units):
                    remaining_after_chunk = remaining_units - chunk_units

                    measure_events.append(
                        NotationEvent(
                            kind=event.kind,
                            note=event.note,
                            duration_units=chunk_units,
                            tie_start=(
                                event.kind == "note"
                                and remaining_after_chunk > 0
                            ),
                            tie_stop=(
                                event.kind == "note"
                                and not first_segment
                            ),
                        )
                    )

                    remaining_units -= chunk_units
                    position_in_measure += chunk_units
                    first_segment = False

                    if position_in_measure == self.measure_units:
                        measures.append(
                            NotationMeasure(
                                number=current_measure_number,
                                events=measure_events,
                            )
                        )
                        current_measure_number += 1
                        measure_events = []
                        position_in_measure = 0

        if measure_events:
            if position_in_measure < self.measure_units:
                measure_events.append(
                    NotationEvent(
                        kind="rest",
                        duration_units=self.measure_units - position_in_measure,
                    )
                )

            measures.append(
                NotationMeasure(
                    number=current_measure_number,
                    events=measure_events,
                )
            )

        return measures

    def decompose_duration_units(self, duration_units: int) -> list[int]:
        chunks = []
        remaining_units = duration_units

        for supported_units in sorted(self.SUPPORTED_DURATION_UNITS, reverse=True):
            while remaining_units >= supported_units:
                chunks.append(supported_units)
                remaining_units -= supported_units

        if remaining_units > 0:
            chunks.append(self.closest_supported_units(remaining_units))

        return chunks

    def build_timeline_events(self, notes: list[DetectedNote]) -> list[NotationEvent]:
        events = []
        previous_end_units = 0

        for note in sorted(notes, key=lambda item: item.start_units):
            start_units = note.start_units
            duration_units = max(self.MIN_DURATION_UNITS, note.duration_units)

            if start_units > previous_end_units:
                gap_units = start_units - previous_end_units
                events.extend(self.split_duration("rest", gap_units))

            if note.is_rest():
                events.extend(self.split_duration("rest", duration_units))
            else:
                events.extend(self.split_duration("note", duration_units, note=note))

            previous_end_units = max(previous_end_units, start_units + duration_units)

        return events

    def split_duration(
        self,
        kind: str,
        duration_units: int,
        note: Optional[DetectedNote] = None,
    ) -> list[NotationEvent]:
        events = []
        remaining_units = duration_units

        while remaining_units > 0:
            unit_value = self.closest_supported_units(
                min(remaining_units, max(self.SUPPORTED_DURATION_UNITS))
            )
            unit_value = min(unit_value, remaining_units)

            if unit_value <= 0:
                unit_value = self.MIN_DURATION_UNITS

            events.append(
                NotationEvent(
                    kind=kind,
                    note=note,
                    duration_units=unit_value,
                )
            )
            remaining_units -= unit_value

        return events

    def seconds_to_units(self, seconds: float) -> int:
        units = round(seconds / self.unit_seconds)
        return max(0, int(units))

    def units_to_seconds(self, units: int) -> float:
        return units * self.unit_seconds

    def quantize_duration_units(self, seconds: float) -> int:
        raw_units = max(
            self.MIN_DURATION_UNITS,
            self.seconds_to_units(seconds),
        )
        return self.closest_supported_units(raw_units)

    def closest_supported_units(self, units: int) -> int:
        return min(
            self.SUPPORTED_DURATION_UNITS,
            key=lambda candidate: (abs(candidate - units), -candidate),
        )
