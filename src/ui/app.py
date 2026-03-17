import os
import sys
from pathlib import Path
import dotenv
import image
import openai
import fitz
import customtkinter as ctk
from PIL.ImageOps import expand
from customtkinter import CTkFrame
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog, messagebox
from ai.anki_gen import AnkiGen
from handler.anki_handler import anki_handler
import genanki
import ctypes
import threading
import queue
from handler.pdf_handler import pdf_handler

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
        self.generator = AnkiGen()
        self.deleted_pages = []
        self.icon_path=base_path/"src"/"ui"/"logo.ico"
        super().__init__()
        self.iconbitmap(str(self.icon_path))

        self.title("Anki Gen")
        self.geometry("600x500")
        ctk.set_appearance_mode("dark")
        self.key_file=base_path / ".env"
        self.selected_file = None

        #Checking for api key
        if self.key_file.exists():
            self.api_key = self.key_file.read_text().strip()
            self.show_main_menu()
        else:
            self.ask_for_key()

    def ask_for_key(self):
        """Asking for and safe api key dialog"""
        self.key_frame = ctk.CTkFrame(self)
        self.key_frame.pack(expand=True, fill="both")

        self.label = ctk.CTkLabel(self.key_frame, text="ENTER THE KEY", font=("System", 24, "bold"))
        self.label.pack(pady=30)

        self.key_entry = ctk.CTkEntry(self.key_frame, placeholder_text="Your API-Key...", width=300, show="*")
        self.key_entry.pack(pady=10)

        self.btn_login = ctk.CTkButton(self.key_frame, text="Login", command=self.login_success)
        self.btn_login.pack(pady=20)

    def login_success(self):
        """Safes api key when entered to env file"""
        key = self.key_entry.get()
        input = f"DEEPSEEK_API_KEY={key}"
        self.key_file.write_text(input,encoding="utf-8")
        self.key_frame.destroy()
        self.show_main_menu()

    def show_main_menu(self):
        """Shows primary landing page """
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both")

        self.title_label = ctk.CTkLabel(self.main_frame, text="ANKI GEN",
                                        font=ctk.CTkFont(family="Courier", size=50, weight="bold"),
                                        text_color="#3498db")
        self.title_label.pack(pady=40)

        self.file_btn = ctk.CTkButton(self.main_frame, text="Choose File",
                                      height=60, width=300, corner_radius=10,
                                      command=lambda : self.select_file(True))
        self.file_btn.pack(pady=20)

    def select_file(self,kind:bool):
        """ Starts file selection dialog. In context to two different cases 1. called  by the main page and 2. called by the details window"""
        if not kind:
            path = filedialog.askopenfilename(filetypes=[("PDF-files", "*.pdf")], parent=self.details_window)
            self.reload_excludes_textbox()
        else:
            path = filedialog.askopenfilename(filetypes=[("PDF-files", "*.pdf")], parent=self.main_frame)

        if path:
            self.generator.set_pdf_handler(Path(path))
            self.selected_file = path
            if(kind == True):
                self.open_details_window()
                return

            file_name = os.path.basename(self.selected_file)[0:20]
            if len(os.path.basename(self.selected_file)) > 20:
                file_name = file_name + "..."
            self.file_button.configure(text=file_name)
