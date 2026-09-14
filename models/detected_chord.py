from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectedChord:
    names: list[str]
    start_time: float
    duration: float
    staff: str = "auto"
    start_units: Optional[int] = None
    duration_units: Optional[int] = None
