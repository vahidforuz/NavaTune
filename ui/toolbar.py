import customtkinter as ctk

from notation.tonality import tonality_label


class Toolbar(ctk.CTkFrame):
    COMPACT_WIDTH = 1120
    NARROW_WIDTH = 720

    def __init__(
        self,
        parent,
        on_detector_changed,
        on_choose_tonality,
    ):
        super().__init__(parent)

        self.current_layout = None

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self.timing_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.timing_frame.grid(row=0, column=0, sticky="w", padx=4, pady=2)

        self.detector_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.detector_frame.grid(row=0, column=1, sticky="ew", padx=4, pady=2)

        self.tonality_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tonality_frame.grid(row=0, column=2, sticky="e", padx=4, pady=2)

        self.tempo_label = ctk.CTkLabel(self.timing_frame, text="Tempo (BPM)")
        self.tempo_label.grid(row=0, column=0, padx=(2, 4), pady=2)

        self.tempo_menu = ctk.CTkComboBox(
            self.timing_frame,
            values=["40", "60", "80", "100", "120", "140"],
            width=72,
        )
        self.tempo_menu.set("60")
        self.tempo_menu.grid(row=0, column=1, padx=3, pady=2)

        self.time_signature_label = ctk.CTkLabel(
            self.timing_frame,
            text="Time Signature",
        )
        self.time_signature_label.grid(row=0, column=2, padx=(10, 4), pady=2)

        self.time_signature_menu = ctk.CTkOptionMenu(
            self.timing_frame,
            values=["2/4", "3/4", "4/4", "6/8", "9/8", "12/8"],
            width=72,
        )
        self.time_signature_menu.set("4/4")
        self.time_signature_menu.grid(row=0, column=3, padx=3, pady=2)

        self.timing_mode_menu = ctk.CTkOptionMenu(
            self.timing_frame,
            values=["Tempo/Signature", "Legacy Timing"],
            width=130,
        )
        self.timing_mode_menu.set("Tempo/Signature")
        self.timing_mode_menu.grid(row=0, column=4, padx=(10, 3), pady=2)

        self.detector_menu = ctk.CTkOptionMenu(
            self.detector_frame,
            values=[
                "Spotify Basic Pitch",
                "Magenta Onsets and Frames (solo piano)",
            ],
            command=on_detector_changed,
            width=290,
        )
        self.detector_menu.set("Spotify Basic Pitch")
        self.detector_menu.grid(row=0, column=0, sticky="ew", padx=3, pady=2)

        self.tonality_label = ctk.CTkLabel(
            self.tonality_frame,
            text="Tonality: Automatic / Unknown",
        )
        self.tonality_label.grid(row=0, column=0, padx=3, pady=2)

        self.tonality_btn = ctk.CTkButton(
            self.tonality_frame,
            text="Choose Tonality",
            command=on_choose_tonality,
            width=135,
        )
        self.tonality_btn.grid(row=0, column=1, padx=(4, 2), pady=2)

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

    def set_tonality(self, tonality):
        self.tonality_label.configure(text=f"Tonality: {tonality_label(tonality)}")
        self.tonality_btn.configure(text="Change Tonality")

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

        self.timing_frame.grid_forget()
        self.detector_frame.grid_forget()
        self.tonality_frame.grid_forget()

        if layout == "wide":
            self.timing_frame.grid(row=0, column=0, sticky="w", padx=4, pady=2)
            self.detector_frame.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
            self.tonality_frame.grid(row=0, column=2, sticky="e", padx=4, pady=2)
            self.grid_columnconfigure(0, weight=0)
            self.grid_columnconfigure(1, weight=1)
            self.grid_columnconfigure(2, weight=0)
        elif layout == "compact":
            self.timing_frame.grid(row=0, column=0, sticky="w", padx=4, pady=2)
            self.detector_frame.grid(row=0, column=1, sticky="e", padx=4, pady=2)
            self.tonality_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=2)
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=0)
            self.grid_columnconfigure(2, weight=0)
        else:
            self.timing_frame.grid(row=0, column=0, sticky="w", padx=4, pady=2)
            self.detector_frame.grid(row=1, column=0, sticky="w", padx=4, pady=2)
            self.tonality_frame.grid(row=2, column=0, sticky="w", padx=4, pady=2)
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=0)
            self.grid_columnconfigure(2, weight=0)
