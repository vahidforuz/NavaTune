import tempfile
import os

import customtkinter as ctk
from tkinter import filedialog, messagebox

from audio.recorder import AudioRecorder
from ui.toolbar import Toolbar
from ui.tab_workspace import TabWorkspace
from ui.export_panel import ExportPanel
from ui.statusbar import StatusBar

from detection.basic_pitch_detector import BasicPitchDetector
from detection.nmf_detector import NMFDetector

from detection.pitch_detector import PitchDetector

from export.musicxml_exporter import MusicXMLExporter
from export.pdf_from_musicxml import PDFMusicXMLConverter
from notation.rhythm_quantizer import RhythmQuantizer


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Music Notation")
        self.geometry("900x600")
        self.minsize(700, 520)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)

        self.toolbar = Toolbar(
            self,
            on_upload=self.upload_audio,
            on_record=self.start_recording,
            on_stop=self.stop_recording,
            on_settings=self.open_settings,
            on_detector_changed=self.change_detector
        )
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.workspace = TabWorkspace(
            self,
            on_notes_changed=self.on_notes_changed,
            get_quarter_note_seconds=self.get_quarter_note_seconds,
        )
        self.workspace.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.export_panel = ExportPanel(
            self,
            on_export_pdf=self.export_pdf,
            on_export_musicxml=self.export_musicxml,
        )
        self.export_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        self.statusbar = StatusBar(self)
        self.statusbar.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        self.librosa_detector = PitchDetector()
        self.basic_pitch_detector = BasicPitchDetector()
        self.nmf_detector = NMFDetector()

        self.detector_name = "Librosa"
        self.pitch_detector = self.librosa_detector

        self.musicxml_exporter = MusicXMLExporter()
        self.pdf_converter = PDFMusicXMLConverter()

        self.recorder = AudioRecorder()

        self.raw_notes = []
        self.current_notes = []

    def upload_audio(self):
        file_path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac"),
                ("All files", "*.*"),
            ],
        )

        if file_path:
            self.statusbar.set_status("Audio loaded")
            self.process_audio_file(file_path)

    def export_musicxml(self):
        if not self.current_notes:
            messagebox.showwarning(
                "No notes",
                "Please upload an audio file and detect notes first.",
            )
            return

        output_path = filedialog.asksaveasfilename(
            title="Save MusicXML",
            defaultextension=".musicxml",
            filetypes=[("MusicXML files", "*.musicxml")],
        )

        if output_path:
            bpm, time_signature = self.get_notation_settings()
            self.musicxml_exporter.export(
                self.current_notes,
                output_path,
                bpm=bpm,
                time_signature=time_signature,
                use_tempo_quantization=self.use_tempo_quantization(),
            )
            self.statusbar.set_status("MusicXML exported")
            messagebox.showinfo("Success", "MusicXML exported successfully.")

    def export_pdf(self):
        if not self.current_notes:
            messagebox.showwarning(
                "No notes",
                "Please upload an audio file and detect notes first.",
            )
            return

        pdf_path = filedialog.asksaveasfilename(
            title="Save PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )

        if pdf_path:
            musicxml_path = pdf_path.replace(".pdf", ".musicxml")
            bpm, time_signature = self.get_notation_settings()

            self.musicxml_exporter.export(
                self.current_notes,
                musicxml_path,
                bpm=bpm,
                time_signature=time_signature,
                use_tempo_quantization=self.use_tempo_quantization(),
            )
            self.pdf_converter.convert(musicxml_path, pdf_path)

            self.statusbar.set_status("PDF exported")
            messagebox.showinfo("Success", "PDF exported successfully.")

    def start_recording(self):
        self.statusbar.set_status("Recording 5 seconds...")

        self.recorder.record(duration=5)

        temp_dir = tempfile.gettempdir()
        recorded_path = os.path.join(temp_dir, "navatune_recording.wav")

        self.recorder.save(recorded_path)

        self.statusbar.set_status("Recording saved")

        self.process_audio_file(recorded_path)

    def stop_recording(self):
        self.statusbar.set_status("Stopped")

    def open_settings(self):
        self.statusbar.set_status("Settings opened")

    def refresh_sheet_preview(self):
        if not self.current_notes:
            return

        temp_dir = tempfile.gettempdir()
        musicxml_path = os.path.join(temp_dir, "navatune_preview.musicxml")
        pdf_path = os.path.join(temp_dir, "navatune_preview.pdf")
        bpm, time_signature = self.get_notation_settings()

        self.musicxml_exporter.export(
            self.current_notes,
            musicxml_path,
            bpm=bpm,
            time_signature=time_signature,
            use_tempo_quantization=self.use_tempo_quantization(),
        )
        self.pdf_converter.convert(musicxml_path, pdf_path)

        self.workspace.set_sheet_pdf(pdf_path)

    def on_notes_changed(self, notes):
        self.current_notes = notes
        self.refresh_sheet_preview()
        self.statusbar.set_status("Notes updated")

    def process_audio_file(self, file_path):
        self.workspace.load_audio(file_path)

        self.raw_notes = self.pitch_detector.detect_notes_with_time(file_path)
        self.current_notes = self.prepare_notes_for_timing_mode(self.raw_notes)

        self.workspace.set_notes(self.current_notes)
        self.workspace.set_editable_notes(self.current_notes)

        self.statusbar.set_status("Notes detected")

        self.refresh_sheet_preview()

    def get_notation_settings(self):
        return (
            self.toolbar.get_tempo_bpm(),
            self.toolbar.get_time_signature(),
        )

    def get_quarter_note_seconds(self):
        bpm, _ = self.get_notation_settings()
        return 60.0 / bpm

    def quantize_notes(self, notes):
        bpm, time_signature = self.get_notation_settings()
        return RhythmQuantizer(
            bpm=bpm,
            time_signature=time_signature,
        ).quantize(notes).notes

    def prepare_notes_for_timing_mode(self, notes):
        if self.use_tempo_quantization():
            return self.quantize_notes(notes)

        return notes

    def use_tempo_quantization(self):
        return self.toolbar.use_tempo_quantization()

    def change_detector(self, detector_name):
        self.detector_name = detector_name

        if detector_name == "Librosa":
            self.pitch_detector = self.librosa_detector
            self.statusbar.set_status("Detector: Librosa")

        elif detector_name == "Spotify Basic Pitch":
            self.pitch_detector = self.basic_pitch_detector
            self.statusbar.set_status("Detector: Spotify Basic Pitch")

        elif detector_name == "NMF (Non-negative Matrix Factorization)":
            self.pitch_detector = self.nmf_detector
            self.statusbar.set_status("Detector: NMF")