# Starts details_window_interface
    def open_details_window(self):
        """Starts config page when a file is selected """
        self.details_window = ctk.CTkToplevel(self)
        self.details_window.title("Config")
        self.details_window.geometry("400x500")
        self.details_window.attributes("-topmost", True)
        self.details_window.after(200, lambda: self.details_window.iconbitmap(str(self.icon_path)))

        file_frame=ctk.CTkFrame(self.details_window,border_color="#4a4a4a",border_width=4,width=380,height=140)
        file_frame.pack_propagate(False)
        file_frame.pack(pady=10)
        file_label_frame=ctk.CTkFrame(file_frame,border_color="#4a4a4a",border_width=4,width=100,height=25)
        file_label_frame.pack(pady=(5, 0))
        file_label_frame.pack_propagate(False)

        #Creates file frame giving the opportunity to see and  change the selected file
        ctk.CTkLabel(file_label_frame, text="File", font=("Arial", 16, "bold"),width=20,height=25).pack(pady=5)
        file_name = os.path.basename(self.selected_file)[0:20]
        if len(os.path.basename(self.selected_file) )> 20:
            file_name=file_name+"..."
        self.file_button=(ctk.CTkButton(file_frame, text=str(file_name),command=lambda :self.select_file(False),fg_color="green",hover_color="darkgreen",width=290,height=40,border_color="#004d00",border_width=5,corner_radius=80))
        self.file_button.pack(pady=20,padx=10,side="left")
        self.reload_file_button=ctk.CTkButton(file_frame, text="↻",width=40,height=40,corner_radius=20,fg_color="green",hover_color="darkgreen",command=self.execute_reload,border_color="#004d00",border_width=5)
        self.reload_file_button.pack(side="right",padx=(4,15))

        #Creates exclude frame which opens the exclude page ui and shows excluded pages
        exclude_frame=ctk.CTkFrame(self.details_window,border_color="#4a4a4a",border_width=4,width=380,height=45)
        exclude_frame.pack()
        self.exclude_textbox = ctk.CTkTextbox(exclude_frame, width = 200, height = 40,state="disabled")
        self.exclude_textbox.pack(pady=5, padx=10,side="right")
        exclude_frame.pack_propagate(False)
        self.exclude_button=(ctk.CTkButton(exclude_frame,text="Exclude pages",corner_radius=32,command=self.open_exclude_window,width=25))
        self.exclude_button.pack(pady=5,side="left",padx=10)

        #Creates context frame giving the opportunity to select the deck name and giving context for card generation
        context_frame=ctk.CTkFrame(self.details_window,border_color="#4a4a4a",border_width=4,width=380,height=120)
        context_frame.pack_propagate(False)
        context_frame.pack(pady=5)
        context_label_frame=ctk.CTkFrame(context_frame,border_color="#4a4a4a",border_width=4,width=130,height=25)
        context_label_frame.pack_propagate(False)
        context_label_frame.pack(pady=5)
        ctk.CTkLabel(context_label_frame, text="Context", font=("Arial", 16, "bold"),width=20,height=25).pack(pady=5)
        self.context_text = ctk.CTkTextbox(context_frame, width=380, height=50)
        self.context_text.pack(pady=10, padx=20)

        #Creates language frame to choose the card language
        language_frame=ctk.CTkFrame(self.details_window,border_color="#4a4a4a",border_width=4,width=380,height=50)
        language_frame.pack_propagate(False)
        language_frame.pack(pady=5)
        ctk.CTkLabel(language_frame, text="Choose language:",font=("Arial", 16, "bold")).pack(pady=5,side="left",padx=(60,0))
        self.lang_switch = ctk.CTkOptionMenu(language_frame, values=["Default", "English", "Spanish","German"])
        self.lang_switch.pack(pady=10,side="right",padx=10)

        self.label=ctk.CTkLabel(self.details_window,text="generate cards",text_color="green")

        #Finish button to start the card generation process
        self.start_btn = ctk.CTkButton(self.details_window, text="generate cards",
                                       fg_color="green", hover_color="darkgreen",
                                       command=self.start_generation,border_color="#004d00",border_width=5,corner_radius=40,width=200,height=40)
        self.start_btn.pack(pady=20)
        
    def open_exclude_window(self):
        """Starts page to exclude pdf pages from the card generation."""
        self.exclude_window = ctk.CTkToplevel(self.details_window)
        self.exclude_window.title("Exclude pages")
        self.exclude_window.focus_force()
        self.exclude_window.grab_set()
        self.exclude_window.lift()
        self.exclude_window.geometry("820x950")
        self.exclude_window.attributes("-topmost", True)
        self.exclude_window.after(200, lambda: self.exclude_window.iconbitmap(str(self.icon_path)))

        self.page_states={}

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.exclude_window,
            width=720,
            height=800,
            label_text="Pages"
        )

        self.loading_label = ctk.CTkLabel(self.exclude_window, text="Loading pages...", font=("Arial", 24, "bold"), text_color="green")
        self.loading_label.pack(expand=True)

        self.finish_button = ctk.CTkButton(self.exclude_window, anchor="s", text="Finish", corner_radius=32, command=self.exclude_window_finish,border_color="#3B8ED0",fg_color="#2B2B2B",hover_color="#3B8ED0",text_color="white",font=("Segoe UI", 13, "bold"),width=400,height=300)
        
        #initalite queue for pdf pages
        self.image_queue = queue.Queue()
        self.current_page_index = 0
        self.columns = 2
        
        threading.Thread(target=self._image_generation_thread, daemon=True).start()
        self.load_next_page()

    def _image_generation_thread(self):
        """Adds pdf pages to queue for loading in the window"""
        for image in self.generator.handler.convert_to_pic():
            self.image_queue.put(image)
        self.image_queue.put(None)

    def load_next_page(self):
        """handles page loading for exclude ui loads 20 pages in one iteration"""

        if not self.exclude_window.winfo_exists():
            return

        batch_size = 20
        images_loaded = False

        for _ in range(batch_size):
            try:
                image = self.image_queue.get_nowait()
            except queue.Empty:
                break

             #function stops at the last image
            if image is None:
                if self.loading_label.winfo_exists():
                    self.loading_label.destroy()
                self.scroll_frame.pack(padx=20, pady=20, fill="both", expand=True)
                self.finish_button.pack(pady=20)
                return

            images_loaded = True
            page_num = self.current_page_index + 1
            row = self.current_page_index // self.columns
            col = self.current_page_index % self.columns
            self.current_page_index += 1
            orig_w, orig_h = image.size

            state = ctk.BooleanVar(value=False)
            self.page_states[page_num] = state
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(orig_w, orig_h))
            
            cell_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            cell_frame.grid(row=row, column=col, padx=10, pady=10)

            checkbox = ctk.CTkCheckBox(cell_frame, text=f"exclude {page_num}", text_color="green", font=("Arial", 14, "bold"), variable=state)
            checkbox.pack()
            img_label = ctk.CTkLabel(cell_frame, image=ctk_img, text="")
            img_label._safe_image_reference = ctk_img
            img_label.pack(pady=10)

        if images_loaded:
            self.exclude_window.update_idletasks()
            #recursive call for next iteration
        self.exclude_window.after(10, self.load_next_page)

    def exclude_window_finish(self):
            """safes deleted pages for removing and closes  exclude window"""
            self.pages_to_delete_sorted = [page_num for page_num, var in self.page_states.items() if var.get()]
            for page_num in self.pages_to_delete_sorted:
                if page_num not in self.deleted_pages:
                    self.deleted_pages.append(page_num)
            self.deleted_pages.sort()
            self.pages_to_delete_sorted.sort(reverse=True)
            output_str=",".join(map(str,self.deleted_pages))
            self.exclude_textbox.configure(state="normal")
            self.exclude_textbox.delete(1.0,"end")
            self.exclude_textbox.insert("end",output_str)
            self.exclude_textbox.configure(state="disabled")
            self.exclude_window.destroy()

    def execute_reload(self):
        """reloads document and exclude textbox"""
        self.generator.handler.doc_reload()
        self.reload_excludes_textbox()

    def reload_excludes_textbox(self):
        self.deleted_pages = []
        self.exclude_textbox.configure(state="normal")
        self.exclude_textbox.delete(1.0, "end")
        self.exclude_textbox.configure(state="disabled")

    def start_generation(self):
        """updates detail page for generation of cards, initialize generation"""
        self.start_btn.configure(state="disabled",text="Generating cards...")
        thread=threading.Thread(target=self.run_gen)
        self.bar=ctk.CTkProgressBar(self.details_window,orientation="horizontal",progress_color="#5353ec",determinate_speed=0.5,border_color="blue",fg_color="#3B8ED0")
        self.bar.pack(pady=10)
        self.bar.start()
        self.label = ctk.CTkLabel(self.details_window, text="generating cards ...", text_color="green")
        self.label.pack(pady=10)
        thread.start()

    def run_gen(self):
        """generates cards"""
        for page in self.deleted_pages:
            self.generator.handler.delete_page(page - 1)
        context=self.context_text.get("1.0","end-1c").strip()
        cards= self.generator.createCards(context,self.lang_switch.get())
        handler=anki_handler(context)
        handler.add_fields(cards)
        output_path=base_path/"output"
        output_path.mkdir(exist_ok=True)
        handler.safe_tofile(output_path)
        self.after(0,self.finish)

    def finish(self):
        """finishes generating cards"""
        if(self.details_window.winfo_exists()):
            self.details_window.destroy()
        messagebox.showinfo("AnkiGen", "Generation successful!")


if __name__ == "__main__":
    app = App()
    app.mainloop()