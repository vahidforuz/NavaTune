import subprocess


class PDFMusicXMLConverter:
    def convert(self, musicxml_path: str, pdf_path: str):
        subprocess.run(
            ["musescore3", musicxml_path, "-o", pdf_path],
            check=True
        )
