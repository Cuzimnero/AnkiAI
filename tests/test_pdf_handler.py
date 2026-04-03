import unittest
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from src.handler.pdf_handler import pdf_handler


class TestPdfHandler(unittest.TestCase):

    def setUp(self):
        # Create a dummy PDF for testing
        self.test_pdf_path = Path("test.pdf")
        self.doc = fitz.open()
        for i in range(3):
            page = self.doc.new_page()
            page.insert_text((50, 72), f"This is page {i + 1}.")
        self.doc.save(str(self.test_pdf_path))
        self.doc.close()
        # Initialize the handler for each test
        self.handler = pdf_handler(self.test_pdf_path)

    def tearDown(self):
        # Clean up the dummy PDF
        if hasattr(self, 'handler') and self.handler:
            if hasattr(self.handler, 'doc') and self.handler.doc:
                try:
                    self.handler.doc.close()
                except ValueError:
                    pass
        if self.test_pdf_path.exists():
            self.test_pdf_path.unlink()

    def test_01_initialization(self):
        """Test if the PDF handler is initialized correctly."""
        self.assertEqual(self.handler.pages, 3)
        self.assertEqual(self.handler.current_page, 0)

    def test_02_get_pdf_page(self):
        """Test if get_pdf_page returns the correct text content."""
        text = self.handler.get_pdf_page()
        self.assertIn("This is page 1.", text)
        self.assertEqual(self.handler.current_page, 1)

        text = self.handler.get_pdf_page()
        self.assertIn("This is page 2.", text)
        self.assertEqual(self.handler.current_page, 2)

        text = self.handler.get_pdf_page()
        self.assertIn("This is page 3.", text)
        self.assertEqual(self.handler.current_page, 3)

        # Test end of document
        text = self.handler.get_pdf_page()
        self.assertIsNone(text)
        self.assertEqual(self.handler.current_page, 3)

    def test_03_convert_to_pic(self):
        """Test if convert_to_pic yields the correct number of images."""
        images = list(self.handler.convert_to_pic())
        self.assertEqual(len(images), 3)
        for img in images:
            self.assertIsInstance(img, Image.Image)

    def test_04_delete_page(self):
        """Test if delete_page correctly deletes a page."""
        self.handler.delete_page(1)  # Delete the second page
        self.assertEqual(self.handler.pages, 2)

        # After deleting page 1 (0-indexed), the new page 1 should be the original page 2
        self.handler.current_page = 1
        text = self.handler.get_pdf_page()
        self.assertIn("This is page 3.", text)

        # Reload the document to verify that the page is not deleted from the file
        self.handler.doc_reload()
        self.assertEqual(self.handler.pages, 3)

    def test_05_doc_reload(self):
        """Test if doc_reload correctly reloads the document."""
        self.handler.delete_page(0)
        self.assertEqual(self.handler.pages, 2)

        # Reload the original document
        self.handler.doc_reload()
        self.assertEqual(self.handler.pages, 3)
        self.handler.current_page = 0
        text = self.handler.get_pdf_page()
        self.assertIn("This is page 1", text)


if __name__ == '__main__':
    unittest.main()
