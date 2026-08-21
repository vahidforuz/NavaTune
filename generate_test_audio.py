import numpy as np
import wave
import os


SAMPLE_RATE = 44100
DURATION = 1.0


NOTES = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "F4": 349.23,
    "G4": 392.00,
    "A4": 440.00,
    "B4": 493.88,
    "C5": 523.25,
}


def create_sine_wave(frequency, duration=DURATION):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    audio = np.sin(2 * np.pi * frequency * t)

    # fade in/out to avoid click sound
    fade_size = int(SAMPLE_RATE * 0.02)
    audio[:fade_size] *= np.linspace(0, 1, fade_size)
    audio[-fade_size:] *= np.linspace(1, 0, fade_size)

    return audio


def save_wav(filename, audio):
    audio_int16 = np.int16(audio * 32767)

    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(audio_int16.tobytes())


def generate_single_notes():
    os.makedirs("test_audio", exist_ok=True)

    for note, freq in NOTES.items():
        audio = create_sine_wave(freq)
        save_wav(f"test_audio/{note}.wav", audio)


def generate_c_major_scale():
    parts = []

    for note in ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]:
        parts.append(create_sine_wave(NOTES[note], duration=0.5))

        silence = np.zeros(int(SAMPLE_RATE * 0.1))
        parts.append(silence)

    audio = np.concatenate(parts)
    save_wav("test_audio/C_major_scale.wav", audio)


def generate_twinkle():
    melody = [
        "C4", "C4", "G4", "G4",
        "A4", "A4", "G4",
        "F4", "F4", "E4", "E4",
        "D4", "D4", "C4",
    ]

    parts = []

    for note in melody:
        parts.append(create_sine_wave(NOTES[note], duration=0.45))
        parts.append(np.zeros(int(SAMPLE_RATE * 0.08)))

    audio = np.concatenate(parts)
    save_wav("test_audio/Twinkle_Twinkle.wav", audio)


def generate_c_major_chord():
    c = create_sine_wave(NOTES["C4"])
    e = create_sine_wave(NOTES["E4"])
    g = create_sine_wave(NOTES["G4"])

    audio = (c + e + g) / 3
    save_wav("test_audio/C_major_chord.wav", audio)


if __name__ == "__main__":
    generate_single_notes()
    generate_c_major_scale()
    generate_twinkle()
    generate_c_major_chord()

    print("Test audio files created in test_audio/")
