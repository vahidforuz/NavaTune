import customtkinter as ctk


class Toolbar(ctk.CTkFrame):
    COMPACT_WIDTH = 1350
    NARROW_WIDTH = 760

    def __init__(
        self,
        parent,
        on_upload,
        on_record,
        on_stop,
        on_settings,
        on_detector_changed
    ):
        super().__init__(parent)

        self.current_layout = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.timing_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.timing_frame.grid(row=0, column=1, sticky="e", padx=5, pady=5)

        self.detector_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.detector_frame.grid(row=1, column=0, sticky="w", padx=5, pady=5)

        self.upload_btn = ctk.CTkButton(
            self.actions_frame,
            text="Upload",
            command=on_upload,
        )
        self.upload_btn.grid(row=0, column=0, padx=5, pady=5)

        self.record_btn = ctk.CTkButton(
            self.actions_frame,
            text="Record",
            command=on_record,
        )
        self.record_btn.grid(row=0, column=1, padx=5, pady=5)

        self.stop_btn = ctk.CTkButton(
            self.actions_frame,
            text="Stop",
            command=on_stop,
        )
        self.stop_btn.grid(row=0, column=2, padx=5, pady=5)

        self.settings_btn = ctk.CTkButton(
            self.actions_frame,
            text="Settings",
            command=on_settings,
        )
        self.settings_btn.grid(row=0, column=3, padx=5, pady=5)

        self.tempo_label = ctk.CTkLabel(self.timing_frame, text="Tempo (BPM)")
        self.tempo_label.grid(row=0, column=0, padx=(5, 5), pady=5)

        self.tempo_menu = ctk.CTkComboBox(
            self.timing_frame,
            values=["40", "60", "80", "100", "120", "140"],
            width=80,
        )
        self.tempo_menu.set("60")
        self.tempo_menu.grid(row=0, column=1, padx=5, pady=5)

        self.time_signature_label = ctk.CTkLabel(
            self.timing_frame,
            text="Time Signature",
        )
        self.time_signature_label.grid(row=0, column=2, padx=(15, 5), pady=5)

        self.time_signature_menu = ctk.CTkOptionMenu(
            self.timing_frame,
            values=["2/4", "3/4", "4/4", "6/8", "9/8", "12/8"],
            width=80,
        )
        self.time_signature_menu.set("4/4")
        self.time_signature_menu.grid(row=0, column=3, padx=5, pady=5)

        self.timing_mode_menu = ctk.CTkOptionMenu(
            self.timing_frame,
            values=["Tempo/Signature", "Legacy Timing"],
            width=140,
        )
        self.timing_mode_menu.set("Tempo/Signature")
        self.timing_mode_menu.grid(row=0, column=4, padx=(15, 5), pady=5)

        self.detector_menu = ctk.CTkOptionMenu(
            self.detector_frame,
            values=[
                "Librosa",
                "Spotify Basic Pitch",
                "NMF (Non-negative Matrix Factorization)",
            ],
            command=on_detector_changed,
            width=240,
        )
        self.detector_menu.set("Librosa")
        self.detector_menu.grid(row=0, column=0, padx=5, pady=5)

        self.bind("<Configure>", self.update_responsive_layout)
        self.after(0, lambda: self.update_responsive_layout())

    def get_tempo_bpm(self):
        try:
            return max(1, int(float(self.tempo_menu.get())))
        except ValueError:
            self.tempo_menu.set("60")
            return 60

    def get_time_signature(self):
        return self.time_signature_menu.get()

    def use_tempo_quantization(self):
        return self.timing_mode_menu.get() == "Tempo/Signature"

    def update_responsive_layout(self, event=None):
        width = event.width if event else self.winfo_width()

        if width <= self.NARROW_WIDTH:
            layout = "narrow"
        elif width <= self.COMPACT_WIDTH:
            layout = "compact"
        else:
            layout = "wide"

        if layout == self.current_layout:
            return

        self.current_layout = layout

        self.actions_frame.grid_forget()
        self.timing_frame.grid_forget()
        self.detector_frame.grid_forget()

        if layout == "wide":
            self.actions_frame.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.timing_frame.grid(row=0, column=1, sticky="e", padx=5, pady=5)
            self.detector_frame.grid(row=0, column=2, sticky="e", padx=5, pady=5)
            self.grid_columnconfigure(0, weight=0)
            self.grid_columnconfigure(1, weight=1)
            self.grid_columnconfigure(2, weight=0)
        elif layout == "compact":
            self.actions_frame.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.timing_frame.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.detector_frame.grid(row=1, column=1, sticky="e", padx=5, pady=5)
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=0)
            self.grid_columnconfigure(2, weight=0)
        else:
            self.actions_frame.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.timing_frame.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.detector_frame.grid(row=2, column=0, sticky="w", padx=5, pady=5)
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=0)
            self.grid_columnconfigure(2, weight=0)
