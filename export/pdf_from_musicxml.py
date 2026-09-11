import subprocess
import tempfile
import os


class PDFMusicXMLConverter:
    def convert(self, musicxml_path: str, pdf_path: str):
        subprocess.run(
            ["musescore3", musicxml_path, "-o", pdf_path],
            check=True
        )
        self.add_page_numbers(pdf_path)

    def add_page_numbers(self, pdf_path: str):
        page_count = self.get_page_count(pdf_path)

        if page_count < 1:
            return

        output_dir = os.path.dirname(os.path.abspath(pdf_path)) or "."

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
            dir=output_dir,
        ) as temp_file:
            numbered_pdf_path = temp_file.name

        try:
            subprocess.run(
                [
                    "gs",
                    "-dBATCH",
                    "-dNOPAUSE",
                    "-q",
                    "-sDEVICE=pdfwrite",
                    f"-sOutputFile={numbered_pdf_path}",
                    "-c",
                    self.page_number_postscript(page_count),
                    "-f",
                    pdf_path,
                ],
                check=True,
            )
            os.replace(numbered_pdf_path, pdf_path)
        finally:
            if os.path.exists(numbered_pdf_path):
                os.remove(numbered_pdf_path)

    def get_page_count(self, pdf_path: str) -> int:
        result = subprocess.run(
            ["pdfinfo", pdf_path],
            check=True,
            capture_output=True,
            text=True,
        )

        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())

        return 0

    def page_number_postscript(self, page_count: int) -> str:
        return f"""
/PageNum 0 def
/TotalPages {page_count} def
<< /EndPage {{
  /reason exch def
  pop
  reason 0 eq {{
    /PageNum PageNum 1 add def
    gsave
      /Helvetica findfont 9 scalefont setfont
      0 setgray
      /PageSize currentpagedevice /PageSize get def
      /pageString 16 string def
      /totalString 16 string def
      /textBuffer 64 string def
      textBuffer 0 PageNum pageString cvs putinterval
      textBuffer PageNum pageString cvs length (/) putinterval
      textBuffer PageNum pageString cvs length 1 add TotalPages totalString cvs putinterval
      /textLength PageNum pageString cvs length 1 add TotalPages totalString cvs length add def
      /text textBuffer 0 textLength getinterval def
      PageSize 0 get 2 div text stringwidth pop 2 div sub 24 moveto
      text show
    grestore
    true
  }} {{
    false
  }} ifelse
}} >> setpagedevice
"""
