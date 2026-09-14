import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser

import customtkinter as ctk
import fitz
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image

from notation.tonality import tonality_label
from ui.notes_editor import NotesEditor


NOTE_PATTERN = re.compile(r"^([A-G])([#b♯♭]?)(-?\d+)$")
PITCH_CLASS_ORDER = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}


class PDFPreview(ctk.CTkFrame):
    MIN_ZOOM = 0.5
    MAX_ZOOM = 3.0
    ZOOM_STEP = 0.25
    BASE_RENDER_SCALE = 1.5
    DENSE_MEASURE_LIMIT = 12
    AWKWARD_GAP_BEATS = 2.0
    MAX_PDF_HISTORY = 20
    ANNOT_COLORS = {
        "Yellow": (1, 0.92, 0.2),
        "Red": (1, 0.2, 0.2),
        "Blue": (0.2, 0.45, 1),
        "Green": (0.2, 0.8, 0.35),
        "Black": (0, 0, 0),
    }
    STAMP_LABELS = ["Fix", "Check", "Wrong note", "Good"]

    def __init__(
        self,
        parent,
        on_edit_score_details=None,
        on_refresh_preview=None,
        on_edit_notes=None,
        on_notes_changed=None,
    ):
        super().__init__(parent)

        self.on_edit_score_details = on_edit_score_details
        self.on_refresh_preview = on_refresh_preview
        self.on_edit_notes = on_edit_notes
        self.on_notes_changed = on_notes_changed
        self.pdf_path = None
        self.page_count = 0
        self.current_page = 1
        self.zoom = 1.0
        self.fit_mode = None
        self.notes = []
        self.review_context = {}
        self.review_enabled = tk.BooleanVar(value=False)
        self.page_images = []
        self.thumbnail_images = []
        self.page_frames = []
        self.page_labels = []
        self.issue_buttons = []
        self.measure_buttons = []
        self.annotation_mode = tk.StringVar(value="Select")
        self.annotation_color = tk.StringVar(value="Yellow")
        self.show_measure_overlay = tk.BooleanVar(value=False)
        self.pdf_undo_stack = []
        self.pdf_redo_stack = []
        self.before_edit_pdf_bytes = None
        self.drag_start = None
        self.freehand_points = []
        self.active_page_label = None
        self.edit_tools_visible = False

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.toolbar = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=(10, 0),
        )

        self.score_details_btn = ctk.CTkButton(
            self.toolbar,
            text="Score Details",
            command=self.open_score_details,
            width=120,
        )
        self.score_details_btn.pack(side="left", padx=(0, 5))

        self.refresh_btn = ctk.CTkButton(
            self.toolbar,
            text="Refresh",
            command=self.refresh_preview,
            width=85,
        )
        self.refresh_btn.pack(side="left", padx=5)

        self.open_btn = ctk.CTkButton(
            self.toolbar,
            text="Open/Edit PDF",
            command=self.open_pdf_edit_tools,
            width=115,
        )
        self.open_btn.pack(side="left", padx=5)

        self.edit_notes_btn = ctk.CTkButton(
            self.toolbar,
            text="Edit Notes",
            command=self.open_notes_editor,
            width=90,
        )
        self.edit_notes_btn.pack(side="left", padx=5)

        self.review_toggle = ctk.CTkCheckBox(
            self.toolbar,
            text="Review",
            variable=self.review_enabled,
            command=self.toggle_review_panel,
            width=80,
        )
        self.review_toggle.pack(side="left", padx=(15, 5))

        self.prev_btn = ctk.CTkButton(
            self.toolbar,
            text="Prev",
            command=self.previous_page,
            width=70,
        )
        self.prev_btn.pack(side="left", padx=(20, 5))

        self.page_label = ctk.CTkLabel(self.toolbar, text="Page 0/0", width=90)
        self.page_label.pack(side="left", padx=5)

        self.next_btn = ctk.CTkButton(
            self.toolbar,
            text="Next",
            command=self.next_page,
            width=70,
        )
        self.next_btn.pack(side="left", padx=5)

        self.zoom_out_btn = ctk.CTkButton(
            self.toolbar,
            text="-",
            command=self.zoom_out,
            width=35,
        )
        self.zoom_out_btn.pack(side="left", padx=(20, 3))

        self.zoom_label = ctk.CTkLabel(self.toolbar, text="100%", width=55)
        self.zoom_label.pack(side="left", padx=3)

        self.zoom_in_btn = ctk.CTkButton(
            self.toolbar,
            text="+",
            command=self.zoom_in,
            width=35,
        )
        self.zoom_in_btn.pack(side="left", padx=3)

        self.fit_width_btn = ctk.CTkButton(
            self.toolbar,
            text="Fit Width",
            command=self.fit_width,
            width=85,
        )
        self.fit_width_btn.pack(side="left", padx=5)

        self.fit_page_btn = ctk.CTkButton(
            self.toolbar,
            text="Fit Page",
            command=self.fit_page,
            width=80,
        )
        self.fit_page_btn.pack(side="left", padx=5)

        self.reset_zoom_btn = ctk.CTkButton(
            self.toolbar,
            text="Reset",
            command=self.reset_zoom,
            width=70,
        )
        self.reset_zoom_btn.pack(side="left", padx=5)

        self.pdf_tools_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pdf_tools_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=(6, 0),
        )

        self.save_as_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Save As PDF",
            command=self.save_as_pdf,
            width=100,
        )
        self.save_as_btn.pack(side="left", padx=(0, 4))

        self.open_external_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Open System App",
            command=self.open_pdf_external,
            width=120,
        )
        self.open_external_btn.pack(side="left", padx=4)

        self.export_image_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Export Page Image",
            command=self.export_current_page_image,
            width=135,
        )
        self.export_image_btn.pack(side="left", padx=4)

        self.print_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Print",
            command=self.print_pdf,
            width=70,
        )
        self.print_btn.pack(side="left", padx=4)

        self.rotate_left_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Rotate Left",
            command=lambda: self.rotate_current_page(-90),
            width=95,
        )
        self.rotate_left_btn.pack(side="left", padx=4)

        self.rotate_right_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Rotate Right",
            command=lambda: self.rotate_current_page(90),
            width=100,
        )
        self.rotate_right_btn.pack(side="left", padx=4)

        self.delete_page_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Delete Page",
            command=self.delete_current_page,
            width=100,
        )
        self.delete_page_btn.pack(side="left", padx=4)

        self.pages_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Pages...",
            command=self.open_pages_tools,
            width=80,
        )
        self.pages_btn.pack(side="left", padx=4)

        self.advanced_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Advanced...",
            command=self.open_advanced_tools,
            width=95,
        )
        self.advanced_btn.pack(side="left", padx=4)

        self.pdf_undo_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Undo PDF",
            command=self.undo_pdf_edit,
            width=85,
        )
        self.pdf_undo_btn.pack(side="left", padx=(14, 4))

        self.pdf_redo_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Redo PDF",
            command=self.redo_pdf_edit,
            width=85,
        )
        self.pdf_redo_btn.pack(side="left", padx=4)

        self.compare_btn = ctk.CTkButton(
            self.pdf_tools_frame,
            text="Compare",
            command=self.compare_before_after,
            width=85,
        )
        self.compare_btn.pack(side="left", padx=4)

        self.annotation_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.annotation_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=(6, 0),
        )

        self.annotation_mode_menu = ctk.CTkOptionMenu(
            self.annotation_frame,
            values=[
                "Select",
                "Text",
                "Highlight",
                "Pen",
                "Eraser",
                "Rectangle",
                "Circle",
                "Arrow",
                "Stamp",
                "Measure",
            ],
            variable=self.annotation_mode,
            width=115,
        )
        self.annotation_mode_menu.pack(side="left", padx=(0, 4))

        self.annotation_color_menu = ctk.CTkOptionMenu(
            self.annotation_frame,
            values=list(self.ANNOT_COLORS),
            variable=self.annotation_color,
            width=90,
        )
        self.annotation_color_menu.pack(side="left", padx=4)

        self.stamp_menu = ctk.CTkOptionMenu(
            self.annotation_frame,
            values=self.STAMP_LABELS,
            width=110,
        )
        self.stamp_menu.set("Fix")
        self.stamp_menu.pack(side="left", padx=4)

        self.measure_overlay_toggle = ctk.CTkCheckBox(
            self.annotation_frame,
            text="Measure numbers",
            variable=self.show_measure_overlay,
            command=self.render_current_page,
            width=135,
        )
        self.measure_overlay_toggle.pack(side="left", padx=(12, 4))

        self.music_tools_btn = ctk.CTkButton(
            self.annotation_frame,
            text="Music Tools...",
            command=self.open_music_tools,
            width=110,
        )
        self.music_tools_btn.pack(side="left", padx=4)

        self.pdf_tools_frame.grid_remove()
        self.annotation_frame.grid_remove()

        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=3, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=0)
        self.main_panel.grid_columnconfigure(1, weight=1)

        self.reviewer_panel = ctk.CTkScrollableFrame(self.main_panel, width=260)
        self.reviewer_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 10))

        self.status_label = ctk.CTkLabel(
            self.reviewer_panel,
            text="Needs review",
            font=("Arial", 16, "bold"),
        )
        self.status_label.pack(anchor="w", padx=10, pady=(10, 6))

        self.stats_label = ctk.CTkLabel(
            self.reviewer_panel,
            text="No PDF loaded",
            justify="left",
            anchor="w",
        )
        self.stats_label.pack(fill="x", padx=10, pady=(0, 10))

        self.issues_title = ctk.CTkLabel(
            self.reviewer_panel,
            text="Review Checklist",
            font=("Arial", 14, "bold"),
        )
        self.issues_title.pack(anchor="w", padx=10, pady=(5, 5))

        self.issues_frame = ctk.CTkFrame(self.reviewer_panel, fg_color="transparent")
        self.issues_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.measures_title = ctk.CTkLabel(
            self.reviewer_panel,
            text="Measures",
            font=("Arial", 14, "bold"),
        )
        self.measures_title.pack(anchor="w", padx=10, pady=(5, 5))

        self.measures_frame = ctk.CTkFrame(self.reviewer_panel, fg_color="transparent")
        self.measures_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.viewer_panel = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.viewer_panel.grid(row=0, column=1, sticky="nsew")
        self.viewer_panel.grid_rowconfigure(0, weight=1)
        self.viewer_panel.grid_columnconfigure(1, weight=1)

        self.thumbnails_frame = ctk.CTkScrollableFrame(self.viewer_panel, width=120)
        self.thumbnails_frame.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        self.canvas = tk.Canvas(self.viewer_panel, highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew")

        self.vertical_scrollbar = ctk.CTkScrollbar(
            self.viewer_panel,
            orientation="vertical",
            command=self.canvas.yview,
            button_color="#3b8ed0",
            button_hover_color="#1f6aa5",
        )
        self.vertical_scrollbar.grid(row=0, column=2, sticky="ns", padx=(4, 0))

        self.horizontal_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="horizontal",
            command=self.canvas.xview,
            button_color="#3b8ed0",
            button_hover_color="#1f6aa5",
        )
        self.horizontal_scrollbar.grid(row=4, column=0, sticky="ew", padx=(280, 10), pady=(4, 10))

        self.canvas.configure(
            xscrollcommand=self.horizontal_scrollbar.set,
            yscrollcommand=self.vertical_scrollbar.set,
        )

        self.preview_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.preview_window = self.canvas.create_window(
            (0, 0),
            window=self.preview_frame,
            anchor="nw",
        )

        self.empty_label = ctk.CTkLabel(self.preview_frame, text="No sheet preview yet")
        self.empty_label.pack(padx=10, pady=10)

        self.preview_frame.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.preview_frame)
        self.update_controls()
        self.toggle_review_panel()

    def open_score_details(self):
        if self.on_edit_score_details:
            self.on_edit_score_details()

    def open_notes_editor(self):
        if self.on_edit_notes:
            self.on_edit_notes()

    def refresh_preview(self):
        if self.on_refresh_preview:
            self.on_refresh_preview()
        elif self.pdf_path:
            self.load_pdf(self.pdf_path)

    def open_pdf_external(self):
        if self.pdf_path and os.path.exists(self.pdf_path):
            webbrowser.open_new(f"file://{os.path.abspath(self.pdf_path)}")

    def open_pdf_edit_tools(self):
        self.edit_tools_visible = not self.edit_tools_visible

        if self.edit_tools_visible:
            self.pdf_tools_frame.grid()
            self.annotation_frame.grid()
            self.open_btn.configure(text="Close PDF Edit")
        else:
            self.pdf_tools_frame.grid_remove()
            self.annotation_frame.grid_remove()
            self.annotation_mode.set("Select")
            self.open_btn.configure(text="Open/Edit PDF")

        self.after(20, self.update_scroll_region)

    def add_pdf_tool_section(self, parent, row, column, title, actions, columnspan=1):
        section = ctk.CTkFrame(parent)
        section.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="nsew",
            padx=8,
            pady=8,
        )
        ctk.CTkLabel(
            section,
            text=title,
            font=("Arial", 15, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 8))

        for text, command in actions:
            ctk.CTkButton(
                section,
                text=text,
                command=command,
                anchor="w",
            ).pack(fill="x", padx=12, pady=4)

    def toggle_measure_numbers(self):
        self.show_measure_overlay.set(not self.show_measure_overlay.get())
        self.render_current_page()

    def save_as_pdf(self):
        if not self.has_pdf():
            return

        output_path = filedialog.asksaveasfilename(
            title="Save PDF As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not output_path:
            return

        try:
            shutil.copyfile(self.pdf_path, output_path)
            messagebox.showinfo("Saved", "PDF saved successfully.")
        except OSError as error:
            messagebox.showerror("Save failed", f"Could not save PDF:\n{error}")

    def export_current_page_image(self):
        if not self.has_pdf():
            return

        output_path = filedialog.asksaveasfilename(
            title="Export Current Page",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg *.jpeg")],
        )
        if not output_path:
            return

        try:
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pix.save(output_path)
            messagebox.showinfo("Exported", "Current page exported successfully.")
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Export failed", f"Could not export page image:\n{error}")

    def print_pdf(self):
        if not self.has_pdf():
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(os.path.abspath(self.pdf_path), "print")
            elif sys.platform == "darwin":
                subprocess.run(["lp", self.pdf_path], check=True)
            else:
                subprocess.run(["lp", self.pdf_path], check=True)
            messagebox.showinfo("Print", "PDF sent to the default printer.")
        except (OSError, subprocess.CalledProcessError) as error:
            messagebox.showerror("Print failed", f"Could not print PDF:\n{error}")

    def rotate_current_page(self, degrees):
        if not self.has_pdf():
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                page.set_rotation((page.rotation + degrees) % 360)
                self.save_pdf_document(doc)
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Rotate failed", f"Could not rotate page:\n{error}")

    def delete_current_page(self):
        if not self.has_pdf() or self.page_count <= 1:
            messagebox.showwarning("Delete page", "A PDF must keep at least one page.")
            return

        if not messagebox.askyesno(
            "Delete page",
            f"Delete page {self.current_page} from this PDF?",
        ):
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                doc.delete_page(self.current_page - 1)
                self.save_pdf_document(doc)
            self.current_page = min(self.current_page, self.page_count - 1)
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Delete failed", f"Could not delete page:\n{error}")

    def open_pages_tools(self):
        window = ctk.CTkToplevel(self)
        window.title("PDF Pages")
        window.geometry("360x300")
        window.resizable(False, False)

        buttons = [
            ("Reorder Pages", self.reorder_pages),
            ("Merge Another PDF", self.merge_pdf),
            ("Split Selected Pages", self.split_pages),
        ]
        for text, command in buttons:
            button = ctk.CTkButton(
                window,
                text=text,
                command=command,
                width=220,
            )
            button.pack(fill="x", padx=20, pady=(16 if text == "Reorder Pages" else 6, 6))

        info = ctk.CTkLabel(
            window,
            text="Use page ranges like 1,3,5-7.",
            justify="left",
            anchor="w",
        )
        info.pack(fill="x", padx=20, pady=(10, 0))
        window.transient(self.winfo_toplevel())
        window.focus()

    def reorder_pages(self):
        if not self.has_pdf():
            return

        order_text = simpledialog.askstring(
            "Reorder Pages",
            f"Enter all pages in the new order, 1-{self.page_count}:",
            parent=self,
        )
        if not order_text:
            return

        try:
            order = self.parse_page_list(order_text, require_all=True)
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as source:
                output = fitz.open()
                for page_number in order:
                    output.insert_pdf(
                        source,
                        from_page=page_number - 1,
                        to_page=page_number - 1,
                    )
                self.save_pdf_document(output)
                output.close()
            self.current_page = 1
            self.render_pdf()
        except (ValueError, RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Reorder failed", f"Could not reorder pages:\n{error}")

    def merge_pdf(self):
        if not self.has_pdf():
            return

        input_path = filedialog.askopenfilename(
            title="Merge Another PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not input_path:
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                with fitz.open(input_path) as other:
                    doc.insert_pdf(other)
                self.save_pdf_document(doc)
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Merge failed", f"Could not merge PDF:\n{error}")

    def split_pages(self):
        if not self.has_pdf():
            return

        pages_text = simpledialog.askstring(
            "Split Pages",
            f"Pages to export from 1-{self.page_count}:",
            parent=self,
        )
        if not pages_text:
            return

        output_path = filedialog.asksaveasfilename(
            title="Save Split PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not output_path:
            return

        try:
            pages = self.parse_page_list(pages_text)
            with fitz.open(self.pdf_path) as source:
                output = fitz.open()
                for page_number in pages:
                    output.insert_pdf(
                        source,
                        from_page=page_number - 1,
                        to_page=page_number - 1,
                    )
                output.save(output_path, garbage=4, deflate=True)
                output.close()
            messagebox.showinfo("Split PDF", "Selected pages saved successfully.")
        except (ValueError, RuntimeError, OSError) as error:
            messagebox.showerror("Split failed", f"Could not split PDF:\n{error}")

    def open_advanced_tools(self):
        window = ctk.CTkToplevel(self)
        window.title("Advanced PDF Tools")
        window.geometry("390x460")
        window.resizable(False, False)

        buttons = [
            ("Extract Text / OCR", self.extract_pdf_text),
            ("Crop Margins", self.crop_margins),
            ("Page Layout", self.open_page_layout_tools),
            ("Add Page Numbers", self.add_page_numbers),
            ("Remove Page Numbers", self.remove_page_number_annotations),
            ("Add Watermark / Signature", self.add_watermark),
            ("Import Existing PDF", self.import_existing_pdf),
            ("Export Annotated PDF", self.save_as_pdf),
        ]
        for text, command in buttons:
            button = ctk.CTkButton(window, text=text, command=command, width=250)
            button.pack(fill="x", padx=20, pady=(14 if text == "Extract Text / OCR" else 5, 5))

        info = ctk.CTkLabel(
            window,
            text=(
                "Text extraction uses embedded PDF text.\n"
                "Scanned-page OCR needs an OCR backend."
            ),
            justify="left",
            anchor="w",
        )
        info.pack(fill="x", padx=20, pady=(12, 0))
        window.transient(self.winfo_toplevel())
        window.focus()

    def extract_pdf_text(self):
        if not self.has_pdf():
            return

        output_path = filedialog.asksaveasfilename(
            title="Save Extracted Text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
        )
        if not output_path:
            return

        try:
            with fitz.open(self.pdf_path) as doc:
                text = "\n\n".join(
                    f"--- Page {index + 1} ---\n{page.get_text()}"
                    for index, page in enumerate(doc)
                )
            with open(output_path, "w", encoding="utf-8") as output:
                output.write(text)
            messagebox.showinfo("Text extracted", "PDF text saved successfully.")
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Extract failed", f"Could not extract text:\n{error}")

    def crop_margins(self):
        if not self.has_pdf():
            return

        margin = simpledialog.askfloat(
            "Crop Margins",
            "Margin to remove from every side, in PDF points:",
            minvalue=0,
            parent=self,
        )
        if margin is None:
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                for page in doc:
                    rect = page.rect
                    crop = fitz.Rect(
                        rect.x0 + margin,
                        rect.y0 + margin,
                        rect.x1 - margin,
                        rect.y1 - margin,
                    )
                    if crop.width <= 20 or crop.height <= 20:
                        raise ValueError("Crop margin is too large.")
                    page.set_cropbox(crop)
                self.save_pdf_document(doc)
            self.render_pdf()
        except (ValueError, RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Crop failed", f"Could not crop PDF:\n{error}")

    def open_page_layout_tools(self):
        if not self.has_pdf():
            return

        window = ctk.CTkToplevel(self)
        window.title("Page Layout")
        window.geometry("380x270")
        window.resizable(False, False)

        size_label = ctk.CTkLabel(window, text="Page size")
        size_label.pack(anchor="w", padx=20, pady=(18, 4))

        size_menu = ctk.CTkOptionMenu(
            window,
            values=["Letter", "A4", "Legal"],
            width=180,
        )
        size_menu.set("Letter")
        size_menu.pack(anchor="w", padx=20, pady=(0, 10))

        def apply_size():
            self.apply_page_size(size_menu.get())
            window.destroy()

        apply_btn = ctk.CTkButton(window, text="Apply Page Size", command=apply_size)
        apply_btn.pack(fill="x", padx=20, pady=8)

        info = ctk.CTkLabel(
            window,
            text=(
                "PDF page size is editable here.\n"
                "Staff size and spacing require exporter settings\n"
                "before the PDF is regenerated."
            ),
            justify="left",
            anchor="w",
        )
        info.pack(fill="x", padx=20, pady=(10, 0))
        window.transient(self.winfo_toplevel())
        window.focus()

    def apply_page_size(self, size_name):
        sizes = {
            "Letter": (612, 792),
            "A4": (595, 842),
            "Legal": (612, 1008),
        }
        width, height = sizes.get(size_name, sizes["Letter"])

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                for page in doc:
                    page.set_mediabox(fitz.Rect(0, 0, width, height))
                self.save_pdf_document(doc)
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Layout failed", f"Could not update page layout:\n{error}")

    def add_page_numbers(self):
        if not self.has_pdf():
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                for index, page in enumerate(doc, start=1):
                    point = fitz.Point(page.rect.width / 2 - 18, page.rect.height - 24)
                    annot = page.add_freetext_annot(
                        fitz.Rect(point.x, point.y - 12, point.x + 50, point.y + 8),
                        str(index),
                        fontsize=9,
                        text_color=(0, 0, 0),
                    )
                    annot.set_info(content="NavaTune page number")
                    annot.update()
                self.save_pdf_document(doc)
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Page numbers failed", f"Could not add page numbers:\n{error}")

    def remove_page_number_annotations(self):
        if not self.has_pdf():
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                for page in doc:
                    for annot in list(page.annots() or []):
                        if annot.info.get("content") == "NavaTune page number":
                            page.delete_annot(annot)
                self.save_pdf_document(doc)
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Remove failed", f"Could not remove page numbers:\n{error}")

    def add_watermark(self):
        if not self.has_pdf():
            return

        text = simpledialog.askstring(
            "Watermark / Signature",
            "Text to place on every page:",
            parent=self,
        )
        if not text:
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                for page in doc:
                    rect = page.rect
                    page.insert_text(
                        fitz.Point(rect.width - 160, rect.height - 28),
                        text,
                        fontsize=11,
                        color=(0.35, 0.35, 0.35),
                    )
                self.save_pdf_document(doc)
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Watermark failed", f"Could not add watermark:\n{error}")

    def import_existing_pdf(self):
        input_path = filedialog.askopenfilename(
            title="Import Existing PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if input_path:
            self.load_pdf(input_path)

    def toggle_review_panel(self):
        if self.review_enabled.get():
            self.reviewer_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
            self.viewer_panel.grid(row=0, column=1, sticky="nsew")
            self.main_panel.grid_columnconfigure(0, weight=0)
            self.main_panel.grid_columnconfigure(1, weight=1)
            self.horizontal_scrollbar.grid_configure(padx=(280, 10))
            self.render_review_panel()
        else:
            self.reviewer_panel.grid_remove()
            self.viewer_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.main_panel.grid_columnconfigure(0, weight=1)
            self.main_panel.grid_columnconfigure(1, weight=0)
            self.horizontal_scrollbar.grid_configure(padx=(10, 10))

        self.after(20, self.update_scroll_region)

    def update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.update_current_page_from_scroll()

    def on_canvas_resize(self, _event=None):
        if self.fit_mode and self.pdf_path:
            self.apply_fit_mode()

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        widget.bind("<Button-4>", self._on_linux_scroll_up)
        widget.bind("<Button-5>", self._on_linux_scroll_down)
        widget.bind("<Shift-Button-4>", self._on_linux_scroll_left)
        widget.bind("<Shift-Button-5>", self._on_linux_scroll_right)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(self._wheel_units(event.delta), "units")
        self.after(10, self.update_current_page_from_scroll)

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(self._wheel_units(event.delta), "units")

    def _on_linux_scroll_up(self, _event):
        self.canvas.yview_scroll(-3, "units")
        self.after(10, self.update_current_page_from_scroll)

    def _on_linux_scroll_down(self, _event):
        self.canvas.yview_scroll(3, "units")
        self.after(10, self.update_current_page_from_scroll)

    def _on_linux_scroll_left(self, _event):
        self.canvas.xview_scroll(-3, "units")

    def _on_linux_scroll_right(self, _event):
        self.canvas.xview_scroll(3, "units")

    def _wheel_units(self, delta):
        if delta == 0:
            return 0

        return -1 * int(delta / abs(delta)) * max(1, abs(delta) // 120)

    def set_review_context(
        self,
        notes=None,
        bpm=None,
        time_signature=None,
        tonality=None,
        score_metadata=None,
    ):
        self.notes = notes or []
        self.review_context = {
            "bpm": bpm,
            "time_signature": time_signature,
            "tonality": tonality,
            "score_metadata": score_metadata,
        }
        self.render_review_panel()

    def load_pdf(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_undo_stack.clear()
        self.pdf_redo_stack.clear()
        self.before_edit_pdf_bytes = None
        self.render_pdf()
        self.render_review_panel()

    def render_pdf(self):
        self.clear_preview()

        if not self.pdf_path or not os.path.exists(self.pdf_path):
            self.empty_label = ctk.CTkLabel(self.preview_frame, text="No sheet preview yet")
            self.empty_label.pack(padx=10, pady=10)
            self.page_count = 0
            self.update_controls()
            return

        with fitz.open(self.pdf_path) as doc:
            self.page_count = doc.page_count
            if self.page_count == 0:
                self.update_controls()
                return

            self.current_page = min(max(1, self.current_page), max(1, self.page_count))
            self.render_page(doc.load_page(self.current_page - 1), self.current_page)

            for index, page in enumerate(doc, start=1):
                self.render_thumbnail(page, index)

        self.update_controls()
        self.after(50, self.update_scroll_region)

    def render_page(self, page, page_number):
        self.clear_rendered_pages()
        pix = page.get_pixmap(matrix=fitz.Matrix(self.render_scale(), self.render_scale()))
        image = self.pixmap_to_image(pix)
        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size,
        )
        self.page_images.append(ctk_image)

        page_frame = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        page_frame.pack(pady=(0, 18))
        self.page_frames.append(page_frame)
        self._bind_mousewheel(page_frame)

        label = ctk.CTkLabel(page_frame, text="", image=ctk_image)
        label.pack()
        self._bind_mousewheel(label)
        label.bind("<ButtonPress-1>", self.on_pdf_mouse_down)
        label.bind("<B1-Motion>", self.on_pdf_mouse_drag)
        label.bind("<ButtonRelease-1>", self.on_pdf_mouse_up)
        self.page_labels.append(label)
        self.active_page_label = label

        if self.show_measure_overlay.get():
            self.render_measure_overlay(page_frame, image.size, page_number)

        number_label = ctk.CTkLabel(page_frame, text=f"Page {page_number}")
        number_label.pack(pady=(4, 0))

    def render_thumbnail(self, page, page_number):
        pix = page.get_pixmap(matrix=fitz.Matrix(0.18, 0.18))
        image = self.pixmap_to_image(pix)
        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size,
        )
        self.thumbnail_images.append(ctk_image)

        thumb_btn = ctk.CTkButton(
            self.thumbnails_frame,
            text=f"Page {page_number}",
            image=ctk_image,
            compound="top",
            command=lambda page_index=page_number: self.go_to_page(page_index),
            width=95,
        )
        thumb_btn.pack(padx=5, pady=5)

    def pixmap_to_image(self, pix):
        mode = "RGBA" if pix.alpha else "RGB"
        return Image.frombytes(mode, [pix.width, pix.height], pix.samples)

    def on_pdf_mouse_down(self, event):
        if not self.has_pdf():
            return

        mode = self.annotation_mode.get()
        self.drag_start = (event.x, event.y)
        self.freehand_points = [(event.x, event.y)]

        if mode == "Text":
            self.add_text_annotation(event.x, event.y)
        elif mode == "Stamp":
            self.add_stamp_annotation(event.x, event.y)
        elif mode == "Eraser":
            self.erase_annotation_at(event.x, event.y)
        elif mode == "Measure":
            self.open_measure_from_click(event.x, event.y)

    def on_pdf_mouse_drag(self, event):
        if self.annotation_mode.get() == "Pen":
            self.freehand_points.append((event.x, event.y))

    def on_pdf_mouse_up(self, event):
        if not self.has_pdf() or not self.drag_start:
            return

        mode = self.annotation_mode.get()
        start_x, start_y = self.drag_start
        end_x, end_y = event.x, event.y
        self.drag_start = None

        if mode == "Highlight":
            self.add_rect_annotation(start_x, start_y, end_x, end_y, "highlight")
        elif mode == "Rectangle":
            self.add_rect_annotation(start_x, start_y, end_x, end_y, "rectangle")
        elif mode == "Circle":
            self.add_rect_annotation(start_x, start_y, end_x, end_y, "circle")
        elif mode == "Arrow":
            self.add_arrow_annotation(start_x, start_y, end_x, end_y)
        elif mode == "Pen" and len(self.freehand_points) > 1:
            self.add_pen_annotation(self.freehand_points)

        self.freehand_points = []

    def add_text_annotation(self, x, y):
        text = simpledialog.askstring("Text Note", "Text to add:", parent=self)
        if not text:
            return

        point = self.event_to_pdf_point(x, y)
        rect = fitz.Rect(point.x, point.y, point.x + 150, point.y + 44)

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                annot = page.add_freetext_annot(
                    rect,
                    text,
                    fontsize=10,
                    text_color=(0, 0, 0),
                    fill_color=(1, 1, 0.82),
                )
                annot.update()
                self.save_pdf_document(doc)
            self.render_current_page()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Annotation failed", f"Could not add text note:\n{error}")

    def add_stamp_annotation(self, x, y):
        label = self.stamp_menu.get()
        point = self.event_to_pdf_point(x, y)
        rect = fitz.Rect(point.x, point.y, point.x + 92, point.y + 28)

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                annot = page.add_freetext_annot(
                    rect,
                    label,
                    fontsize=12,
                    text_color=(1, 1, 1),
                    fill_color=self.annotation_rgb(),
                )
                annot.set_border(width=0)
                annot.update()
                self.save_pdf_document(doc)
            self.render_current_page()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Stamp failed", f"Could not add stamp:\n{error}")

    def add_rect_annotation(self, start_x, start_y, end_x, end_y, kind):
        rect = self.event_rect_to_pdf_rect(start_x, start_y, end_x, end_y)
        if rect.width < 3 or rect.height < 3:
            return

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                if kind == "highlight":
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=self.annotation_rgb())
                elif kind == "circle":
                    annot = page.add_circle_annot(rect)
                    annot.set_colors(stroke=self.annotation_rgb())
                    annot.set_border(width=1.5)
                else:
                    annot = page.add_rect_annot(rect)
                    annot.set_colors(stroke=self.annotation_rgb())
                    annot.set_border(width=1.5)
                annot.update()
                self.save_pdf_document(doc)
            self.render_current_page()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Annotation failed", f"Could not add annotation:\n{error}")

    def add_arrow_annotation(self, start_x, start_y, end_x, end_y):
        start = self.event_to_pdf_point(start_x, start_y)
        end = self.event_to_pdf_point(end_x, end_y)

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                annot = page.add_line_annot(start, end)
                annot.set_colors(stroke=self.annotation_rgb())
                annot.set_border(width=1.8)
                annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_CLOSED_ARROW)
                annot.update()
                self.save_pdf_document(doc)
            self.render_current_page()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Arrow failed", f"Could not add arrow:\n{error}")

    def add_pen_annotation(self, points):
        pdf_points = [self.event_to_pdf_point(x, y) for x, y in points]

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                shape = page.new_shape()
                shape.draw_polyline(pdf_points)
                shape.finish(color=self.annotation_rgb(), width=1.5)
                shape.commit()
                self.save_pdf_document(doc)
            self.render_current_page()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Pen failed", f"Could not draw on PDF:\n{error}")

    def erase_annotation_at(self, x, y):
        point = self.event_to_pdf_point(x, y)
        hit = fitz.Rect(point.x - 8, point.y - 8, point.x + 8, point.y + 8)

        try:
            self.push_pdf_undo_state()
            removed = False
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(self.current_page - 1)
                for annot in list(page.annots() or []):
                    if annot.rect.intersects(hit):
                        page.delete_annot(annot)
                        removed = True
                        break
                if not removed:
                    self.discard_failed_pdf_undo()
                    return
                self.save_pdf_document(doc)
            self.render_current_page()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Erase failed", f"Could not erase annotation:\n{error}")

    def open_measure_from_click(self, x, _y):
        measure_count = self.measure_count()
        if not measure_count:
            return

        page_start, page_end = self.measure_range_for_page(self.current_page)
        page_measure_count = max(1, page_end - page_start + 1)
        image_width = max(1, self.active_page_label.winfo_width() if self.active_page_label else 1)
        measure_offset = min(page_measure_count - 1, max(0, int(x / image_width * page_measure_count)))
        self.open_measure_editor(page_start + measure_offset)

    def render_measure_overlay(self, page_frame, image_size, page_number):
        page_start, page_end = self.measure_range_for_page(page_number)
        if page_end < page_start:
            return

        overlay = ctk.CTkFrame(page_frame, fg_color="transparent")
        overlay.place(relx=0.5, y=16, anchor="n", relwidth=0.92)

        for measure_number in range(page_start, page_end + 1):
            label = ctk.CTkLabel(
                overlay,
                text=str(measure_number),
                width=max(24, int(image_size[0] * 0.04)),
                height=20,
                fg_color="#1f2933",
                text_color="#ffffff",
                corner_radius=4,
            )
            label.pack(side="left", padx=2)

    def open_music_tools(self):
        window = ctk.CTkToplevel(self)
        window.title("Music Editing Tools")
        window.geometry("380x420")
        window.resizable(False, False)

        actions = [
            ("Edit Score Details", self.open_score_details),
            ("Edit Notes", self.open_notes_editor),
            ("Edit Current Measure", lambda: self.open_measure_editor(self.current_measure_guess())),
            ("Mark Current Measure Needs Correction", self.mark_current_measure_needs_correction),
            ("Add Current Measure Comment", self.add_current_measure_comment),
            ("Quantize Rhythm", self.quantize_rhythm),
            ("Transpose Score", self.transpose_score),
            ("Regenerate PDF", self.refresh_preview),
        ]
        for text, command in actions:
            button = ctk.CTkButton(window, text=text, command=command, width=260)
            button.pack(fill="x", padx=20, pady=(14 if text == "Edit Score Details" else 5, 5))

        info = ctk.CTkLabel(
            window,
            text=(
                "Title, composer, key, tempo, and time signature\n"
                "are edited through Score Details and the top toolbar."
            ),
            justify="left",
            anchor="w",
        )
        info.pack(fill="x", padx=20, pady=(12, 0))
        window.transient(self.winfo_toplevel())
        window.focus()

    def mark_current_measure_needs_correction(self):
        self.add_measure_stamp(self.current_measure_guess(), "Needs correction")

    def add_current_measure_comment(self):
        measure = self.current_measure_guess()
        comment = simpledialog.askstring(
            "Measure Comment",
            f"Comment for measure {measure}:",
            parent=self,
        )
        if comment:
            self.add_measure_stamp(measure, comment)

    def add_measure_stamp(self, measure_number, text):
        if not self.has_pdf():
            return

        target_page = self.page_for_measure(measure_number)
        page_start, page_end = self.measure_range_for_page(target_page)
        page_measure_count = max(1, page_end - page_start + 1)
        offset = min(page_measure_count - 1, max(0, measure_number - page_start))

        try:
            self.push_pdf_undo_state()
            with fitz.open(self.pdf_path) as doc:
                page = doc.load_page(target_page - 1)
                width = page.rect.width / page_measure_count
                x0 = 18 + offset * width
                rect = fitz.Rect(x0, 18, min(page.rect.width - 18, x0 + 120), 48)
                annot = page.add_freetext_annot(
                    rect,
                    text,
                    fontsize=9,
                    text_color=(1, 1, 1),
                    fill_color=(1, 0.2, 0.2),
                )
                annot.update()
                self.save_pdf_document(doc)
            self.current_page = target_page
            self.render_pdf()
        except (RuntimeError, OSError) as error:
            self.discard_failed_pdf_undo()
            messagebox.showerror("Measure mark failed", f"Could not mark measure:\n{error}")

    def quantize_rhythm(self):
        if not self.notes:
            return

        quarter = self.quarter_note_seconds()
        grid = quarter / 4
        if grid <= 0:
            return

        for note in self.notes:
            note.start_time = round(note.start_time / grid) * grid
            note.duration = max(grid, round(note.duration / grid) * grid)

        self.notify_notes_changed()

    def transpose_score(self):
        if not self.notes:
            return

        semitones = simpledialog.askinteger(
            "Transpose Score",
            "Semitones to transpose, e.g. 2 or -1:",
            parent=self,
        )
        if semitones is None:
            return

        names = self.chromatic_pitch_names()
        index_by_name = {name: index for index, name in enumerate(names)}

        for note in self.notes:
            if note.is_rest():
                continue
            clean_name = note.name.strip().replace("♯", "#").replace("♭", "b")
            if clean_name not in index_by_name:
                continue
            next_index = index_by_name[clean_name] + semitones
            if 0 <= next_index < len(names):
                note.name = names[next_index]

        self.notify_notes_changed()

    def notify_notes_changed(self):
        self.notes = sorted(self.notes, key=lambda note: note.start_time)
        if self.on_notes_changed:
            self.on_notes_changed(self.notes)
        else:
            self.render_review_panel()
        self.refresh_preview()

    def current_measure_guess(self):
        page_start, _page_end = self.measure_range_for_page(self.current_page)
        return max(1, page_start)

    def chromatic_pitch_names(self):
        pitch_classes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return [f"{pitch}{octave}" for octave in range(0, 9) for pitch in pitch_classes]

    def has_pdf(self):
        return bool(self.pdf_path and os.path.exists(self.pdf_path) and self.page_count > 0)

    def save_pdf_document(self, doc):
        output_dir = os.path.dirname(os.path.abspath(self.pdf_path)) or "."
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=output_dir,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name

        try:
            doc.save(temp_path, garbage=4, deflate=True)
            os.replace(temp_path, self.pdf_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def push_pdf_undo_state(self):
        if not self.has_pdf():
            return

        with open(self.pdf_path, "rb") as pdf_file:
            current = pdf_file.read()

        if self.before_edit_pdf_bytes is None:
            self.before_edit_pdf_bytes = current

        self.pdf_undo_stack.append(current)
        if len(self.pdf_undo_stack) > self.MAX_PDF_HISTORY:
            self.pdf_undo_stack.pop(0)
        self.pdf_redo_stack.clear()
        self.update_controls()

    def discard_failed_pdf_undo(self):
        if self.pdf_undo_stack:
            self.pdf_undo_stack.pop()
        self.update_controls()

    def undo_pdf_edit(self):
        if not self.pdf_undo_stack or not self.has_pdf():
            return

        with open(self.pdf_path, "rb") as pdf_file:
            self.pdf_redo_stack.append(pdf_file.read())

        previous = self.pdf_undo_stack.pop()
        with open(self.pdf_path, "wb") as pdf_file:
            pdf_file.write(previous)
        self.render_pdf()

    def redo_pdf_edit(self):
        if not self.pdf_redo_stack or not self.has_pdf():
            return

        with open(self.pdf_path, "rb") as pdf_file:
            self.pdf_undo_stack.append(pdf_file.read())

        next_state = self.pdf_redo_stack.pop()
        with open(self.pdf_path, "wb") as pdf_file:
            pdf_file.write(next_state)
        self.render_pdf()

    def compare_before_after(self):
        if not self.before_edit_pdf_bytes or not self.has_pdf():
            messagebox.showinfo("Compare", "No earlier PDF edit state is available yet.")
            return

        window = ctk.CTkToplevel(self)
        window.title("Before / After PDF")
        window.geometry("1100x720")
        window.grid_columnconfigure((0, 1), weight=1)
        window.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(window, text="Before", font=("Arial", 16, "bold")).grid(row=0, column=0, pady=8)
        ctk.CTkLabel(window, text="After", font=("Arial", 16, "bold")).grid(row=0, column=1, pady=8)

        before_frame = ctk.CTkScrollableFrame(window)
        after_frame = ctk.CTkScrollableFrame(window)
        before_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
        after_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))

        self.render_pdf_bytes_into_frame(self.before_edit_pdf_bytes, before_frame)
        with open(self.pdf_path, "rb") as pdf_file:
            self.render_pdf_bytes_into_frame(pdf_file.read(), after_frame)

        window.transient(self.winfo_toplevel())
        window.focus()

    def render_pdf_bytes_into_frame(self, pdf_bytes, frame):
        images = []
        frame._preview_images = images
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.page_count == 0:
                return
            page = doc.load_page(min(self.current_page - 1, doc.page_count - 1))
            pix = page.get_pixmap(matrix=fitz.Matrix(0.95, 0.95))
            image = self.pixmap_to_image(pix)
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
            images.append(ctk_image)
            ctk.CTkLabel(frame, text="", image=ctk_image).pack(padx=8, pady=8)

    def parse_page_list(self, text, require_all=False):
        pages = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start_text, end_text = part.split("-", 1)
                start = int(start_text)
                end = int(end_text)
                if end < start:
                    raise ValueError("Page ranges must be ascending.")
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))

        if not pages:
            raise ValueError("No pages selected.")
        if any(page < 1 or page > self.page_count for page in pages):
            raise ValueError(f"Pages must be between 1 and {self.page_count}.")
        if require_all and sorted(pages) != list(range(1, self.page_count + 1)):
            raise ValueError("Reorder must include every page exactly once.")

        return pages

    def event_to_pdf_point(self, x, y):
        scale = self.render_scale()
        return fitz.Point(x / scale, y / scale)

    def event_rect_to_pdf_rect(self, start_x, start_y, end_x, end_y):
        start = self.event_to_pdf_point(start_x, start_y)
        end = self.event_to_pdf_point(end_x, end_y)
        return fitz.Rect(
            min(start.x, end.x),
            min(start.y, end.y),
            max(start.x, end.x),
            max(start.y, end.y),
        )

    def annotation_rgb(self):
        return self.ANNOT_COLORS.get(self.annotation_color.get(), (1, 0.92, 0.2))

    def measure_range_for_page(self, page_number):
        measure_count = self.measure_count()
        if not measure_count:
            return 1, 0

        pages = max(1, self.page_count)
        start = math.floor((page_number - 1) * measure_count / pages) + 1
        end = math.floor(page_number * measure_count / pages)
        return start, max(start, end)

    def clear_preview(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()

        self.page_images.clear()
        self.thumbnail_images.clear()
        self.page_frames.clear()
        self.page_labels.clear()

    def clear_rendered_pages(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        self.page_images.clear()
        self.page_frames.clear()
        self.page_labels.clear()

    def render_current_page(self):
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            return

        with fitz.open(self.pdf_path) as doc:
            if doc.page_count == 0:
                return

            self.page_count = doc.page_count
            self.current_page = min(max(1, self.current_page), self.page_count)
            self.render_page(doc.load_page(self.current_page - 1), self.current_page)

        self.update_controls()
        self.after(20, self.update_scroll_region)

    def render_scale(self):
        return self.BASE_RENDER_SCALE * self.zoom

    def zoom_in(self):
        self.fit_mode = None
        self.set_zoom(self.zoom + self.ZOOM_STEP)

    def zoom_out(self):
        self.fit_mode = None
        self.set_zoom(self.zoom - self.ZOOM_STEP)

    def reset_zoom(self):
        self.fit_mode = None
        self.set_zoom(1.0)

    def fit_width(self):
        self.fit_mode = "width"
        self.apply_fit_mode()

    def fit_page(self):
        self.fit_mode = "page"
        self.apply_fit_mode()

    def apply_fit_mode(self):
        if not self.pdf_path:
            return

        page_size = self.first_page_size()
        if not page_size:
            return

        page_width, page_height = page_size
        available_width = max(240, self.canvas.winfo_width() - 30)
        available_height = max(240, self.canvas.winfo_height() - 30)

        if self.fit_mode == "width":
            zoom = available_width / (page_width * self.BASE_RENDER_SCALE)
        elif self.fit_mode == "page":
            zoom = min(
                available_width / (page_width * self.BASE_RENDER_SCALE),
                available_height / (page_height * self.BASE_RENDER_SCALE),
            )
        else:
            return

        self.set_zoom(zoom)

    def first_page_size(self):
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            return None

        with fitz.open(self.pdf_path) as doc:
            if doc.page_count == 0:
                return None

            rect = doc.load_page(0).rect
            return rect.width, rect.height

    def set_zoom(self, zoom):
        new_zoom = min(self.MAX_ZOOM, max(self.MIN_ZOOM, zoom))

        if abs(new_zoom - self.zoom) < 0.01:
            self.update_controls()
            return

        current_page = self.current_page
        self.zoom = new_zoom
        self.render_pdf()
        self.after(80, lambda: self.go_to_page(current_page))

    def previous_page(self):
        self.go_to_page(self.current_page - 1)

    def next_page(self):
        self.go_to_page(self.current_page + 1)

    def go_to_page(self, page_number):
        if self.page_count == 0:
            return

        next_page = min(max(1, page_number), self.page_count)
        if next_page != self.current_page:
            self.current_page = next_page
            self.render_current_page()

        self.canvas.yview_moveto(0)
        self.update_controls()

    def update_current_page_from_scroll(self):
        if self.page_count:
            self.update_controls()

    def update_controls(self):
        self.page_label.configure(text=f"Page {self.current_page}/{self.page_count}")
        self.zoom_label.configure(text=f"{int(self.zoom * 100)}%")
        has_pdf = self.page_count > 0
        self.prev_btn.configure(state="normal" if has_pdf and self.current_page > 1 else "disabled")
        self.next_btn.configure(state="normal" if has_pdf and self.current_page < self.page_count else "disabled")
        self.open_btn.configure(state="normal" if has_pdf else "disabled")
        for button_name in [
            "save_as_btn",
            "export_image_btn",
            "print_btn",
            "rotate_left_btn",
            "rotate_right_btn",
            "delete_page_btn",
            "pages_btn",
            "advanced_btn",
            "compare_btn",
        ]:
            if hasattr(self, button_name):
                getattr(self, button_name).configure(state="normal" if has_pdf else "disabled")

        if hasattr(self, "delete_page_btn"):
            self.delete_page_btn.configure(
                state="normal" if has_pdf and self.page_count > 1 else "disabled"
            )
        if hasattr(self, "pdf_undo_btn"):
            self.pdf_undo_btn.configure(state="normal" if self.pdf_undo_stack else "disabled")
        if hasattr(self, "pdf_redo_btn"):
            self.pdf_redo_btn.configure(state="normal" if self.pdf_redo_stack else "disabled")

    def render_review_panel(self):
        if not self.review_enabled.get():
            return

        for button in self.issue_buttons:
            button.destroy()
        self.issue_buttons.clear()
        for button in self.measure_buttons:
            button.destroy()
        self.measure_buttons.clear()

        issues = self.review_issues()
        status_text = "Ready to export" if not issues else "Needs review"
        status_color = "#7ed957" if not issues else "#f5a623"
        self.status_label.configure(text=status_text, text_color=status_color)
        self.stats_label.configure(text=self.review_stats_text())

        if not issues:
            ok_label = ctk.CTkLabel(
                self.issues_frame,
                text="No issues found",
                text_color="#7ed957",
                justify="left",
                anchor="w",
            )
            ok_label.pack(fill="x", pady=2)
            self.issue_buttons.append(ok_label)
        else:
            for issue in issues:
                button = ctk.CTkButton(
                    self.issues_frame,
                    text=issue["text"],
                    command=lambda target_page=issue.get("page", 1): self.go_to_page(target_page),
                    anchor="w",
                    width=220,
                )
                button.pack(fill="x", pady=3)
                self.issue_buttons.append(button)

        self.render_measure_buttons()

    def render_measure_buttons(self):
        measure_count = self.measure_count()

        if not measure_count:
            label = ctk.CTkLabel(
                self.measures_frame,
                text="No measures",
                justify="left",
                anchor="w",
            )
            label.pack(fill="x", pady=2)
            self.measure_buttons.append(label)
            return

        for measure_number in range(1, measure_count + 1):
            notes = self.notes_for_measure(measure_number)
            note_count = sum(1 for note in notes if not note.is_rest())
            rest_count = len(notes) - note_count
            button = ctk.CTkButton(
                self.measures_frame,
                text=f"Measure {measure_number}  ({note_count} notes, {rest_count} rests)",
                command=lambda number=measure_number: self.open_measure_editor(number),
                anchor="w",
                width=220,
            )
            button.pack(fill="x", pady=3)
            self.measure_buttons.append(button)

    def open_measure_editor(self, measure_number):
        measure_notes = self.notes_for_measure(measure_number)
        measure_state = {"notes": list(measure_notes)}

        def handle_measure_notes_changed(edited_notes):
            self.replace_measure_notes(
                measure_number,
                measure_state["notes"],
                edited_notes,
            )
            measure_state["notes"] = list(edited_notes)

        window = ctk.CTkToplevel(self)
        window.title(f"Edit Measure {measure_number}")
        window.geometry("1050x620")
        window.minsize(760, 420)
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)
        window.grid_columnconfigure(1, weight=0)

        editor = NotesEditor(
            window,
            on_notes_changed=handle_measure_notes_changed,
            get_quarter_note_seconds=self.quarter_note_seconds,
            get_time_signature=lambda: self.review_context.get("time_signature") or "4/4",
            get_default_start_time=lambda: self.measure_start_time(measure_number),
        )
        editor.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        editor.set_notes(measure_state["notes"])

        side_panel = ctk.CTkFrame(window)
        side_panel.grid(row=0, column=1, sticky="ns", padx=(5, 10), pady=10)

        title = ctk.CTkLabel(
            side_panel,
            text=f"Measure {measure_number}",
            font=("Arial", 18, "bold"),
        )
        title.pack(anchor="w", padx=12, pady=(12, 6))

        info = ctk.CTkLabel(
            side_panel,
            text=(
                "Edit notes on the left.\n"
                "Use Apply Changes to update\n"
                "this measure in the score."
            ),
            justify="left",
            anchor="w",
        )
        info.pack(fill="x", padx=12, pady=(0, 12))

        refresh_btn = ctk.CTkButton(
            side_panel,
            text="Refresh PDF",
            command=self.refresh_preview,
            width=160,
        )
        refresh_btn.pack(fill="x", padx=12, pady=5)

        close_btn = ctk.CTkButton(
            side_panel,
            text="Close",
            command=window.destroy,
            width=160,
        )
        close_btn.pack(fill="x", padx=12, pady=5)

        window.transient(self.winfo_toplevel())
        window.focus()

    def replace_measure_notes(self, measure_number, original_measure_notes, edited_notes):
        original_ids = {id(note) for note in original_measure_notes}
        remaining_notes = [
            note for note in self.notes
            if id(note) not in original_ids
        ]
        self.notes = sorted(
            remaining_notes + list(edited_notes),
            key=lambda note: note.start_time,
        )

        if self.on_notes_changed:
            self.on_notes_changed(self.notes)
        else:
            self.render_review_panel()

    def notes_for_measure(self, measure_number):
        return [
            note for note in self.notes
            if self.measure_for_time(note.start_time) == measure_number
        ]

    def measure_start_time(self, measure_number):
        measure_index = max(0, measure_number - 1)
        return measure_index * self.beats_per_bar() * self.quarter_note_seconds()

    def review_stats_text(self):
        note_count = sum(1 for note in self.notes if not note.is_rest())
        rest_count = len(self.notes) - note_count
        measure_count = self.measure_count()
        bpm = self.review_context.get("bpm") or "-"
        time_signature = self.review_context.get("time_signature") or "-"
        tonality = tonality_label(self.review_context.get("tonality")) if self.review_context.get("tonality") else "-"
        page_count = self.page_count or 0

        return (
            f"Notes: {note_count}\n"
            f"Rests: {rest_count}\n"
            f"Measures: {measure_count}\n"
            f"Time: {time_signature}\n"
            f"Tempo: {bpm} BPM\n"
            f"Tonality: {tonality}\n"
            f"Pages: {page_count}"
        )

    def review_issues(self):
        issues = []
        metadata = self.review_context.get("score_metadata")

        if not self.notes:
            issues.append({"text": "Empty score", "page": 1})

        if metadata:
            if not getattr(metadata, "title", "").strip() or metadata.title.strip() == "Untitled":
                issues.append({"text": "Missing title", "page": 1})
            if not getattr(metadata, "composer", "").strip():
                issues.append({"text": "Missing composer", "page": 1})

        outside_count = sum(
            1
            for note in self.notes
            if not note.is_rest() and self.is_outside_staff_range(note.name)
        )
        if outside_count:
            issues.append({"text": f"{outside_count} notes outside staff range", "page": 1})

        for measure, count in self.dense_measures():
            issues.append({
                "text": f"Dense measure {measure}: {count} notes",
                "page": self.page_for_measure(measure),
            })

        for measure, gap in self.awkward_gaps():
            issues.append({
                "text": f"Long gap/rest in measure {measure}: {gap:.1f} beats",
                "page": self.page_for_measure(measure),
            })

        return issues

    def measure_count(self):
        if not self.notes:
            return 0

        beats_per_bar = self.beats_per_bar()
        quarter_seconds = self.quarter_note_seconds()
        end_time = max(note.start_time + note.duration for note in self.notes)
        total_beats = end_time / quarter_seconds
        return max(1, math.ceil(total_beats / beats_per_bar))

    def dense_measures(self):
        counts = {}

        for note in self.notes:
            if note.is_rest():
                continue

            measure = self.measure_for_time(note.start_time)
            counts[measure] = counts.get(measure, 0) + 1

        return [
            (measure, count)
            for measure, count in sorted(counts.items())
            if count > self.DENSE_MEASURE_LIMIT
        ]

    def awkward_gaps(self):
        awkward = []
        quarter_seconds = self.quarter_note_seconds()
        long_gap_seconds = quarter_seconds * self.AWKWARD_GAP_BEATS
        sorted_notes = sorted(self.notes, key=lambda note: note.start_time)

        for note in sorted_notes:
            if note.is_rest() and note.duration >= long_gap_seconds:
                awkward.append((
                    self.measure_for_time(note.start_time),
                    note.duration / quarter_seconds,
                ))

        for index in range(len(sorted_notes) - 1):
            current = sorted_notes[index]
            next_note = sorted_notes[index + 1]
            gap = next_note.start_time - (current.start_time + current.duration)
            if gap >= long_gap_seconds:
                awkward.append((self.measure_for_time(current.start_time), gap / quarter_seconds))

        return awkward

    def is_outside_staff_range(self, note_name):
        match = NOTE_PATTERN.match(
            note_name.strip().replace("♯", "#").replace("♭", "b")
        )
        if not match:
            return True

        letter, accidental, octave = match.groups()
        midi = (int(octave) + 1) * 12 + PITCH_CLASS_ORDER.get(letter + accidental, 0)
        return midi < 36 or midi > 84

    def measure_for_time(self, start_time):
        beats = start_time / self.quarter_note_seconds()
        return int(beats // self.beats_per_bar()) + 1

    def page_for_measure(self, measure):
        if self.page_count <= 1:
            return 1

        measure_count = max(1, self.measure_count())
        return min(self.page_count, max(1, math.ceil(measure / measure_count * self.page_count)))

    def beats_per_bar(self):
        time_signature = self.review_context.get("time_signature") or "4/4"

        try:
            numerator, denominator = time_signature.split("/", 1)
            return max(1, int(numerator)) * (4 / max(1, int(denominator)))
        except ValueError:
            return 4

    def quarter_note_seconds(self):
        bpm = self.review_context.get("bpm") or 60
        return 60.0 / max(1, float(bpm))
