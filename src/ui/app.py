import ctypes
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import ollama
from dotenv import load_dotenv
from tkinterdnd2 import TkinterDnD

from ai.anki_gen import AnkiGen
from handler.anki_handler import anki_handler
from ui.details_window import details_window
from ui.exclude_window import ExcludeWindow
from ui.main_ui import main_ui
from ui.verify import verification

# Set a unique AppUserModelID to ensure the app has its own taskbar icon on Windows
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AnkiGen")
except Exception:
    pass

# Determine base path for resources (handles both standard script and PyInstaller .exe)
if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent.parent.parent

# Add the project root to sys.path to ensure internal modules can be imported correctly
if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))


# Application interface
class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        """Initializes the main application, window settings, and authentication state."""
        self.pages_to_delete_sorted = []
        self.main_ui = None
        log_filename = datetime.now().ctime().replace(":", r"-") + ".log"
        logging_path = base_path / "logs"
        logging_path.mkdir(exist_ok=True, parents=True)
        log_file = logging_path / log_filename
        logging.basicConfig(
            filename=str(log_file),
            filemode='a',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            force=True
        )

        self.verification = verification(self)
        self.localMod = None
        self.deleted_pages = []
        self.icon_path = base_path / "src" / "ui" / "logo.ico"
        super().__init__()
        self.iconbitmap(str(self.icon_path))

        self.title("Anki Gen")
        self.geometry("600x500")
        ctk.set_appearance_mode("dark")
        self.key_file = base_path / ".env"
        self.selected_file = None
        self.generator = AnkiGen(1, "")

        self.logger = logging.getLogger(__name__)
        self.logger.info("Logger started")

        # Checking for api key, loading safed key and data
        if self.key_file.exists():
            load_dotenv()
            self.chooseMod_state = os.getenv("CHOOSE_MOD_STATE", "normal")
            self.key_valid = os.getenv("KEY_VALID", "False") == "True"
            self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
            self.text_for_add_key = f"Your API Key {self.api_key}"
            self.start()
        else:
            self.verification.ask_for_key("ENTER THE KEY", False, "I dont have a key")

    def start(self):
        self.main_ui = main_ui(self)
        self.main_ui.show()

    def selectModel(self, choice):
        """ Initializes chosen Model. If Ollama is selected, it fetches installed local models and displays a selection menu."""
        values = {"DeepSeek": 1, "Local Model (Ollama)": 2}
        model = values.get(choice)

        if model == 2:
            try:
                response = ollama.list()
                installed_models = [m.model for m in response.models]
                if self.main_ui and self.main_ui.main_frame.winfo_exists():
                    self.main_ui.selectModel(choice, installed_models)
                if installed_models:
                    default_model = installed_models[0]
                else:
                    self.main_ui.file_btn.configure(state="disabled")
                    if hasattr(self.main_ui, "localMod"):
                        self.main_ui.localMod.configure(values=["You have no models installed!"])
                        self.main_ui.localMod.set("You have no models installed!")
                    default_model = "no models installed"
                    messagebox.showwarning("Warning", "You have no models installed!")

                self.generator = AnkiGen(model, default_model)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            if self.main_ui and hasattr(self.main_ui, "file_btn"):
                if self.main_ui.file_btn.winfo_exists():
                    self.main_ui.file_btn.configure(state="normal")
            self.main_ui.destroy_local_mod()
            self.generator = AnkiGen(model, "")

    def set_model(self, model: str):
        self.generator.set_model(model)

    def create_details_window(self):
        self.details_window = details_window(self)
        self.details_window.show()
        self.deleted_pages.clear()

    def create_exclude_window(self):
        self.exclude_window = ExcludeWindow(self)
        self.exclude_window.show()

    def handle_pdf_error(self):
        self.details_window.withdraw()
        self.details_window.destroy()
        messagebox.showerror("Error", f"PDF Error Try again !")
        self.main_ui.file_btn.configure(state="normal")

    def start_generation(self):
        """updates detail page for generation of cards, initialize generation"""
        self.details_window.start_btn.configure(state="disabled", text="Generating cards...")
        thread = threading.Thread(target=self.run_gen)
        self.details_window.start_progress_bar()
        self.generator.load_embedding_model()
        thread.start()

    def run_gen(self):
        """generates cards"""
        if self.generator.model == "no models installed" and self.generator.type == 2:
            messagebox.showerror("Error", "Please install a model first (e.g., 'ollama pull llama3')")
            return
        for page in self.pages_to_delete_sorted:
            try:
                self.generator.handler.delete_page(page - 1)
            except Exception as e:
                self.after(0, self.handle_pdf_error)
                return
        deck_name = self.details_window.context_text.get("1.0", "end-1c").strip()
        cards = self.generator.createCards(self.details_window.lang_switch.get(), self.details_window.info_label)
        if not cards:
            messagebox.showerror("Error", "No cards generated.")
            self.details_window.after(10, self.details_window.destroy)
            self.main_ui.file_btn.configure(state="normal")
            return
        handler = anki_handler(deck_name)
        handler.add_fields(cards)
        output_path = base_path / "output"
        output_path.mkdir(exist_ok=True)
        handler.safe_tofile(output_path)
        self.after(0, self.finish)

    def finish(self):
        """finishes generating cards"""
        if self.details_window.winfo_exists():
            self.details_window.destroy()
        self.main_ui.file_btn.configure(state="normal")
        messagebox.showinfo("AnkiGen", "Generation successful!")


if __name__ == "__main__":
    app = App()
    app.mainloop()
