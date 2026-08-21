import customtkinter as ctk
import librosa
import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class WaveformPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = None

        self.message = ctk.CTkLabel(
            self,
            text="No audio loaded",
            font=("Arial", 20)
        )
        self.message.pack(expand=True)

    def load_audio(self, file_path: str):
        self.message.pack_forget()

        audio_data, sample_rate = librosa.load(file_path, sr=None)

        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(audio_data)
        ax.set_title("Waveform")
        ax.set_xlabel("Samples")
        ax.set_ylabel("Amplitude")

        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
