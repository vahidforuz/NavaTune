import math
import os
import re
import webbrowser

import customtkinter as ctk
import fitz
import tkinter as tk
from PIL import Image

from notation.tonality import tonality_label


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

    def __init__(
        self,
        parent,
        on_edit_score_details=None,
        on_refresh_preview=None,
        on_edit_notes=None,
    ):
        super().__init__(parent)

        self.on_edit_score_details = on_edit_score_details
        self.on_refresh_preview = on_refresh_preview
        self.on_edit_notes = on_edit_notes
        self.pdf_path = None
        self.page_count = 0
        self.current_page = 1
        self.zoom = 1.0
        self.fit_mode = None
        self.notes = []
        self.review_context = {}
        self.review_enabled = tk.BooleanVar(value=True)
        self.page_images = []
        self.thumbnail_images = []
        self.page_frames = []
        self.issue_buttons = []

        self.grid_rowconfigure(1, weight=1)
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
            command=self.open_pdf_external,
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

        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))
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
        self.horizontal_scrollbar.grid(row=2, column=0, sticky="ew", padx=(280, 10), pady=(4, 10))

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
            for index, page in enumerate(doc, start=1):
                self.render_page(page, index)
                self.render_thumbnail(page, index)

        self.current_page = min(max(1, self.current_page), max(1, self.page_count))
        self.update_controls()
        self.after(50, lambda: self.go_to_page(self.current_page))

    def render_page(self, page, page_number):
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

    def clear_preview(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()

        self.page_images.clear()
        self.thumbnail_images.clear()
        self.page_frames.clear()

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
        if not self.page_frames:
            return

        self.current_page = min(max(1, page_number), self.page_count)
        target = self.page_frames[self.current_page - 1]
        self.update_scroll_region()
        scroll_bbox = self.canvas.bbox("all")

        if not scroll_bbox:
            return

        content_height = max(1, scroll_bbox[3] - scroll_bbox[1])
        y = max(0, target.winfo_y() - 8)
        self.canvas.yview_moveto(y / content_height)
        self.update_controls()

    def update_current_page_from_scroll(self):
        if not self.page_frames or self.page_count == 0:
            return

        top = self.canvas.canvasy(0)
        closest_page = 1
        closest_distance = None

        for index, frame in enumerate(self.page_frames, start=1):
            distance = abs(frame.winfo_y() - top)
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_page = index

        if closest_page != self.current_page:
            self.current_page = closest_page
            self.update_controls()

    def update_controls(self):
        self.page_label.configure(text=f"Page {self.current_page}/{self.page_count}")
        self.zoom_label.configure(text=f"{int(self.zoom * 100)}%")
        has_pdf = self.page_count > 0
        self.prev_btn.configure(state="normal" if has_pdf and self.current_page > 1 else "disabled")
        self.next_btn.configure(state="normal" if has_pdf and self.current_page < self.page_count else "disabled")
        self.open_btn.configure(state="normal" if has_pdf else "disabled")

    def render_review_panel(self):
        if not self.review_enabled.get():
            return

        for button in self.issue_buttons:
            button.destroy()
        self.issue_buttons.clear()

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
