from detection.pitch_detector import PitchDetector


def observation(name, time, frequency=440.0, magnitude=1.0):
    return {
        "name": name,
        "time": time,
        "frequency": frequency,
        "magnitude": magnitude,
    }


def test_first_note_ignores_single_frame_transient():
    detector = PitchDetector()

    notes = detector.collapse_stable_frames(
        [
            observation("G4", 0.00),
            observation("C4", 0.01),
            observation("C4", 0.02),
            observation("C4", 0.03),
            observation("C4", 0.04),
            observation("C4", 0.05),
        ],
        frame_duration=0.01,
        global_peak=1.0,
    )

    assert [(note.name, note.start_time) for note in notes] == [("C4", 0.01)]


def test_first_note_start_time_uses_candidate_start_not_confirmation_time():
    detector = PitchDetector()

    notes = detector.collapse_stable_frames(
        [
            observation("A4", 0.10),
            observation("A4", 0.11),
            observation("A4", 0.12),
            observation("A4", 0.13),
            observation("A4", 0.14),
        ],
        frame_duration=0.01,
        global_peak=1.0,
    )

    assert len(notes) == 1
    assert notes[0].name == "A4"
    assert notes[0].start_time == 0.10
    assert round(notes[0].duration, 2) == 0.05
