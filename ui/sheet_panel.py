import customtkinter as ctk
import tkinter as tk


class SheetPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = tk.Canvas(
            self,
            bg="white",
            height=500,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=20, pady=20)

        self.draw_empty_staff()

    def draw_staff(self, start_x, end_x, start_y, clef_name):
        line_spacing = 14

        for i in range(5):
            y = start_y + i * line_spacing
            self.canvas.create_line(
                start_x, y, end_x, y,
                fill="black",
                width=2
            )

        self.canvas.create_text(
            start_x + 20,
            start_y - 30,
            text=clef_name,
            fill="black",
            font=("Arial", 16, "bold")
        )

    def draw_empty_staff(self):
        self.canvas.delete("all")

        self.draw_staff(
            start_x=60,
            end_x=760,
            start_y=100,
            clef_name="Treble Staff"
        )

        self.draw_staff(
            start_x=60,
            end_x=760,
            start_y=280,
            clef_name="Bass Staff"
        )

    def show_notes(self, notes):
        self.draw_empty_staff()

        if not notes:
            return

        x_treble = 120
        x_bass = 120

        treble_positions = {
            "Cb4": 170, "C4": 170, "C#4": 170,
            "Db4": 163, "D4": 163, "D#4": 163,
            "Eb4": 156, "E4": 156, "E#4": 156,
            "Fb4": 149, "F4": 149, "F#4": 149,
            "Gb4": 142, "G4": 142, "G#4": 142,
            "Ab4": 135, "A4": 135, "A#4": 135,
            "Bb4": 128, "B4": 128, "B#4": 128,
            "Cb5": 121, "C5": 121, "C#5": 121,
        }

        bass_positions = {
            "Cb2": 350, "C2": 350, "C#2": 350,
            "Db2": 343, "D2": 343, "D#2": 343,
            "Eb2": 336, "E2": 336, "E#2": 336,
            "Fb2": 329, "F2": 329, "F#2": 329,
            "Gb2": 322, "G2": 322, "G#2": 322,
            "Ab2": 315, "A2": 315, "A#2": 315,
            "Bb2": 308, "B2": 308, "B#2": 308,

            "Cb3": 301, "C3": 301, "C#3": 301,
            "Db3": 294, "D3": 294, "D#3": 294,
            "Eb3": 287, "E3": 287, "E#3": 287,
            "Fb3": 280, "F3": 280, "F#3": 280,
            "Gb3": 273, "G3": 273, "G#3": 273,
            "Ab3": 266, "A3": 266, "A#3": 266,
            "Bb3": 259, "B3": 259, "B#3": 259,
        }

        for note in notes:
            name = note.name if hasattr(note, "name") else str(note)

            simple_name = (
                name.replace("♯", "#")
                    .replace("♭", "b")
            )

            octave = self.get_octave(simple_name)

            if octave >= 4:
                y = treble_positions.get(simple_name, 142)
                x = x_treble
                x_treble += 70
            else:
                y = bass_positions.get(simple_name, 301)
                x = x_bass
                x_bass += 70

            self.draw_accidental(simple_name, x, y)
            self.draw_note(x, y)

            self.canvas.create_text(
                x,
                y + 65,
                text=simple_name,
                fill="black",
                font=("Arial", 10)
            )

    def get_octave(self, note_name):
        for char in reversed(note_name):
            if char.isdigit():
                return int(char)
        return 4

    def draw_accidental(self, note_name, x, y):
        if "#" in note_name:
            self.canvas.create_text(
                x - 18,
                y,
                text="#",
                font=("Arial", 18),
                fill="black"
            )

        elif "b" in note_name:
            self.canvas.create_text(
                x - 18,
                y,
                text="♭",
                font=("Arial", 20),
                fill="black"
            )

    def draw_note(self, x, y):
        self.canvas.create_oval(
            x - 10,
            y - 7,
            x + 10,
            y + 7,
            fill="black"
        )

        self.canvas.create_line(
            x + 10,
            y,
            x + 10,
            y - 50,
            width=2
        )