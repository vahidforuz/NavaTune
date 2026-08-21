from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


class PDFExporter:
    def export_sheet(self, notes, output_path: str):
        pdf = canvas.Canvas(output_path, pagesize=letter)

        width, height = letter

        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(50, height - 50, "NavaTune - Sheet Music")

        self._draw_staff(pdf, x_start=60, x_end=540, y_start=620)

        self._draw_notes(pdf, notes, x_start=100, y_start=620)

        pdf.save()

    def _draw_staff(self, pdf, x_start, x_end, y_start):
        line_spacing = 14

        for i in range(5):
            y = y_start - i * line_spacing
            pdf.line(x_start, y, x_end, y)
        
        pdf.setFont("Helvetica", 48)
        pdf.drawString(x_start + 5, y_start - 55, "𝄞")

    def _draw_notes(self, pdf, notes, x_start, y_start):
        if not notes:
            pdf.setFont("Helvetica", 12)
            pdf.drawString(x_start, y_start - 100, "No notes detected.")
            return

        note_positions = {
            "C4": y_start - 70,
            "D4": y_start - 63,
            "E4": y_start - 56,
            "F4": y_start - 49,
            "G4": y_start - 42,
            "A4": y_start - 35,
            "B4": y_start - 28,
            "C5": y_start - 21,
        }

        x = x_start

        for note in notes:
            name = note.name if hasattr(note, "name") else str(note)
            y = note_positions.get(name, y_start - 42)

            # note head
            pdf.ellipse(x - 8, y - 6, x + 8, y + 6, fill=1)

            # stem
            pdf.line(x + 8, y, x + 8, y + 45)

            # note name under staff
            pdf.setFont("Helvetica", 9)
            pdf.drawString(x - 8, y_start - 110, name)

            x += 50

            if x > 520:
                break

    def export_notes(self, notes, output_path: str):
        self.export_sheet(notes, output_path)
