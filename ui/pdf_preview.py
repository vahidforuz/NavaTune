import fitz
from PIL import Image
import customtkinter as ctk
import tkinter as tk


class PDFPreview(ctk.CTkFrame):
    def __init__(self, parent, on_edit_score_details=None):
        super().__init__(parent)

        self.on_edit_score_details = on_edit_score_details

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.toolbar = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=(10, 0),
        )

        self.score_details_btn = ctk.CTkButton(
            self.toolbar,
            text="Score Details",
            command=self.open_score_details,
            width=130,
        )
        self.score_details_btn.pack(side="left")

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))

        self.vertical_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="vertical",
            command=self.canvas.yview,
            button_color="#3b8ed0",
            button_hover_color="#1f6aa5",
        )
        self.vertical_scrollbar.grid(row=1, column=1, sticky="ns", padx=(4, 10), pady=(10, 0))

        self.horizontal_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="horizontal",
            command=self.canvas.xview,
            button_color="#3b8ed0",
            button_hover_color="#1f6aa5",
        )
        self.horizontal_scrollbar.grid(row=2, column=0, sticky="ew", padx=(10, 0), pady=(4, 10))

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
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.preview_frame)
        self._bind_mousewheel(self.image_label)

    def open_score_details(self):
        if self.on_edit_score_details:
            self.on_edit_score_details()

    def update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        widget.bind("<Button-4>", self._on_linux_scroll_up)
        widget.bind("<Button-5>", self._on_linux_scroll_down)
        widget.bind("<Shift-Button-4>", self._on_linux_scroll_left)
        widget.bind("<Shift-Button-5>", self._on_linux_scroll_right)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(self._wheel_units(event.delta), "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(self._wheel_units(event.delta), "units")

    def _on_linux_scroll_up(self, _event):
        self.canvas.yview_scroll(-3, "units")

    def _on_linux_scroll_down(self, _event):
        self.canvas.yview_scroll(3, "units")

    def _on_linux_scroll_left(self, _event):
        self.canvas.xview_scroll(-3, "units")

    def _on_linux_scroll_right(self, _event):
        self.canvas.xview_scroll(3, "units")

    def _wheel_units(self, delta):
        if delta == 0:
            return 0

        return -1 * int(delta / abs(delta)) * max(1, abs(delta) // 120)

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
