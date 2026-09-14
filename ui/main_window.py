import tempfile
import os
import tkinter as tk

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from audio.recorder import AudioRecorder
from ui.toolbar import Toolbar
from ui.tab_workspace import TabWorkspace
from ui.score_details_dialog import ScoreDetailsDialog
from ui.statusbar import StatusBar
from ui.tonality_dialog import TonalityDialog

from detection.basic_pitch_detector import BasicPitchDetector
from detection.detector_errors import DetectorBackendError
from detection.magenta_onsets_frames_detector import MagentaOnsetsFramesDetector

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


MAGENTA_ONSETS_FRAMES_DETECTOR = "Magenta Onsets and Frames (solo piano)"


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Music Notation")
        self.geometry("900x600")
        self.minsize(760, 360)
        self.resizable(True, True)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.create_menu_bar()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)

        self.toolbar = Toolbar(
            self,
            on_detector_changed=self.change_detector,
            on_choose_tonality=self.open_tonality_dialog,
        )
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))

        self.workspace = TabWorkspace(
            self,
            on_notes_changed=self.on_notes_changed,
            get_quarter_note_seconds=self.get_quarter_note_seconds,
            get_time_signature=self.get_time_signature,
            on_edit_score_details=self.open_score_details,
            on_refresh_preview=self.refresh_sheet_preview,
        )
        self.workspace.grid(row=1, column=0, sticky="nsew", padx=8, pady=(2, 4))

        self.statusbar = StatusBar(self)
        self.statusbar.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 6))

        self.resize_grip = ttk.Sizegrip(self)
        self.resize_grip.grid(row=2, column=0, sticky="se", padx=(0, 2), pady=(0, 2))

        self.basic_pitch_detector = BasicPitchDetector()
        self.magenta_detector = MagentaOnsetsFramesDetector()

        self.detector_name = "Spotify Basic Pitch"
        self.pitch_detector = self.basic_pitch_detector

        self.musicxml_exporter = MusicXMLExporter()
        self.musicxml_importer = MusicXMLImporter()
        self.pdf_converter = PDFMusicXMLConverter()

        self.recorder = AudioRecorder()

        self.selected_tonality = AUTOMATIC_TONALITY
        self.score_metadata = ScoreMetadata()
        self.raw_notes = []
        self.timed_notes = []
        self.current_notes = []
        self.current_musicxml_path = None
        self.preview_refresh_after_id = None

    def create_menu_bar(self):
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Upload", command=self.upload_audio)
        file_menu.add_command(label="Open MusicXML", command=self.open_musicxml)
        file_menu.add_command(label="Save", command=self.save_musicxml)
        file_menu.add_separator()

        export_menu = tk.Menu(file_menu, tearoff=0)
        export_menu.add_command(label="PDF", command=self.export_pdf)
        export_menu.add_command(label="MusicXML", command=self.export_musicxml)
        file_menu.add_cascade(label="Export", menu=export_menu)

        recording_menu = tk.Menu(file_menu, tearoff=0)
        recording_menu.add_command(label="Record", command=self.start_recording)
        recording_menu.add_command(label="Stop", command=self.stop_recording)
        file_menu.add_cascade(label="Recording", menu=recording_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Score Details", command=self.open_score_details)
        edit_menu.add_command(label="Edit Notes", command=lambda: self.workspace.set("Edit Notes"))
        edit_menu.add_command(label="Choose Tonality", command=self.open_tonality_dialog)
        edit_menu.add_command(label="Refresh Sheet Preview", command=self.refresh_sheet_preview)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        setting_menu = tk.Menu(menu_bar, tearoff=0)
        setting_menu.add_command(label="Settings", command=self.open_settings)
        menu_bar.add_cascade(label="Setting", menu=setting_menu)

        advanced_menu = tk.Menu(menu_bar, tearoff=0)
        advanced_menu.add_command(
            label="Waveform",
            command=lambda: self.workspace.show_waveform(),
        )
        advanced_menu.add_command(
            label="Detected Notes",
            command=lambda: self.workspace.show_detected_notes(),
        )
        menu_bar.add_cascade(label="Advanced", menu=advanced_menu)

        about_menu = tk.Menu(menu_bar, tearoff=0)
        about_menu.add_command(label="About NavaTune", command=self.show_about)
        menu_bar.add_cascade(label="About", menu=about_menu)

        self.config(menu=menu_bar)

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
            self.write_musicxml(output_path)
            self.current_musicxml_path = output_path
            self.statusbar.set_status("MusicXML exported")
            messagebox.showinfo("Success", "MusicXML exported successfully.")

    def save_musicxml(self):
        if not self.current_notes:
            messagebox.showwarning(
                "No notes",
                "Please upload an audio file or open a MusicXML file first.",
            )
            return

        if not self.current_musicxml_path:
            output_path = filedialog.asksaveasfilename(
                title="Save MusicXML",
                defaultextension=".musicxml",
                filetypes=[("MusicXML files", "*.musicxml")],
            )
            if not output_path:
                return
            self.current_musicxml_path = output_path

        self.write_musicxml(self.current_musicxml_path)
        self.statusbar.set_status("Saved")
        messagebox.showinfo("Saved", "MusicXML saved successfully.")

    def write_musicxml(self, output_path):
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
        self.current_musicxml_path = input_path

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

    def show_about(self):
        messagebox.showinfo(
            "About NavaTune",
            "NavaTune\nAudio-to-sheet-music notation editor.",
        )

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
        self.cancel_pending_preview_refresh()

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
        bpm, time_signature = self.get_notation_settings()

        self.workspace.set_pdf_review_context(
            notes=self.current_notes,
            bpm=bpm,
            time_signature=time_signature,
            tonality=self.selected_tonality,
            score_metadata=self.score_metadata,
        )
        self.schedule_sheet_preview_refresh()
        self.statusbar.set_status("Notes updated; preview refresh queued")

    def schedule_sheet_preview_refresh(self, delay_ms=700):
        self.cancel_pending_preview_refresh()
        self.preview_refresh_after_id = self.after(delay_ms, self.refresh_sheet_preview)

    def cancel_pending_preview_refresh(self):
        if not self.preview_refresh_after_id:
            return

        try:
            self.after_cancel(self.preview_refresh_after_id)
        except ValueError:
            pass

        self.preview_refresh_after_id = None

    def process_audio_file(self, file_path):
        self.workspace.load_audio(file_path)

        try:
            self.raw_notes = self.pitch_detector.detect_notes_with_time(file_path)
        except DetectorBackendError as error:
            self.statusbar.set_status(str(error))
            messagebox.showinfo("Detector backend error", str(error))
            return

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
            detector_name = "Spotify Basic Pitch"

        if detector_name == "Spotify Basic Pitch":
            self.pitch_detector = self.basic_pitch_detector
            self.statusbar.set_status("Detector: Spotify Basic Pitch")

        elif detector_name == MAGENTA_ONSETS_FRAMES_DETECTOR:
            self.pitch_detector = self.magenta_detector
            self.statusbar.set_status("Detector: Magenta Onsets and Frames")
