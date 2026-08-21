import fitz
from PIL import Image
import customtkinter as ctk


class PDFPreview(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.image_label = ctk.CTkLabel(self, text="No sheet preview yet")
        self.image_label.pack(fill="both", expand=True, padx=10, pady=10)

        self.ctk_image = None

    def load_pdf(self, pdf_path: str):
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)

        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        image.thumbnail((900, 650))

        self.ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size
        )

        self.image_label.configure(
            text="",
            image=self.ctk_image
        )