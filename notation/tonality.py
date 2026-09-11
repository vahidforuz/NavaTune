from dataclasses import replace
import re


AUTOMATIC_TONALITY = "Automatic / Unknown"

KEY_SIGNATURES = {
    AUTOMATIC_TONALITY: {
        "type": "natural",
        "accidentals": [],
    },
    "C major": {
        "type": "natural",
        "accidentals": [],
    },
    "G major": {
        "type": "sharp",
        "accidentals": ["F#"],
    },
    "D major": {
        "type": "sharp",
        "accidentals": ["F#", "C#"],
    },
    "A major": {
        "type": "sharp",
        "accidentals": ["F#", "C#", "G#"],
    },
    "E major": {
        "type": "sharp",
        "accidentals": ["F#", "C#", "G#", "D#"],
    },
    "F major": {
        "type": "flat",
        "accidentals": ["Bb"],
    },
    "Bb major": {
        "type": "flat",
        "accidentals": ["Bb", "Eb"],
    },
    "Eb major": {
        "type": "flat",
        "accidentals": ["Bb", "Eb", "Ab"],
    },
    "Ab major": {
        "type": "flat",
        "accidentals": ["Bb", "Eb", "Ab", "Db"],
    },
    "A minor": {
        "type": "natural",
        "accidentals": [],
    },
    "E minor": {
        "type": "sharp",
        "accidentals": ["F#"],
    },
    "B minor": {
        "type": "sharp",
        "accidentals": ["F#", "C#"],
    },
    "F# minor": {
        "type": "sharp",
        "accidentals": ["F#", "C#", "G#"],
    },
    "D minor": {
        "type": "flat",
        "accidentals": ["Bb"],
    },
    "G minor": {
        "type": "flat",
        "accidentals": ["Bb", "Eb"],
    },
    "C minor": {
        "type": "flat",
        "accidentals": ["Bb", "Eb", "Ab"],
    },
}

TONALITY_LABELS = {
    AUTOMATIC_TONALITY: AUTOMATIC_TONALITY,
    "C major": "C major",
    "G major": "G major",
    "D major": "D major",
    "A major": "A major",
    "E major": "E major",
    "F major": "F major",
    "Bb major": "B♭ major",
    "Eb major": "E♭ major",
    "Ab major": "A♭ major",
    "A minor": "A minor",
    "E minor": "E minor",
    "B minor": "B minor",
    "F# minor": "F♯ minor",
    "D minor": "D minor",
    "G minor": "G minor",
    "C minor": "C minor",
}

TONALITY_KEYS_BY_LABEL = {
    label: key
    for key, label in TONALITY_LABELS.items()
}

ENHARMONIC_EQUIVALENTS = {
    "C#": "Db",
    "Db": "C#",
    "D#": "Eb",
    "Eb": "D#",
    "F#": "Gb",
    "Gb": "F#",
    "G#": "Ab",
    "Ab": "G#",
    "A#": "Bb",
    "Bb": "A#",
}

FLAT_TO_SHARP = {
    flat_name: sharp_name
    for sharp_name, flat_name in ENHARMONIC_EQUIVALENTS.items()
    if "#" in sharp_name
}
SHARP_TO_FLAT = {
    sharp_name: flat_name
    for sharp_name, flat_name in ENHARMONIC_EQUIVALENTS.items()
    if "#" in sharp_name
}

NOTE_PATTERN = re.compile(r"^([A-Ga-g])([#b♯♭]?)(-?\d+)?$")

SHARP_KEY_SIGNATURE_ORDER = ["F#", "C#", "G#", "D#", "A#", "E#", "B#"]
FLAT_KEY_SIGNATURE_ORDER = ["Bb", "Eb", "Ab", "Db", "Gb", "Cb", "Fb"]

TREBLE_KEY_SIGNATURE_POSITIONS = {
    "F#": "F5",
    "C#": "C5",
    "G#": "G5",
    "D#": "D5",
    "A#": "A4",
    "E#": "E5",
    "B#": "B4",
    "Bb": "B4",
    "Eb": "E5",
    "Ab": "A4",
    "Db": "D5",
    "Gb": "G4",
    "Cb": "C5",
    "Fb": "F4",
}


