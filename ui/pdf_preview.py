import fitz
from PIL import Image
import customtkinter as ctk
import tkinter as tk


class PDFPreview(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))

        self.vertical_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="vertical",
            command=self.canvas.yview,
            button_color="#3b8ed0",
            button_hover_color="#1f6aa5",
        )
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 10), pady=(10, 0))

        self.horizontal_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="horizontal",
            command=self.canvas.xview,
            button_color="#3b8ed0",
            button_hover_color="#1f6aa5",
        )
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew", padx=(10, 0), pady=(4, 10))

        self.canvas.configure(
            xscrollcommand=self.horizontal_scrollbar.set,
            yscrollcommand=self.vertical_scrollbar.set,
        )

        self.preview_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.preview_window = self.canvas.create_window(
            (0, 0),
            window=self.preview_frame,
            anchor="nw",
        )

        self.image_label = ctk.CTkLabel(self.preview_frame, text="No sheet preview yet")
        self.image_label.pack(padx=10, pady=10)

        self.ctk_image = None
        self.preview_frame.bind("<Configure>", self.update_scroll_region)

    def update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def load_pdf(self, pdf_path: str):
        with fitz.open(pdf_path) as doc:
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))

        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        self.ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size
        )

        self.image_label.configure(
            text="",
            image=self.ctk_image
        )
