import tkinter as tk

import customtkinter as ctk

from ui.waveform import WaveformPanel
from ui.notes_panel import NotesPanel
from ui.notes_editor import NotesEditor
from ui.pdf_preview import PDFPreview


class TabWorkspace(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_notes_changed=None,
        get_quarter_note_seconds=None,
        get_time_signature=None,
        on_edit_score_details=None,
        on_refresh_preview=None,
    ):
        super().__init__(parent)

        self.on_notes_changed_callback = on_notes_changed
        self.current_audio_path = None
        self.current_notes = []
        self.waveform_window = None
        self.detected_notes_window = None
        self.waveform_panel = None
        self.notes_panel = None
        self.initial_sash_positioned = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.splitter = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=8,
            sashrelief=tk.RAISED,
            bd=0,
            bg="#2b2b2b",
            opaqueresize=True,
        )
        self.splitter.grid(row=0, column=0, sticky="nsew")

        self.sheet_area = ctk.CTkFrame(self)
        self.sheet_area.grid_rowconfigure(1, weight=1)
        self.sheet_area.grid_columnconfigure(0, weight=1)

        self.sheet_title = ctk.CTkLabel(
            self.sheet_area,
            text="Sheet Music",
            font=("Arial", 15, "bold"),
            anchor="w",
        )
        self.sheet_title.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        self.edit_area = ctk.CTkFrame(self)
        self.edit_area.grid_rowconfigure(1, weight=1)
        self.edit_area.grid_columnconfigure(0, weight=1)

        self.edit_title = ctk.CTkLabel(
            self.edit_area,
            text="Edit Notes",
            font=("Arial", 15, "bold"),
            anchor="w",
        )
        self.edit_title.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        self.notes_editor = NotesEditor(
            self.edit_area,
            on_notes_changed=self.on_notes_changed,
            get_quarter_note_seconds=get_quarter_note_seconds,
            get_time_signature=get_time_signature,
        )
        self.notes_editor.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self.sheet_panel = PDFPreview(
            self.sheet_area,
            on_edit_score_details=on_edit_score_details,
            on_refresh_preview=on_refresh_preview,
            on_edit_notes=self.open_notes_editor,
            on_notes_changed=self.on_sheet_notes_changed,
        )
        self.sheet_panel.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self.splitter.add(self.sheet_area, minsize=360, stretch="always")
        self.splitter.add(self.edit_area, minsize=320, stretch="always")
        self.bind("<Configure>", self.position_initial_sash)

    def position_initial_sash(self, event=None):
        if self.initial_sash_positioned:
            return

        width = event.width if event else self.winfo_width()
        if width <= 1:
            self.after(50, self.position_initial_sash)
            return

        self.initial_sash_positioned = True
        self.splitter.sash_place(0, int(width * 0.6), 0)

    def load_audio(self, file_path: str):
        self.current_audio_path = file_path
        if self.waveform_window_is_open():
            self.waveform_panel.load_audio(file_path)

    def set_notes(self, notes):
        self.current_notes = notes
        if self.detected_notes_window_is_open():
            self.notes_panel.set_notes(notes)

    def set_editable_notes(self, notes):
        self.notes_editor.set_notes(notes)

    def open_notes_editor(self):
        self.notes_editor.focus_set()

    def set_sheet_pdf(self, pdf_path: str):
        self.sheet_panel.load_pdf(pdf_path)

    def set(self, _view_name):
        self.open_notes_editor()

    def show_waveform(self):
        if self.waveform_window_is_open():
            self.waveform_window.focus()
            return

        self.waveform_window = ctk.CTkToplevel(self)
        self.waveform_window.title("Waveform")
        self.waveform_window.geometry("900x420")
        self.waveform_window.minsize(640, 320)
        self.waveform_window.grid_rowconfigure(0, weight=1)
        self.waveform_window.grid_columnconfigure(0, weight=1)

        self.waveform_panel = WaveformPanel(self.waveform_window)
        self.waveform_panel.grid(row=0, column=0, sticky="nsew")
        if self.current_audio_path:
            self.waveform_panel.load_audio(self.current_audio_path)

    def show_detected_notes(self):
        if self.detected_notes_window_is_open():
            self.detected_notes_window.focus()
            return

        self.detected_notes_window = ctk.CTkToplevel(self)
        self.detected_notes_window.title("Detected Notes")
        self.detected_notes_window.geometry("900x500")
        self.detected_notes_window.minsize(640, 360)
        self.detected_notes_window.grid_rowconfigure(0, weight=1)
        self.detected_notes_window.grid_columnconfigure(0, weight=1)

        self.notes_panel = NotesPanel(self.detected_notes_window)
        self.notes_panel.grid(row=0, column=0, sticky="nsew")
        self.notes_panel.set_notes(self.current_notes)

    def waveform_window_is_open(self):
        return bool(self.waveform_window and self.waveform_window.winfo_exists())

    def detected_notes_window_is_open(self):
        return bool(
            self.detected_notes_window
            and self.detected_notes_window.winfo_exists()
        )

    def set_pdf_review_context(
        self,
        notes=None,
        bpm=None,
        time_signature=None,
        tonality=None,
        score_metadata=None,
    ):
        self.sheet_panel.set_review_context(
            notes=notes,
            bpm=bpm,
            time_signature=time_signature,
            tonality=tonality,
            score_metadata=score_metadata,
        )

    def on_notes_changed(self, notes):
        self.current_notes = notes
        if self.detected_notes_window_is_open():
            self.notes_panel.set_notes(notes)

        if self.on_notes_changed_callback:
            self.on_notes_changed_callback(notes)

    def on_sheet_notes_changed(self, notes):
        self.current_notes = notes
        if self.detected_notes_window_is_open():
            self.notes_panel.set_notes(notes)
        self.notes_editor.set_notes(notes)

        if self.on_notes_changed_callback:
            self.on_notes_changed_callback(notes)
