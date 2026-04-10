from pathlib import Path

import fitz
from PIL import Image


class pdf_handler:

    def __init__(self, path: Path):
        "Initalize the handler and opens the PDF file"
        self.path = path
        self.current_page = 0
        self.doc = fitz.open(self.path)
        self.pages = len(self.doc)

    def doc_reload(self):
        """reload doc from PDF file"""
        self.doc.close()
        self.doc = fitz.open(self.path)
        self.pages = len(self.doc)

    def get_pdf_page(self):
        """returns next page of the PDF file"""
        if self.current_page >= self.pages:
            return
        output = self.doc[self.current_page]
        self.current_page = self.current_page + 1
        return output.get_text()

    def convert_to_pic(self):
        """Yields a PIL Image for each page in the PDF.
        Uses a scale matrix to reduce memory footprint and increase speed."""
        for page in self.doc:
            mat = fitz.Matrix(0.35, 0.35)
            map = page.get_pixmap(matrix=mat)
            yield Image.frombytes("RGB", (map.width, map.height), map.samples)

    def delete_page(self, page: int):
        """Deletes a specific page by index and updates the total page count."""
        try:
            self.doc.delete_page(page)
            self.pages = len(self.doc)
            return
        except Exception as e:
            raise ValueError("Page does not exist")
