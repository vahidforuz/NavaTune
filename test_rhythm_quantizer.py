from models.detected_note import DetectedNote
from notation.rhythm_quantizer import RhythmQuantizer


def test_quarter_and_whole_notes_crossing_measures():
    notes = [
        DetectedNote("C3", 0.0, 1.0),
        DetectedNote("E3", 1.0, 4.0),
        DetectedNote("G3", 5.0, 1.0),
        DetectedNote("B3", 6.0, 4.0),
    ]

    score = RhythmQuantizer(bpm=60, time_signature="4/4").quantize(notes)

    assert [(note.name, note.duration_units) for note in score.notes] == [
        ("C3", 8),
        ("E3", 32),
        ("G3", 8),
        ("B3", 32),
    ]

    assert [
        [
            (
                event.kind,
                getattr(event.note, "name", None),
                event.duration_units,
                event.tie_start,
                event.tie_stop,
            )
            for event in measure.events
        ]
        for measure in score.measures
    ] == [
        [
            ("note", "C3", 8, False, False),
            ("note", "E3", 24, True, False),
        ],
        [
            ("note", "E3", 8, False, True),
            ("note", "G3", 8, False, False),
            ("note", "B3", 16, True, False),
        ],
        [
            ("note", "B3", 16, False, True),
            ("rest", None, 16, False, False),
        ],
    ]


def test_explicit_rest_is_not_exported_as_pitch():
    notes = [
        DetectedNote("C4", 0.0, 1.0),
        DetectedNote("Rest", 1.0, 1.0),
        DetectedNote("E4", 2.0, 1.0),
    ]

    score = RhythmQuantizer(bpm=60, time_signature="4/4").quantize(notes)

    assert [
        (event.kind, getattr(event.note, "name", None), event.duration_units)
        for event in score.measures[0].events[:3]
    ] == [
        ("note", "C4", 8),
        ("rest", None, 8),
        ("note", "E4", 8),
    ]


def test_simultaneous_notes_on_different_hands_are_not_joined_as_chord():
    notes = [
        DetectedNote("C3", 0.0, 1.0, staff="bass"),
        DetectedNote("E4", 0.0, 1.0, staff="treble"),
        DetectedNote("G4", 0.0, 1.0, staff="treble"),
    ]

    score = RhythmQuantizer(bpm=60, time_signature="4/4").quantize(notes)
    note_events = [
        event for event in score.measures[0].events
        if event.kind == "note"
    ]

    assert note_events[0].note.name == "C3"
    assert note_events[0].note.staff == "bass"
    assert note_events[1].note.names == ["E4", "G4"]
    assert note_events[1].note.staff == "treble"
