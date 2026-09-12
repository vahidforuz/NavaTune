import copy
import re

import customtkinter as ctk
from models.detected_note import DetectedNote


PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PITCHES = [f"{pitch}{octave}" for octave in range(2, 6) for pitch in PITCH_CLASSES]
FLAT_TO_SHARP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}
NOTE_PATTERN = re.compile(r"^[A-G](?:#|b)?[0-8]$")


class NotesEditor(ctk.CTkFrame):
    TABLE_COLUMN_COUNT = 10
    DURATION_MULTIPLIERS = {
        "1": 4.0,
        "1 dotted": 6.0,
        "1/2": 2.0,
        "1/2 dotted": 3.0,
        "1/4": 1.0,
        "1/4 dotted": 1.5,
        "1/8": 0.5,
        "1/8 dotted": 0.75,
        "1/16": 0.25,
    }
    MAX_HISTORY = 50

    def __init__(
        self,
        parent,
        on_notes_changed=None,
        get_quarter_note_seconds=None,
        get_time_signature=None,
    ):
        super().__init__(parent)

        self.on_notes_changed = on_notes_changed
        self.get_quarter_note_seconds = get_quarter_note_seconds
        self.get_time_signature = get_time_signature
        self.notes = []
        self.undo_stack = []
        self.redo_stack = []

        title = ctk.CTkLabel(self, text="Editable Notes", font=("Arial", 22))
        title.pack(pady=10)

        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(pady=5)

        self.undo_btn = ctk.CTkButton(
            self.actions_frame,
            text="Undo",
            width=70,
            command=self.undo,
        )
        self.undo_btn.grid(row=0, column=0, padx=5, pady=5)

        self.redo_btn = ctk.CTkButton(
            self.actions_frame,
            text="Redo",
            width=70,
            command=self.redo,
        )
        self.redo_btn.grid(row=0, column=1, padx=5, pady=5)

        self.pitch_menu = ctk.CTkOptionMenu(
            self.actions_frame,
            values=PITCHES,
            width=90,
        )
        self.pitch_menu.set("C4")
        self.pitch_menu.grid(row=0, column=2, padx=(20, 5), pady=5)

        self.note_duration_menu = ctk.CTkOptionMenu(
            self.actions_frame,
            values=list(self.DURATION_MULTIPLIERS.keys()),
            width=110,
        )
        self.note_duration_menu.set("1/4")
        self.note_duration_menu.grid(row=0, column=3, padx=5, pady=5)

        self.add_btn = ctk.CTkButton(
            self.actions_frame,
            text="Add Note",
            width=90,
            command=self.add_note,
        )
        self.add_btn.grid(row=0, column=4, padx=5, pady=5)

        self.rest_duration_menu = ctk.CTkOptionMenu(
            self.actions_frame,
            values=list(self.DURATION_MULTIPLIERS.keys()),
            width=110,
        )
        self.rest_duration_menu.set("1/4")
        self.rest_duration_menu.grid(row=0, column=5, padx=(20, 5), pady=5)

        self.add_rest_btn = ctk.CTkButton(
            self.actions_frame,
            text="Add Rest",
            width=90,
            command=self.add_rest,
        )
        self.add_rest_btn.grid(row=0, column=6, padx=5, pady=5)

        self.summary_label = ctk.CTkLabel(
            self,
            text="No notes loaded",
            font=("Arial", 13),
        )
        self.summary_label.pack(pady=(0, 5))

        self.table = ctk.CTkScrollableFrame(
            self,
            orientation="vertical",
            scrollbar_button_color="#3b8ed0",
            scrollbar_button_hover_color="#1f6aa5",
        )
        self.table.pack(fill="both", expand=True, padx=10, pady=10)

        self.draw_table()
        self.update_history_buttons()

    def draw_table(self):
        for widget in self.table.winfo_children():
            widget.destroy()

        self.update_summary()

        headers = [
            "Note/Rest",
            "Position",
            "Start (s)",
            "Duration",
            "Staff",
            "Warnings",
            "Up",
            "Down",
            "Save",
            "Delete",
        ]

        for col, text in enumerate(headers):
            label = ctk.CTkLabel(self.table, text=text, font=("Arial", 14, "bold"))
            label.grid(row=0, column=col, padx=8, pady=5)

        display_row = 1
        for index, note in enumerate(self.notes):
            self.create_note_row(display_row, note)
            display_row += 1

            current_measure = self.measure_for_time(note.start_time)
            next_note = self.notes[index + 1] if index + 1 < len(self.notes) else None
            next_measure = self.measure_for_time(next_note.start_time) if next_note else None

            if next_measure != current_measure:
                self.create_measure_divider(display_row, current_measure)
                display_row += 1

    def set_notes(self, notes):
        self.notes = notes
        self.undo_stack.clear()
        self.redo_stack.clear()

        for note in self.notes:
            if not hasattr(note, "staff"):
                note.staff = "auto"

        self.draw_table()
        self.update_history_buttons()

    def create_note_row(self, row, note):
        name_entry = ctk.CTkEntry(self.table, width=80)
        name_entry.insert(0, note.name)
        name_entry.grid(row=row, column=0, padx=5, pady=5)

        position_label = ctk.CTkLabel(
            self.table,
            text=self.format_position(note.start_time),
            width=85,
        )
        position_label.grid(row=row, column=1, padx=5, pady=5)

        start_entry = ctk.CTkEntry(self.table, width=80)
        start_entry.insert(0, f"{note.start_time:.2f}")
        start_entry.grid(row=row, column=2, padx=5, pady=5)

        duration_entry = ctk.CTkEntry(self.table, width=90)
        duration_entry.insert(0, f"{note.duration:.2f}")
        duration_entry.grid(row=row, column=3, padx=5, pady=5)

        staff_menu = ctk.CTkOptionMenu(
            self.table,
            values=["auto", "treble", "bass"],
            width=90,
        )
        staff_menu.set(getattr(note, "staff", "auto"))
        staff_menu.grid(row=row, column=4, padx=5, pady=5)

        warnings = self.note_warnings(note)
        warning_label = ctk.CTkLabel(
            self.table,
            text=", ".join(warnings) if warnings else "OK",
            text_color="#f5a623" if warnings else "#7ed957",
            width=150,
        )
        warning_label.grid(row=row, column=5, padx=5, pady=5)

        up_btn = ctk.CTkButton(
            self.table,
            text="↑",
            width=35,
            command=lambda: self.move_note(note, 1)
        )
        up_btn.grid(row=row, column=6, padx=2, pady=5)

        down_btn = ctk.CTkButton(
            self.table,
            text="↓",
            width=35,
            command=lambda: self.move_note(note, -1)
        )
        down_btn.grid(row=row, column=7, padx=2, pady=5)

        save_btn = ctk.CTkButton(
            self.table,
            text="Save",
            width=60,
            command=lambda: self.save_row(
                note,
                name_entry,
                start_entry,
                duration_entry,
                staff_menu
            )
        )
        save_btn.grid(row=row, column=8, padx=5, pady=5)

        delete_btn = ctk.CTkButton(
            self.table,
            text="Delete",
            width=70,
            command=lambda: self.delete_note(note)
        )
        delete_btn.grid(row=row, column=9, padx=5, pady=5)

    def create_measure_divider(self, row, measure_number):
        divider = ctk.CTkFrame(self.table, fg_color="transparent")
        divider.grid(
            row=row,
            column=0,
            columnspan=self.TABLE_COLUMN_COUNT,
            sticky="ew",
            padx=5,
            pady=(4, 8),
        )
        divider.grid_columnconfigure(0, weight=0)
        divider.grid_columnconfigure(1, weight=1)

        label = ctk.CTkLabel(
            divider,
            text=f"End of measure {measure_number}",
            font=("Arial", 12, "bold"),
            text_color="#9bbce3",
        )
        label.grid(row=0, column=0, padx=(0, 8), sticky="w")

        line = ctk.CTkFrame(divider, height=2, fg_color="#3b8ed0")
        line.grid(row=0, column=1, sticky="ew")

    def save_row(self, note, name_entry, start_entry, duration_entry, staff_menu):
        try:
            name = name_entry.get().strip()
            start_time = float(start_entry.get())
            duration = float(duration_entry.get())
            staff = staff_menu.get()

            self.push_undo_state()
            note.name = name
            note.start_time = start_time
            note.duration = duration
            note.staff = staff

            self.draw_table()
            self.notify_change()

        except ValueError:
            print("Invalid number")

    def move_note(self, note, direction):
        if note.is_rest():
            return

        clean_name = self.to_sharp_note_name(self.clean_note_name(note.name))

        if clean_name not in PITCHES:
            return

        index = PITCHES.index(clean_name)
        new_index = index + direction

        if 0 <= new_index < len(PITCHES):
            self.push_undo_state()
            note.name = PITCHES[new_index]

        self.draw_table()
        self.notify_change()

    def add_note(self):
        quarter_note_seconds = self.current_quarter_note_seconds()
        duration_multiplier = self.DURATION_MULTIPLIERS[self.note_duration_menu.get()]

        self.push_undo_state()
        new_note = DetectedNote(
            name=self.pitch_menu.get(),
            start_time=self.next_start_time(),
            duration=quarter_note_seconds * duration_multiplier,
            staff="auto"
        )

        self.notes.append(new_note)
        self.draw_table()
        self.notify_change()

    def add_rest(self):
        quarter_note_seconds = self.current_quarter_note_seconds()
        duration_multiplier = self.DURATION_MULTIPLIERS[self.rest_duration_menu.get()]

        self.push_undo_state()
        new_rest = DetectedNote(
            name="Rest",
            start_time=self.next_start_time(),
            duration=quarter_note_seconds * duration_multiplier,
            staff="auto",
        )

        self.notes.append(new_rest)
        self.draw_table()
        self.notify_change()

    def current_quarter_note_seconds(self):
        if self.get_quarter_note_seconds:
            return self.get_quarter_note_seconds()

        return 1.0

    def next_start_time(self):
        if not self.notes:
            return 0.0

        return max(note.start_time + note.duration for note in self.notes)

    def delete_note(self, note):
        if note in self.notes:
            self.push_undo_state()
            self.notes.remove(note)

        self.draw_table()
        self.notify_change()

    def push_undo_state(self):
        self.undo_stack.append(copy.deepcopy(self.notes))

        if len(self.undo_stack) > self.MAX_HISTORY:
            self.undo_stack.pop(0)

        self.redo_stack.clear()
        self.update_history_buttons()

    def undo(self):
        if not self.undo_stack:
            return

        self.redo_stack.append(copy.deepcopy(self.notes))
        self.notes = self.undo_stack.pop()
        self.draw_table()
        self.update_history_buttons()
        self.notify_change()

    def redo(self):
        if not self.redo_stack:
            return

        self.undo_stack.append(copy.deepcopy(self.notes))
        self.notes = self.redo_stack.pop()
        self.draw_table()
        self.update_history_buttons()
        self.notify_change()

    def update_history_buttons(self):
        if hasattr(self, "undo_btn"):
            self.undo_btn.configure(state="normal" if self.undo_stack else "disabled")

        if hasattr(self, "redo_btn"):
            self.redo_btn.configure(state="normal" if self.redo_stack else "disabled")

    def update_summary(self):
        if not hasattr(self, "summary_label"):
            return

        note_count = sum(1 for note in self.notes if not note.is_rest())
        rest_count = len(self.notes) - note_count
        warning_count = sum(1 for note in self.notes if self.note_warnings(note))
        duration = self.next_start_time()
        time_signature = self.current_time_signature()

        self.summary_label.configure(
            text=(
                f"{note_count} notes, {rest_count} rests, "
                f"{duration:.2f}s total, {time_signature}, "
                f"{warning_count} warnings"
            )
        )

    def note_warnings(self, note):
        warnings = []
        clean_name = self.clean_note_name(note.name)

        if not note.is_rest() and not self.is_supported_note_name(clean_name):
            warnings.append("Invalid pitch")

        if note.start_time < 0:
            warnings.append("Negative start")

        if note.duration <= 0:
            warnings.append("Bad duration")
        elif note.duration < self.current_quarter_note_seconds() * 0.125:
            warnings.append("Very short")

        if getattr(note, "staff", "auto") not in {"auto", "treble", "bass"}:
            warnings.append("Bad staff")

        return warnings

    def format_position(self, start_time):
        quarter_note_seconds = self.current_quarter_note_seconds()

        if quarter_note_seconds <= 0:
            return "bar 1 beat 1"

        beats_per_bar = self.current_beats_per_bar()
        total_beats = start_time / quarter_note_seconds
        bar = self.measure_for_time(start_time)
        beat = (total_beats % beats_per_bar) + 1

        return f"bar {bar} beat {beat:.2f}"

    def measure_for_time(self, start_time):
        quarter_note_seconds = self.current_quarter_note_seconds()

        if quarter_note_seconds <= 0:
            return 1

        total_beats = start_time / quarter_note_seconds
        return max(1, int(total_beats // self.current_beats_per_bar()) + 1)

    def current_beats_per_bar(self):
        numerator, denominator = self.parse_time_signature()
        return numerator * (4 / denominator)

    def parse_time_signature(self):
        try:
            numerator, denominator = self.current_time_signature().split("/", 1)
            return max(1, int(numerator)), max(1, int(denominator))
        except ValueError:
            return 4, 4

    def current_time_signature(self):
        if self.get_time_signature:
            return self.get_time_signature()

        return "4/4"

    def clean_note_name(self, note_name):
        return note_name.strip().replace("♯", "#").replace("♭", "b")

    def is_supported_note_name(self, note_name):
        if not NOTE_PATTERN.match(note_name):
            return False

        return self.to_sharp_note_name(note_name) in PITCHES

    def to_sharp_note_name(self, note_name):
        pitch_class = note_name[:-1]
        octave = note_name[-1]
        return f"{FLAT_TO_SHARP.get(pitch_class, pitch_class)}{octave}"

    def notify_change(self):
        self.update_history_buttons()
        if self.on_notes_changed:
            self.on_notes_changed(self.notes)
