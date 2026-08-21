import customtkinter as ctk


class Workspace(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.label = ctk.CTkLabel(
            self,
            text="Empty Workspace",
            font=("Arial", 22)
        )
        self.label.grid(row=0, column=0, sticky="nsew")

    def set_message(self, message: str):
        self.label.configure(text=message)
