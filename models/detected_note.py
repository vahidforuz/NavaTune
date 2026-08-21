from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectedNote:
    name: str
    start_time: float
    duration: float
    staff: str = "auto"
    raw_start_time: Optional[float] = None
    raw_duration: Optional[float] = None
    start_units: Optional[int] = None
    duration_units: Optional[int] = None

    def is_rest(self):
        return self.name.strip().lower() in {"rest", "silence"}
