from pathlib import Path

import fitz
from PIL import Image,ImageTk

class pdf_handler:
    def doc_reload(self):
        self.doc = fitz.open(self.path)
        self.pages = len(self.doc)

    def __init__(self,path:Path):
         self.path=path
         self.current_page=0
         self.doc = fitz.open(self.path)
         self.pages=len(self.doc)


    def get_pdf_page(self):
         if self.current_page>=self.pages:
             return
         output=self.doc[self.current_page]
         self.current_page=self.current_page+1
         return output.get_text()

    def convert_to_pic(self):
        for page in self.doc:
            mat = fitz.Matrix(0.35, 0.35)
            map=page.get_pixmap(matrix=mat)
            yield Image.frombytes("RGB",(map.width,map.height),map.samples)

    def delete_page(self,page:int):
        self.doc.delete_page(page)
        self.pages = len(self.doc)





