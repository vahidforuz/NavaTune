import customtkinter as ctk


class StatusBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.status_label = ctk.CTkLabel(self, text="Status: Ready")
        self.status_label.pack(side="left", padx=10, pady=5)

    def set_status(self, message: str):
        self.status_label.configure(text=f"Status: {message}")
