import os
import wave
import numpy as np


SAMPLE_RATE = 44100

NOTES = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "G4": 392.00,
}


def create_sine_wave(frequency, duration):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    audio = np.sin(2 * np.pi * frequency * t)

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


def silence(duration):
    return np.zeros(int(SAMPLE_RATE * duration))


if __name__ == "__main__":
    os.makedirs("test_audio", exist_ok=True)

    parts = []

    # eighth note-ish
    parts.append(create_sine_wave(NOTES["C4"], 0.25))
    parts.append(silence(0.10))

    # quarter note-ish
    parts.append(create_sine_wave(NOTES["D4"], 0.50))
    parts.append(silence(0.10))

    # half note-ish
    parts.append(create_sine_wave(NOTES["E4"], 1.00))
    parts.append(silence(0.10))

    # whole note-ish
    parts.append(create_sine_wave(NOTES["G4"], 2.00))

    audio = np.concatenate(parts)

    save_wav("test_audio/rhythm_test.wav", audio)

    print("Created: test_audio/rhythm_test.wav")
