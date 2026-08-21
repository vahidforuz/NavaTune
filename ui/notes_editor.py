import customtkinter as ctk
from models.detected_note import DetectedNote


PITCHES = [
    "C2", "D2", "E2", "F2", "G2", "A2", "B2",
    "C3", "D3", "E3", "F3", "G3", "A3", "B3",
    "C4", "D4", "E4", "F4", "G4", "A4", "B4",
    "C5", "D5", "E5", "F5", "G5", "A5", "B5",
]


class NotesEditor(ctk.CTkFrame):
    REST_DURATIONS = {
        "1": 4.0,
        "1/2": 2.0,
        "1/4": 1.0,
        "1/8": 0.5,
        "1/16": 0.25,
    }

    def __init__(
        self,
        parent,
        on_notes_changed=None,
        get_quarter_note_seconds=None,
    ):
        super().__init__(parent)

        self.on_notes_changed = on_notes_changed
        self.get_quarter_note_seconds = get_quarter_note_seconds
        self.notes = []

        title = ctk.CTkLabel(self, text="Editable Notes", font=("Arial", 22))
        title.pack(pady=10)

        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(pady=5)

        self.add_btn = ctk.CTkButton(
            self.actions_frame,
            text="Add Note",
            command=self.add_note,
        )
        self.add_btn.grid(row=0, column=0, padx=5, pady=5)

        self.rest_duration_menu = ctk.CTkOptionMenu(
            self.actions_frame,
            values=list(self.REST_DURATIONS.keys()),
            width=80,
        )
        self.rest_duration_menu.set("1/4")
        self.rest_duration_menu.grid(row=0, column=1, padx=5, pady=5)

        self.add_rest_btn = ctk.CTkButton(
            self.actions_frame,
            text="Add Rest",
            command=self.add_rest,
        )
        self.add_rest_btn.grid(row=0, column=2, padx=5, pady=5)

        self.table = ctk.CTkScrollableFrame(self)
        self.table.pack(fill="both", expand=True, padx=10, pady=10)

        self.draw_table()

    def draw_table(self):
        for widget in self.table.winfo_children():
            widget.destroy()

        headers = ["Note/Rest", "Start", "Duration", "Staff", "Move", "Actions"]

        for col, text in enumerate(headers):
            label = ctk.CTkLabel(self.table, text=text, font=("Arial", 14, "bold"))
            label.grid(row=0, column=col, padx=8, pady=5)

        for row, note in enumerate(self.notes, start=1):
            self.create_note_row(row, note)

    def set_notes(self, notes):
        self.notes = notes

        for note in self.notes:
            if not hasattr(note, "staff"):
                note.staff = "auto"

        self.draw_table()

    def create_note_row(self, row, note):
        name_entry = ctk.CTkEntry(self.table, width=80)
        name_entry.insert(0, note.name)
        name_entry.grid(row=row, column=0, padx=5, pady=5)

        start_entry = ctk.CTkEntry(self.table, width=80)
        start_entry.insert(0, f"{note.start_time:.2f}")
        start_entry.grid(row=row, column=1, padx=5, pady=5)

        duration_entry = ctk.CTkEntry(self.table, width=80)
        duration_entry.insert(0, f"{note.duration:.2f}")
        duration_entry.grid(row=row, column=2, padx=5, pady=5)

        staff_menu = ctk.CTkOptionMenu(
            self.table,
            values=["auto", "treble", "bass"]
        )
        staff_menu.set(getattr(note, "staff", "auto"))
        staff_menu.grid(row=row, column=3, padx=5, pady=5)

        up_btn = ctk.CTkButton(
            self.table,
            text="↑",
            width=35,
            command=lambda: self.move_note(note, 1)
        )
        up_btn.grid(row=row, column=4, padx=2, pady=5)

        down_btn = ctk.CTkButton(
            self.table,
            text="↓",
            width=35,
            command=lambda: self.move_note(note, -1)
        )
        down_btn.grid(row=row, column=5, padx=2, pady=5)

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
        save_btn.grid(row=row, column=6, padx=5, pady=5)

        delete_btn = ctk.CTkButton(
            self.table,
            text="Delete",
            width=70,
            command=lambda: self.delete_note(note)
        )
        delete_btn.grid(row=row, column=7, padx=5, pady=5)

    def save_row(self, note, name_entry, start_entry, duration_entry, staff_menu):
        try:
            note.name = name_entry.get()
            note.start_time = float(start_entry.get())
            note.duration = float(duration_entry.get())
            note.staff = staff_menu.get()

            self.notify_change()

        except ValueError:
            print("Invalid number")

    def move_note(self, note, direction):
        if note.is_rest():
            return

        clean_name = note.name.replace("♯", "#").replace("♭", "b")

        if clean_name not in PITCHES:
            return

        index = PITCHES.index(clean_name)
        new_index = index + direction

        if 0 <= new_index < len(PITCHES):
            note.name = PITCHES[new_index]

        self.draw_table()
        self.notify_change()

    def add_note(self):
        new_note = DetectedNote(
            name="C4",
            start_time=0.0,
            duration=0.5,
            staff="auto"
        )

        self.notes.append(new_note)
        self.draw_table()
        self.notify_change()

    def add_rest(self):
        quarter_note_seconds = self.current_quarter_note_seconds()
        duration_multiplier = self.REST_DURATIONS[self.rest_duration_menu.get()]

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
            self.notes.remove(note)

        self.draw_table()
        self.notify_change()

    def notify_change(self):
        if self.on_notes_changed:
            self.on_notes_changed(self.notes)
