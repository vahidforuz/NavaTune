import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 1
        self.recording = None

    def list_devices(self):
        print(sd.query_devices())

    def record(self, duration=5):
        devices = sd.query_devices()
        print(devices)

        self.recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32"
        )
        sd.wait()
        return self.recording

    def save(self, output_path):
        if self.recording is None:
            return False

        sf.write(output_path, self.recording, self.sample_rate)
        return True