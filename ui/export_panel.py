import customtkinter as ctk


class ExportPanel(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_export_pdf,
        on_export_musicxml,
        on_open_musicxml,
    ):
        super().__init__(parent)

        self.export_pdf_btn = ctk.CTkButton(
            self,
            text="Export PDF",
            command=on_export_pdf
        )
        self.export_pdf_btn.pack(side="left", padx=5, pady=10)

        self.export_xml_btn = ctk.CTkButton(
            self,
            text="Export MusicXML",
            command=on_export_musicxml
        )
        self.export_xml_btn.pack(side="left", padx=5, pady=10)

        self.open_xml_btn = ctk.CTkButton(
            self,
            text="Open MusicXML",
            command=on_open_musicxml
        )
        self.open_xml_btn.pack(side="left", padx=5, pady=10)
