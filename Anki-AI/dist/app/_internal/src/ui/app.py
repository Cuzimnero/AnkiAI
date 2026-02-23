import sys
from pathlib import Path
import dotenv
import openai
import fitz
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog
from ai.anki_gen import AnkiGen
from handler.anki_handler import anki_handler
import genanki
import ctypes
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AnkiGen")
except Exception:
    pass

if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent.parent.parent
if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))

class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        self.icon_path=base_path/"src"/"ui"/"logo.ico"
        super().__init__()
        try:
            self.TkdndVersion = TkinterDnD._pytkinterdnd2.TkinterDnD_Init(self)
        except Exception:
            pass
        self.iconbitmap(str(self.icon_path))

        self.title("Anki Gen Pro")
        self.geometry("600x500")
        ctk.set_appearance_mode("dark")
        self.key_file=base_path / ".env"
        self.selected_file = None
        if self.key_file.exists():
            self.api_key = self.key_file.read_text().strip()
            self.show_main_menu()
        else:
            self.ask_for_key()

    def ask_for_key(self):
        self.key_frame = ctk.CTkFrame(self)
        self.key_frame.pack(expand=True, fill="both")

        self.label = ctk.CTkLabel(self.key_frame, text="ENTER THE KEY", font=("System", 24, "bold"))
        self.label.pack(pady=30)

        self.key_entry = ctk.CTkEntry(self.key_frame, placeholder_text="Dein API-Key...", width=300, show="*")
        self.key_entry.pack(pady=10)

        self.btn_login = ctk.CTkButton(self.key_frame, text="Login", command=self.login_success)
        self.btn_login.pack(pady=20)

    def login_success(self):
        key = self.key_entry.get()
        input = f"DEEPSEEK_API_KEY={key}"
        self.key_file.write_text(input,encoding="utf-8")
        self.key_frame.destroy()
        self.show_main_menu()

    def show_main_menu(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both")

        self.title_label = ctk.CTkLabel(self.main_frame, text="ANKI GEN",
                                        font=ctk.CTkFont(family="Courier", size=50, weight="bold"),
                                        text_color="#3498db")
        self.title_label.pack(pady=40)

        self.file_btn = ctk.CTkButton(self.main_frame, text="PDF DATEI AUSWÄHLEN",
                                      height=60, width=300, corner_radius=10,
                                      command=self.select_file)
        self.file_btn.pack(pady=20)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Dateien", "*.pdf")])
        if path:
            self.selected_file = path
            self.open_details_window()

    def open_details_window(self):
        self.details_window = ctk.CTkToplevel(self)
        self.details_window.title("Konfiguration")
        self.details_window.geometry("400x550")
        self.details_window.attributes("-topmost", True)
        self.details_window.after(200, lambda: self.details_window.iconbitmap(str(self.icon_path)))
        ctk.CTkLabel(self.details_window, text="Zusätzliche Anforderungen", font=("Arial", 16, "bold")).pack(pady=10)

        self.req_text = ctk.CTkTextbox(self.details_window, width=350, height=150)
        self.req_text.pack(pady=10, padx=20)

        ctk.CTkLabel(self.details_window, text="Thema / Kontext ", font=("Arial", 14, "bold")).pack(
            pady=(10, 0))
        self.context_text = ctk.CTkTextbox(self.details_window, width=380, height=50)
        self.context_text.pack(pady=10, padx=20)
        ctk.CTkLabel(self.details_window, text="Sprache auswählen:").pack(pady=5)
        self.lang_switch = ctk.CTkOptionMenu(self.details_window, values=["Deutsch", "Englisch", "Spanisch","Default"])
        self.lang_switch.pack(pady=10)

        self.start_btn = ctk.CTkButton(self.details_window, text="Karten generieren",
                                       fg_color="green", hover_color="darkgreen",
                                       command=self.start_generation)
        self.start_btn.pack(pady=30)

    def start_generation(self):
        generator = AnkiGen()
        context=self.context_text.get("1.0","end-1c").strip()
        cards= generator.createCards(self.selected_file,context,self.lang_switch.get())
        handler=anki_handler(context)
        handler.add_fields(cards)
        output_path=base_path/base_path/"output"
        output_path.mkdir(exist_ok=True)
        handler.safe_tofile(output_path)



if __name__ == "__main__":
    app = App()
    app.mainloop()