def get_key_signature(key):
    key = normalize_tonality_key(key)
    return KEY_SIGNATURES.get(key, KEY_SIGNATURES[AUTOMATIC_TONALITY])


def supported_tonalities():
    return list(KEY_SIGNATURES.keys())


def supported_tonality_labels():
    return [
        TONALITY_LABELS[key]
        for key in supported_tonalities()
    ]


def tonality_label(key):
    return TONALITY_LABELS.get(normalize_tonality_key(key), key)


def normalize_tonality_key(key):
    return TONALITY_KEYS_BY_LABEL.get(key, key)


def prefer_sharps_or_flats(key):
    key = normalize_tonality_key(key)

    if key == AUTOMATIC_TONALITY:
        return "automatic"

    return get_key_signature(key)["type"]


def key_signature_accidentals(key):
    key_signature = get_key_signature(key)
    accidental_type = key_signature["type"]
    accidentals = list(key_signature["accidentals"])

    if accidental_type == "sharp":
        order = SHARP_KEY_SIGNATURE_ORDER
    elif accidental_type == "flat":
        order = FLAT_KEY_SIGNATURE_ORDER
    else:
        return []

    return [
        accidental
        for accidental in order
        if accidental in accidentals
    ]


def key_signature_fifths(key):
    key_signature = get_key_signature(key)
    accidental_count = len(key_signature_accidentals(key))

    if key_signature["type"] == "sharp":
        return accidental_count

    if key_signature["type"] == "flat":
        return -accidental_count

    return 0


def key_signature_symbols(key):
    accidental_type = prefer_sharps_or_flats(key)

    if accidental_type == "sharp":
        symbol = "#"
    elif accidental_type == "flat":
        symbol = "b"
    else:
        return []

    return [
        {
            "accidental": accidental,
            "symbol": symbol,
            "staff_note": TREBLE_KEY_SIGNATURE_POSITIONS[accidental],
        }
        for accidental in key_signature_accidentals(key)
    ]


def normalize_note_name(note):
    match = NOTE_PATTERN.match(note.strip())

    if not match:
        return note

    step, accidental, octave = match.groups()
    normalized_accidental = accidental.replace("♯", "#").replace("♭", "b")
    return f"{step.upper()}{normalized_accidental}{octave or ''}"


def split_note_name(note):
    normalized_note = normalize_note_name(note)
    match = NOTE_PATTERN.match(normalized_note)

    if not match:
        return None, None

    step, accidental, octave = match.groups()
    return f"{step.upper()}{accidental}", octave or ""


def convert_to_flat_name(note):
    pitch_class, octave = split_note_name(note)

    if pitch_class in SHARP_TO_FLAT:
        return f"{SHARP_TO_FLAT[pitch_class]}{octave}"

    return normalize_note_name(note)


def convert_to_sharp_name(note):
    pitch_class, octave = split_note_name(note)

    if pitch_class in FLAT_TO_SHARP:
        return f"{FLAT_TO_SHARP[pitch_class]}{octave}"

    return normalize_note_name(note)


def spell_note_for_key(note, key):
    key = normalize_tonality_key(key)

    if key == AUTOMATIC_TONALITY:
        return note

    preference = prefer_sharps_or_flats(key)

    if preference == "flat":
        return convert_to_flat_name(note)

    if preference == "sharp":
        return convert_to_sharp_name(note)

    return normalize_note_name(note)


def spell_notes_for_key(notes, key):
    key = normalize_tonality_key(key)

    if key == AUTOMATIC_TONALITY:
        return list(notes)

    spelled_notes = []

    for note in notes:
        if hasattr(note, "is_rest") and note.is_rest():
            spelled_notes.append(note)
            continue

        if hasattr(note, "name"):
            spelled_notes.append(
                replace(note, name=spell_note_for_key(note.name, key))
            )
        elif hasattr(note, "names"):
            spelled_notes.append(
                replace(
                    note,
                    names=[
                        spell_note_for_key(note_name, key)
                        for note_name in note.names
                    ],
                )
            )
        else:
            spelled_notes.append(spell_note_for_key(str(note), key))

    return spelled_notes
