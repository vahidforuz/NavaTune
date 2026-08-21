from dataclasses import dataclass


@dataclass
class DetectedChord:
    names: list[str]
    start_time: float
    duration: float
