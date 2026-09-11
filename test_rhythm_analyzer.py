import numpy as np
import soundfile as sf

from models.detected_note import DetectedNote
from notation.rhythm_analyzer import (
    RhythmAnalyzer,
    get_allowed_note_durations,
    get_quarter_duration,
    quantize_duration,
)


def note(name, start_time, duration, confidence=None, instability=None):
    detected_note = DetectedNote(name, start_time, duration)

    if confidence is not None:
        detected_note.confidence = confidence

    if instability is not None:
        detected_note.pitch_instability_cents = instability

    return detected_note


def names_and_durations(events):
    return [
        (event.name, event.start_time, event.duration)
        for event in events
    ]


def test_quarter_duration_uses_tempo():
    assert get_quarter_duration(60) == 1.0
    assert get_quarter_duration(120) == 0.5


def test_allowed_note_durations_at_60_bpm():
    assert [
        (duration.name, duration.seconds)
        for duration in get_allowed_note_durations(60)
    ] == [
        ("sixteenth", 0.25),
        ("eighth", 0.5),
        ("quarter", 1.0),
        ("half", 2.0),
        ("whole", 4.0),
    ]


def test_tempo_60_quantizes_notes_to_musical_durations():
    assert quantize_duration(1.0, 60) == 1.0
    assert quantize_duration(0.5, 60) == 0.5
    assert quantize_duration(2.0, 60) == 2.0
    assert quantize_duration(0.94, 60) == 1.0
    assert quantize_duration(0.47, 60) == 0.5


def test_tempo_120_quantizes_notes_to_musical_durations():
    assert quantize_duration(0.5, 120) == 0.5
    assert quantize_duration(0.25, 120) == 0.25
    assert quantize_duration(1.0, 120) == 1.0


def test_silence_gaps_become_tempo_based_rests_at_60_bpm():
    analyzer = RhythmAnalyzer(bpm=60)
    events = analyzer.analyze([
        note("F#4", 0.0, 1.0),
        note("G#4", 2.0, 0.5),
        note("A#4", 3.0, 0.5),
    ])

    assert names_and_durations(events) == [
        ("F#4", 0.0, 1.0),
        ("Rest", 1.0, 1.0),
        ("G#4", 2.0, 0.5),
        ("Rest", 2.5, 0.5),
        ("A#4", 3.0, 0.5),
    ]


def test_short_gap_between_same_pitch_does_not_create_rest():
    analyzer = RhythmAnalyzer(bpm=60)
    events = analyzer.analyze([
        note("F#4", 0.0, 0.5),
        note("F#4", 0.54, 0.5),
    ])

    assert names_and_durations(events) == [
        ("F#4", 0.0, 1.0),
    ]


def test_false_pitch_glitch_is_removed_and_surrounding_notes_merge():
    analyzer = RhythmAnalyzer(bpm=60)
    events = analyzer.analyze([
        note("F#4", 0.0, 0.5),
        note("G4", 0.5, 0.04),
        note("F#4", 0.54, 0.5),
    ])

    assert names_and_durations(events) == [
        ("F#4", 0.0, 1.0),
    ]


def test_low_confidence_pitch_is_rejected_not_guessed():
    analyzer = RhythmAnalyzer(bpm=60)
    events = analyzer.analyze([
        note("F#4", 0.0, 1.0, confidence=0.2),
    ])

    assert events == []


def test_unstable_pitch_is_rejected_not_guessed():
    analyzer = RhythmAnalyzer(bpm=60)
    events = analyzer.analyze([
        note("F#4", 0.0, 1.0, instability=80.0),
    ])

    assert events == []


def test_tempo_changes_duration_but_not_pitch_name():
    analyzer = RhythmAnalyzer(bpm=120)
    events = analyzer.analyze([
        note("A#4", 0.0, 0.47),
    ])

    assert names_and_durations(events) == [
        ("A#4", 0.0, 0.5),
    ]


def test_rms_low_energy_gap_becomes_rest(tmp_path):
    sample_rate = 8000
    tone = np.sin(2 * np.pi * 440 * np.arange(sample_rate) / sample_rate) * 0.2
    silence = np.zeros(sample_rate)
    audio = np.concatenate([tone, silence, tone])
    audio_path = tmp_path / "note_rest_note.wav"
    sf.write(audio_path, audio, sample_rate)

    analyzer = RhythmAnalyzer(bpm=60)
    events = analyzer.analyze_audio_file(
        [
            note("A4", 0.0, 1.0),
            note("B4", 2.0, 1.0),
        ],
        str(audio_path),
    )

    assert names_and_durations(events) == [
        ("A4", 0.0, 1.0),
        ("Rest", 1.0, 1.0),
        ("B4", 2.0, 1.0),
    ]


def test_rms_high_energy_uncertain_gap_does_not_become_rest(tmp_path):
    sample_rate = 8000
    tone = np.sin(2 * np.pi * 440 * np.arange(sample_rate * 3) / sample_rate) * 0.2
    audio_path = tmp_path / "continuous_energy.wav"
    sf.write(audio_path, tone, sample_rate)

    analyzer = RhythmAnalyzer(bpm=60)
    events = analyzer.analyze_audio_file(
        [
            note("A4", 0.0, 1.0),
            note("Unknown", 1.0, 1.0, confidence=0.1),
            note("B4", 2.0, 1.0),
        ],
        str(audio_path),
    )

    assert names_and_durations(events) == [
        ("A4", 0.0, 1.0),
        ("B4", 2.0, 1.0),
    ]
