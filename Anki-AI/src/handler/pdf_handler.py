from pathlib import Path

import fitz
class pdf_handler:
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