import customtkinter as ctk

from ui.waveform import WaveformPanel
from ui.notes_panel import NotesPanel
from ui.notes_editor import NotesEditor
from ui.pdf_preview import PDFPreview


class TabWorkspace(ctk.CTkTabview):
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

        self.add("Waveform")
        self.add("Detected Notes")
        self.add("Edit Notes")
        self.add("Sheet Music")

        self.waveform_panel = WaveformPanel(self.tab("Waveform"))
        self.waveform_panel.pack(fill="both", expand=True)

        self.notes_panel = NotesPanel(self.tab("Detected Notes"))
        self.notes_panel.pack(fill="both", expand=True)

        self.notes_editor = NotesEditor(
            self.tab("Edit Notes"),
            on_notes_changed=self.on_notes_changed,
            get_quarter_note_seconds=get_quarter_note_seconds,
            get_time_signature=get_time_signature,
        )
        self.notes_editor.pack(fill="both", expand=True)

        self.sheet_panel = PDFPreview(
            self.tab("Sheet Music"),
            on_edit_score_details=on_edit_score_details,
            on_refresh_preview=on_refresh_preview,
            on_edit_notes=self.open_notes_editor,
        )
        self.sheet_panel.pack(fill="both", expand=True)

    def load_audio(self, file_path: str):
        self.set("Waveform")
        self.waveform_panel.load_audio(file_path)

    def set_notes(self, notes):
        self.set("Detected Notes")
        self.notes_panel.set_notes(notes)

    def set_editable_notes(self, notes):
        self.notes_editor.set_notes(notes)

    def open_notes_editor(self):
        self.set("Edit Notes")

    def set_sheet_pdf(self, pdf_path: str):
        self.set("Sheet Music")
        self.sheet_panel.load_pdf(pdf_path)

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
        self.notes_panel.set_notes(notes)

        if self.on_notes_changed_callback:
            self.on_notes_changed_callback(notes)
