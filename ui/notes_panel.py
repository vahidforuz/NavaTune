import customtkinter as ctk


class NotesPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        title = ctk.CTkLabel(
            self,
            text="Detected Notes",
            font=("Arial", 22)
        )
        title.pack(pady=20)

        self.textbox = ctk.CTkTextbox(self)
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)

        self.textbox.insert("end", "No notes detected yet.\n")
        self.textbox.configure(state="disabled")

    def set_notes(self, notes):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")

        if not notes:
            self.textbox.insert("end", "No notes detected yet.\n")
        else:
            for note in notes:
                if hasattr(note, "start_time"):
                    name = "Rest" if note.is_rest() else note.name
                    line = (
                        f"{name} | "
                        f"start: {note.start_time:.2f}s | "
                        f"duration: {note.duration:.2f}s\n"
                    )
                else:
                    line = f"{note}\n"
    
                self.textbox.insert("end", line)

        self.textbox.configure(state="disabled")
