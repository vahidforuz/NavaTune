import customtkinter as ctk

from notation.tonality import supported_tonality_labels, tonality_label


class TonalityDialog(ctk.CTkToplevel):
    def __init__(self, parent, selected_tonality, on_selected):
        super().__init__(parent)

        self.on_selected = on_selected
        self.title("Choose Tonality")
        self.geometry("320x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self, text="Tonality", font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self.tonality_menu = ctk.CTkOptionMenu(
            self,
            values=supported_tonality_labels(),
            width=250,
        )
        self.tonality_menu.set(tonality_label(selected_tonality))
        self.tonality_menu.grid(row=1, column=0, sticky="ew", padx=18, pady=8)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="e", padx=18, pady=(20, 18))

        cancel_btn = ctk.CTkButton(
            actions,
            text="Cancel",
            width=90,
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=0, padx=5)

        apply_btn = ctk.CTkButton(
            actions,
            text="Apply",
            width=90,
            command=self.apply_selection,
        )
        apply_btn.grid(row=0, column=1, padx=5)

        self.tonality_menu.focus_set()

    def apply_selection(self):
        self.on_selected(self.tonality_menu.get())
        self.destroy()
