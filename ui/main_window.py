import tempfile
import os

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from audio.recorder import AudioRecorder
from ui.toolbar import Toolbar
from ui.tab_workspace import TabWorkspace
from ui.export_panel import ExportPanel
from ui.score_details_dialog import ScoreDetailsDialog
from ui.statusbar import StatusBar
from ui.tonality_dialog import TonalityDialog

from detection.basic_pitch_detector import BasicPitchDetector
from detection.nmf_detector import NMFDetector

from detection.pitch_detector import PitchDetector

from export.musicxml_exporter import MusicXMLExporter
from export.musicxml_importer import MusicXMLImporter
from export.pdf_from_musicxml import PDFMusicXMLConverter
from models.score_metadata import ScoreMetadata
from notation.rhythm_analyzer import RhythmAnalyzer
from notation.rhythm_quantizer import RhythmQuantizer
from notation.tonality import (
    AUTOMATIC_TONALITY,
    normalize_tonality_key,
    spell_notes_for_key,
    tonality_label,
)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Music Notation")
        self.geometry("900x600")
        self.minsize(500, 360)
        self.resizable(True, True)

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
            on_detector_changed=self.change_detector,
            on_choose_tonality=self.open_tonality_dialog,
        )
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.workspace = TabWorkspace(
            self,
            on_notes_changed=self.on_notes_changed,
            get_quarter_note_seconds=self.get_quarter_note_seconds,
            get_time_signature=self.get_time_signature,
            on_edit_score_details=self.open_score_details,
            on_refresh_preview=self.refresh_sheet_preview,
        )
        self.workspace.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.export_panel = ExportPanel(
            self,
            on_export_pdf=self.export_pdf,
            on_export_musicxml=self.export_musicxml,
            on_open_musicxml=self.open_musicxml,
        )
        self.export_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        self.statusbar = StatusBar(self)
        self.statusbar.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        self.resize_grip = ttk.Sizegrip(self)
        self.resize_grip.grid(row=3, column=0, sticky="se", padx=(0, 2), pady=(0, 2))

        self.librosa_detector = PitchDetector()
        self.basic_pitch_detector = BasicPitchDetector()
        self.nmf_detector = NMFDetector()

        self.detector_name = "Librosa"
        self.pitch_detector = self.librosa_detector

        self.musicxml_exporter = MusicXMLExporter()
        self.musicxml_importer = MusicXMLImporter()
        self.pdf_converter = PDFMusicXMLConverter()

        self.recorder = AudioRecorder()

        self.selected_tonality = AUTOMATIC_TONALITY
        self.score_metadata = ScoreMetadata()
        self.raw_notes = []
        self.timed_notes = []
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
                tonality=self.selected_tonality,
                score_metadata=self.score_metadata,
            )
            self.statusbar.set_status("MusicXML exported")
            messagebox.showinfo("Success", "MusicXML exported successfully.")

    def open_musicxml(self):
        input_path = filedialog.askopenfilename(
            title="Open MusicXML",
            filetypes=[
                ("MusicXML files", "*.musicxml *.xml"),
                ("All files", "*.*"),
            ],
        )

        if not input_path:
            return

        try:
            bpm, _ = self.get_notation_settings()
            imported_notes = self.musicxml_importer.import_file(input_path, bpm=bpm)
        except Exception as error:
            messagebox.showerror(
                "Open MusicXML failed",
                f"Could not open MusicXML file:\n{error}",
            )
            return

        self.raw_notes = imported_notes
        self.timed_notes = imported_notes
        self.current_notes = imported_notes

        self.workspace.set_notes(self.current_notes)
        self.workspace.set_editable_notes(self.current_notes)
        self.workspace.set("Edit Notes")
        self.refresh_sheet_preview()

        self.statusbar.set_status("MusicXML opened")

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
                tonality=self.selected_tonality,
                score_metadata=self.score_metadata,
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

    def open_score_details(self):
        ScoreDetailsDialog(
            self,
            score_metadata=self.score_metadata,
            on_save=self.update_score_metadata,
        )

    def update_score_metadata(self, score_metadata):
        self.score_metadata = score_metadata.normalized()
        self.refresh_sheet_preview()
        self.statusbar.set_status("Score details updated")

    def open_tonality_dialog(self):
        TonalityDialog(
            self,
            selected_tonality=self.selected_tonality,
            on_selected=self.change_tonality,
        )

    def change_tonality(self, tonality):
        self.selected_tonality = normalize_tonality_key(tonality)
        self.toolbar.set_tonality(self.selected_tonality)

        if self.timed_notes:
            self.current_notes = self.apply_tonality(self.timed_notes)
            self.workspace.set_notes(self.current_notes)
            self.workspace.set_editable_notes(self.current_notes)
            self.refresh_sheet_preview()

        self.statusbar.set_status(
            f"Tonality: {tonality_label(self.selected_tonality)}"
        )

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
            tonality=self.selected_tonality,
            score_metadata=self.score_metadata,
        )
        self.pdf_converter.convert(musicxml_path, pdf_path)

        self.workspace.set_pdf_review_context(
            notes=self.current_notes,
            bpm=bpm,
            time_signature=time_signature,
            tonality=self.selected_tonality,
            score_metadata=self.score_metadata,
        )
        self.workspace.set_sheet_pdf(pdf_path)

    def on_notes_changed(self, notes):
        self.timed_notes = notes
        self.current_notes = notes
        self.refresh_sheet_preview()
        self.statusbar.set_status("Notes updated")

    def process_audio_file(self, file_path):
        self.workspace.load_audio(file_path)

        self.raw_notes = self.pitch_detector.detect_notes_with_time(file_path)
        self.timed_notes = self.prepare_notes_for_timing_mode(
            self.raw_notes,
            file_path=file_path,
        )
        self.current_notes = self.apply_tonality(self.timed_notes)

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

    def get_time_signature(self):
        _, time_signature = self.get_notation_settings()
        return time_signature

    def quantize_notes(self, notes):
        bpm, time_signature = self.get_notation_settings()
        return RhythmQuantizer(
            bpm=bpm,
            time_signature=time_signature,
        ).quantize(notes).notes

    def prepare_notes_for_timing_mode(self, notes, file_path=None):
        if self.use_tempo_quantization():
            rhythm_notes = self.analyze_rhythm(notes, file_path=file_path)
            return self.quantize_notes(rhythm_notes)

        return notes

    def analyze_rhythm(self, notes, file_path=None):
        bpm, _ = self.get_notation_settings()
        analyzer = RhythmAnalyzer(bpm=bpm)

        if file_path:
            return analyzer.analyze_audio_file(notes, file_path)

        return analyzer.analyze(notes)

    def apply_tonality(self, notes):
        return spell_notes_for_key(notes, self.selected_tonality)

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
