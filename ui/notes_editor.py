import copy
import re
import tkinter as tk

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
    TABLE_COLUMN_COUNT = 11
    STAFF_OPTIONS = ["auto", "right hand", "left hand"]
    STAFF_LABEL_TO_VALUE = {
        "auto": "auto",
        "right hand": "treble",
        "left hand": "bass",
    }
    STAFF_VALUE_TO_LABEL = {
        "auto": "auto",
        "treble": "right hand",
        "bass": "left hand",
    }
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
    NOTE_VALUE_LABELS = {
        "1": "Round / whole",
        "1 dotted": "Dotted round / whole",
        "1/2": "White / half",
        "1/2 dotted": "Dotted white / half",
        "1/4": "Black / quarter",
        "1/4 dotted": "Dotted black / quarter",
        "1/8": "Croche / eighth",
        "1/8 dotted": "Dotted croche / eighth",
        "1/16": "Double croche / sixteenth",
    }
    NOTE_VALUE_OPTIONS = [
        "Round / whole",
        "Dotted round / whole",
        "White / half",
        "Dotted white / half",
        "Black / quarter",
        "Dotted black / quarter",
        "Croche / eighth",
        "Dotted croche / eighth",
        "Double croche / sixteenth",
    ]
    NOTE_VALUE_TO_DURATION_KEY = {
        "Round / whole": "1",
        "Dotted round / whole": "1 dotted",
        "White / half": "1/2",
        "Dotted white / half": "1/2 dotted",
        "Black / quarter": "1/4",
        "Dotted black / quarter": "1/4 dotted",
        "Croche / eighth": "1/8",
        "Dotted croche / eighth": "1/8 dotted",
        "Double croche / sixteenth": "1/16",
    }
    MAX_HISTORY = 50

    def __init__(
        self,
        parent,
        on_notes_changed=None,
        get_quarter_note_seconds=None,
        get_time_signature=None,
        get_default_start_time=None,
    ):
        super().__init__(parent)

        self.on_notes_changed = on_notes_changed
        self.get_quarter_note_seconds = get_quarter_note_seconds
        self.get_time_signature = get_time_signature
        self.get_default_start_time = get_default_start_time
        self.notes = []
        self.undo_stack = []
        self.redo_stack = []
        self.row_editors = {}
        self.measure_duration_modes = {}

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

        self.rest_duration_menu = ctk.CTkOptionMenu(
            self.actions_frame,
            values=self.NOTE_VALUE_OPTIONS,
            width=180,
        )
        self.rest_duration_menu.set(self.NOTE_VALUE_LABELS["1/4"])
        self.rest_duration_menu.grid(row=0, column=2, padx=(20, 5), pady=5)

        self.add_rest_btn = ctk.CTkButton(
            self.actions_frame,
            text="Add Rest",
            width=90,
            command=self.add_rest,
        )
        self.add_rest_btn.grid(row=0, column=3, padx=5, pady=5)

        self.apply_btn = ctk.CTkButton(
            self.actions_frame,
            text="Apply Changes",
            width=120,
            command=self.apply_changes,
        )
        self.apply_btn.grid(row=0, column=4, padx=(20, 5), pady=5)

        self.revert_btn = ctk.CTkButton(
            self.actions_frame,
            text="Revert Edits",
            width=110,
            command=self.draw_table,
        )
        self.revert_btn.grid(row=0, column=5, padx=5, pady=5)

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

        self.row_editors.clear()
        self.update_summary()
        self.update_apply_buttons()

        headers = [
            "Note/Rest",
            "Position",
            "Start (s)",
            "Duration / note value",
            "Hand",
            "Warnings",
            "Up",
            "Down",
            "Status",
            "Delete",
            "Add Note",
        ]

        for col, text in enumerate(headers):
            label = ctk.CTkLabel(self.table, text=text, font=("Arial", 14, "bold"))
            label.grid(row=0, column=col, padx=8, pady=5)

        display_row = 1
        previous_measure = None
        for index, note in enumerate(self.notes):
            current_measure = self.measure_for_time(note.start_time)

            if current_measure != previous_measure:
                self.create_measure_header(display_row, current_measure)
                display_row += 1
                previous_measure = current_measure

            self.create_note_row(display_row, note, current_measure)
            display_row += 1

            next_note = self.notes[index + 1] if index + 1 < len(self.notes) else None
            next_measure = self.measure_for_time(next_note.start_time) if next_note else None

            if next_measure != current_measure:
                self.create_measure_divider(display_row, current_measure)
                display_row += 1

    def set_notes(self, notes):
        self.notes = notes
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.measure_duration_modes.clear()

        for note in self.notes:
            if not hasattr(note, "staff"):
                note.staff = "auto"

        self.draw_table()
        self.update_history_buttons()

    def create_note_row(self, row, note, measure_number):
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

        duration_frame = ctk.CTkFrame(self.table, fg_color="transparent")
        duration_frame.grid(row=row, column=3, padx=5, pady=5, sticky="ew")

        duration_entry = ctk.CTkEntry(duration_frame, width=75)
        duration_entry.insert(0, f"{note.duration:.2f}")
        duration_entry.grid(row=0, column=0, padx=(0, 5), pady=2)

        note_value_menu = ctk.CTkOptionMenu(
            duration_frame,
            values=self.NOTE_VALUE_OPTIONS,
            width=170,
            command=lambda _value: self.mark_note_value_edited(note),
        )
        note_value_menu.set(self.closest_note_value_label(note.duration))
        note_value_menu.grid(row=0, column=1, padx=0, pady=2)

        staff_menu = ctk.CTkOptionMenu(
            self.table,
            values=self.STAFF_OPTIONS,
            width=105,
            command=lambda _value: self.mark_row_dirty(note),
        )
        staff_menu.set(self.staff_label(note))
        staff_menu.grid(row=row, column=4, padx=5, pady=5)

        for entry in (name_entry, start_entry):
            entry.bind(
                "<KeyRelease>",
                lambda _event, edited_note=note: self.mark_row_dirty(edited_note),
            )

        duration_entry.bind(
            "<KeyRelease>",
            lambda _event, edited_note=note: self.mark_duration_seconds_edited(
                edited_note
            ),
        )

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

        status_label = ctk.CTkLabel(
            self.table,
            text="Saved",
            text_color="#7ed957",
            width=60,
        )
        status_label.grid(row=row, column=8, padx=5, pady=5)

        delete_btn = ctk.CTkButton(
            self.table,
            text="Delete",
            width=70,
            command=lambda: self.delete_note(note)
        )
        delete_btn.grid(row=row, column=9, padx=5, pady=5)

        add_note_btn = ctk.CTkButton(
            self.table,
            text="Add Note",
            width=80,
            command=lambda: self.add_note_after(note)
        )
        add_note_btn.grid(row=row, column=10, padx=5, pady=5)

        self.row_editors[id(note)] = {
            "note": note,
            "measure_number": measure_number,
            "name_entry": name_entry,
            "start_entry": start_entry,
            "duration_entry": duration_entry,
            "note_value_menu": note_value_menu,
            "staff_menu": staff_menu,
            "status_label": status_label,
            "dirty": False,
        }

    def create_measure_header(self, row, measure_number):
        header = ctk.CTkFrame(self.table, fg_color="#1f2933")
        header.grid(
            row=row,
            column=0,
            columnspan=self.TABLE_COLUMN_COUNT,
            sticky="ew",
            padx=5,
            pady=(8, 3),
        )
        header.grid_columnconfigure(3, weight=1)

        label = ctk.CTkLabel(
            header,
            text=f"Measure {measure_number}",
            font=("Arial", 13, "bold"),
            text_color="#ffffff",
            width=90,
        )
        label.grid(row=0, column=0, padx=(8, 18), pady=6, sticky="w")

        mode = self.measure_duration_mode(measure_number)

        seconds_radio = ctk.CTkRadioButton(
            header,
            text="seconds",
            variable=mode,
            value="seconds",
            width=80,
            command=lambda: self.mark_measure_dirty(measure_number),
        )
        seconds_radio.grid(row=0, column=1, padx=(0, 8), pady=6, sticky="w")

        value_radio = ctk.CTkRadioButton(
            header,
            text="note",
            variable=mode,
            value="note_value",
            width=70,
            command=lambda: self.mark_measure_dirty(measure_number),
        )
        value_radio.grid(row=0, column=2, padx=(0, 8), pady=6, sticky="w")

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

    def mark_row_dirty(self, note):
        editor = self.row_editors.get(id(note))
        if not editor:
            return

        editor["dirty"] = True
        editor["status_label"].configure(text="Edited", text_color="#f5a623")
        self.update_apply_buttons()

    def mark_duration_seconds_edited(self, note):
        editor = self.row_editors.get(id(note))
        if editor:
            self.measure_duration_mode(editor["measure_number"]).set("seconds")

        self.mark_row_dirty(note)

    def mark_note_value_edited(self, note):
        editor = self.row_editors.get(id(note))
        if editor:
            self.measure_duration_mode(editor["measure_number"]).set("note_value")

        self.mark_row_dirty(note)

    def mark_measure_dirty(self, measure_number):
        for editor in self.row_editors.values():
            if editor["measure_number"] == measure_number:
                self.mark_row_dirty(editor["note"])

    def apply_changes(self):
        dirty_editors = [
            editor for editor in self.row_editors.values()
            if editor.get("dirty")
        ]

        if not dirty_editors:
            return

        updates = []
        has_invalid_row = False

        for editor in dirty_editors:
            note = editor["note"]
            measure_number = editor["measure_number"]
            name_entry = editor["name_entry"]
            start_entry = editor["start_entry"]
            duration_entry = editor["duration_entry"]
            note_value_menu = editor["note_value_menu"]
            staff_menu = editor["staff_menu"]

            try:
                name = name_entry.get().strip()
                start_time = float(start_entry.get())
                duration = self.row_duration_seconds(
                    self.measure_duration_mode(measure_number).get(),
                    duration_entry.get(),
                    note_value_menu.get(),
                )
                staff = self.staff_value(staff_menu.get())
            except ValueError:
                editor["status_label"].configure(text="Invalid", text_color="#ff6b6b")
                has_invalid_row = True
                continue

            updates.append((note, name, start_time, duration, staff))

        if has_invalid_row:
            return

        if not updates:
            return

        self.push_undo_state()

        for note, name, start_time, duration, staff in updates:
            note.name = name
            note.start_time = start_time
            note.duration = duration
            note.staff = staff

        self.draw_table()
        self.notify_change()

    def save_row(self, note, name_entry, start_entry, duration_entry, staff_menu):
        try:
            name = name_entry.get().strip()
            start_time = float(start_entry.get())
            duration = float(duration_entry.get())
            staff = self.staff_value(staff_menu.get())

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
        self.push_undo_state()
        self.notes.append(self.create_added_note(self.next_start_time()))
        self.draw_table()
        self.notify_change()

    def add_note_after(self, note):
        self.push_undo_state()
        new_note = self.create_added_note(note.start_time + note.duration)

        try:
            index = self.notes.index(note)
            self.notes.insert(index + 1, new_note)
        except ValueError:
            self.notes.append(new_note)

        self.draw_table()
        self.notify_change()

    def create_added_note(self, start_time):
        quarter_note_seconds = self.current_quarter_note_seconds()
        duration_multiplier = self.duration_multiplier_for_label(
            self.NOTE_VALUE_LABELS["1/4"]
        )

        return DetectedNote(
            name="C4",
            start_time=start_time,
            duration=quarter_note_seconds * duration_multiplier,
            staff="auto"
        )

    def add_rest(self):
        quarter_note_seconds = self.current_quarter_note_seconds()
        duration_multiplier = self.duration_multiplier_for_label(
            self.rest_duration_menu.get()
        )

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

    def measure_duration_mode(self, measure_number):
        if measure_number not in self.measure_duration_modes:
            self.measure_duration_modes[measure_number] = tk.StringVar(value="seconds")

        return self.measure_duration_modes[measure_number]

    def row_duration_seconds(self, mode, seconds_text, note_value_label):
        if mode == "note_value":
            return (
                self.current_quarter_note_seconds()
                * self.duration_multiplier_for_label(note_value_label)
            )

        return float(seconds_text)

    def duration_multiplier_for_label(self, label):
        duration_key = self.NOTE_VALUE_TO_DURATION_KEY.get(label, label)
        return self.DURATION_MULTIPLIERS[duration_key]

    def closest_note_value_label(self, duration):
        quarter_note_seconds = self.current_quarter_note_seconds()

        if quarter_note_seconds <= 0:
            return self.NOTE_VALUE_LABELS["1/4"]

        closest_key = min(
            self.DURATION_MULTIPLIERS,
            key=lambda key: abs(
                (quarter_note_seconds * self.DURATION_MULTIPLIERS[key]) - duration
            ),
        )
        return self.NOTE_VALUE_LABELS[closest_key]

    def next_start_time(self):
        if not self.notes:
            if self.get_default_start_time:
                return self.get_default_start_time()

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

        self.update_apply_buttons()

    def update_apply_buttons(self):
        if not hasattr(self, "apply_btn"):
            return

        dirty_count = sum(
            1 for editor in self.row_editors.values()
            if editor.get("dirty")
        )
        state = "normal" if dirty_count else "disabled"
        self.apply_btn.configure(
            state=state,
            text=f"Apply Changes ({dirty_count})" if dirty_count else "Apply Changes",
        )
        self.revert_btn.configure(state=state)

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

    def staff_label(self, note):
        return self.STAFF_VALUE_TO_LABEL.get(getattr(note, "staff", "auto"), "auto")

    def staff_value(self, label):
        return self.STAFF_LABEL_TO_VALUE.get(label, "auto")

    def notify_change(self):
        self.update_history_buttons()
        if self.on_notes_changed:
            self.on_notes_changed(self.notes)
