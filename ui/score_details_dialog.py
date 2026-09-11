import customtkinter as ctk

from models.score_metadata import ScoreMetadata


class ScoreDetailsDialog(ctk.CTkToplevel):
    def __init__(self, parent, score_metadata, on_save):
        super().__init__(parent)

        self.title("Score Details")
        self.geometry("420x360")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_save = on_save
        self.entries = {}
        metadata = score_metadata.normalized()

        self.grid_columnconfigure(1, weight=1)

        fields = [
            ("Title", "title", metadata.title),
            ("Subtitle", "subtitle", metadata.subtitle),
            ("Composer", "composer", metadata.composer),
            ("Arranger", "arranger", metadata.arranger),
            ("Copyright", "copyright", metadata.copyright),
        ]

        for row, (label_text, key, value) in enumerate(fields):
            label = ctk.CTkLabel(self, text=label_text)
            label.grid(row=row, column=0, sticky="w", padx=16, pady=(16 if row == 0 else 8, 4))

            entry = ctk.CTkEntry(self)
            entry.insert(0, value)
            entry.grid(row=row, column=1, sticky="ew", padx=(8, 16), pady=(16 if row == 0 else 8, 4))
            self.entries[key] = entry

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", padx=16, pady=20)

        cancel_btn = ctk.CTkButton(
            buttons,
            text="Cancel",
            command=self.destroy,
            width=90,
        )
        cancel_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(
            buttons,
            text="Apply",
            command=self.save,
            width=90,
        )
        save_btn.pack(side="left", padx=5)

    def save(self):
        metadata = ScoreMetadata(
            title=self.entries["title"].get(),
            subtitle=self.entries["subtitle"].get(),
            composer=self.entries["composer"].get(),
            arranger=self.entries["arranger"].get(),
            copyright=self.entries["copyright"].get(),
        ).normalized()

        self.on_save(metadata)
        self.destroy()
