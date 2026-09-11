from models.detected_note import DetectedNote
from notation.tonality import (
    AUTOMATIC_TONALITY,
    key_signature_accidentals,
    key_signature_fifths,
    key_signature_symbols,
    spell_note_for_key,
    spell_notes_for_key,
)


def test_f_major_prefers_bb_for_a_sharp():
    assert spell_note_for_key("A#4", "F major") == "Bb4"


def test_bb_major_prefers_flats():
    assert spell_note_for_key("A#4", "Bb major") == "Bb4"
    assert spell_note_for_key("D#4", "Bb major") == "Eb4"


def test_eb_major_prefers_flats():
    assert spell_note_for_key("A#4", "Eb major") == "Bb4"
    assert spell_note_for_key("D#4", "Eb major") == "Eb4"
    assert spell_note_for_key("G#4", "Eb major") == "Ab4"


def test_sharp_oriented_keys_prefer_sharps():
    assert spell_note_for_key("Gb4", "G major") == "F#4"
    assert spell_note_for_key("F#4", "G major") == "F#4"


def test_out_of_key_notes_keep_the_same_pitch_class():
    assert spell_note_for_key("F#4", "F major") == "Gb4"
    assert spell_note_for_key("Gb4", "F major") == "Gb4"


def test_automatic_unknown_preserves_existing_note_name():
    assert spell_note_for_key("A#4", AUTOMATIC_TONALITY) == "A#4"
    assert spell_note_for_key("B♭4", AUTOMATIC_TONALITY) == "B♭4"


def test_octave_and_timing_fields_are_preserved_for_note_objects():
    raw_note = DetectedNote(
        name="A#4",
        start_time=1.25,
        duration=0.5,
        staff="treble",
        raw_start_time=1.2,
        raw_duration=0.55,
        start_units=10,
        duration_units=4,
    )

    spelled_note = spell_notes_for_key([raw_note], "F major")[0]

    assert raw_note.name == "A#4"
    assert spelled_note.name == "Bb4"
    assert spelled_note.start_time == raw_note.start_time
    assert spelled_note.duration == raw_note.duration
    assert spelled_note.staff == raw_note.staff
    assert spelled_note.raw_start_time == raw_note.raw_start_time
    assert spelled_note.raw_duration == raw_note.raw_duration
    assert spelled_note.start_units == raw_note.start_units
    assert spelled_note.duration_units == raw_note.duration_units


def test_major_key_signature_accidental_order_and_fifths():
    expected = {
        "C major": ([], 0),
        "G major": (["F#"], 1),
        "D major": (["F#", "C#"], 2),
        "F major": (["Bb"], -1),
        "Bb major": (["Bb", "Eb"], -2),
        "Eb major": (["Bb", "Eb", "Ab"], -3),
        "Ab major": (["Bb", "Eb", "Ab", "Db"], -4),
    }

    for key, (accidentals, fifths) in expected.items():
        assert key_signature_accidentals(key) == accidentals
        assert key_signature_fifths(key) == fifths


def test_minor_key_signature_accidental_order_and_fifths():
    expected = {
        "A minor": ([], 0),
        "E minor": (["F#"], 1),
        "B minor": (["F#", "C#"], 2),
        "F# minor": (["F#", "C#", "G#"], 3),
        "D minor": (["Bb"], -1),
        "G minor": (["Bb", "Eb"], -2),
        "C minor": (["Bb", "Eb", "Ab"], -3),
    }

    for key, (accidentals, fifths) in expected.items():
        assert key_signature_accidentals(key) == accidentals
        assert key_signature_fifths(key) == fifths


def test_key_signature_symbols_include_type_order_and_staff_positions():
    assert key_signature_symbols("D major") == [
        {"accidental": "F#", "symbol": "#", "staff_note": "F5"},
        {"accidental": "C#", "symbol": "#", "staff_note": "C5"},
    ]
    assert key_signature_symbols("Eb major") == [
        {"accidental": "Bb", "symbol": "b", "staff_note": "B4"},
        {"accidental": "Eb", "symbol": "b", "staff_note": "E5"},
        {"accidental": "Ab", "symbol": "b", "staff_note": "A4"},
    ]


def test_automatic_unknown_has_no_key_signature_symbols():
    assert key_signature_accidentals(AUTOMATIC_TONALITY) == []
    assert key_signature_symbols(AUTOMATIC_TONALITY) == []
    assert key_signature_fifths(AUTOMATIC_TONALITY) == 0
