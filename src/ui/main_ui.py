import os
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from ui.app import App


class main_ui:

    def __init__(self, app_instance: App):
        self.localMod = None
        self.app_instance = app_instance
        self.main_frame = ctk.CTkFrame(self.app_instance)
        self.addKey_button = ctk.CTkButton(self.main_frame, text=self.app_instance.text_for_add_key,
                                           fg_color="transparent",
                                           command=self.app_instance.verification.addKey, text_color="darkgreen")
        self.title_label = ctk.CTkLabel(self.main_frame, text="ANKI GEN",
                                        font=ctk.CTkFont(family="Courier", size=50, weight="bold"),
                                        text_color="#3498db")
        self.modelFrame = ctk.CTkFrame(self.main_frame, border_color="#4a4a4a", border_width=4, width=300, height=180)
        self.Modelabel = ctk.CTkLabel(self.modelFrame, text="Select Model", )
        self.chooseMod = ctk.CTkOptionMenu(self.modelFrame, values=["DeepSeek", "Local Model (Ollama)"],
                                           command=self.app_instance.selectModel,
                                           state=self.app_instance.chooseMod_state)
        self.file_btn = ctk.CTkButton(self.main_frame, text="Choose File",
                                      height=60, width=300, corner_radius=10,
                                      command=lambda: self.select_file(True))
        if not self.app_instance.key_valid:
            self.app_instance.selectModel("Local Model (Ollama)")

    def show(self):
        self.title_label.pack(pady=40)
        self.addKey_button.pack(pady=20, padx=20, anchor="se", side="bottom")
        self.main_frame.pack(expand=True, fill="both")
        self.modelFrame.pack_propagate(False)
        self.modelFrame.pack(pady=10)
        self.Modelabel.pack(pady=10)
        self.chooseMod.pack(pady=10)
        self.file_btn.pack(pady=20)

    def select_file(self, kind: bool):
        """ Starts file selection dialog. In context to two different cases 1. called  by the main page and 2. called by the details window"""
        self.file_btn.configure(state="disabled")
        self.chooseMod.configure(state="disabled")
        if self.localMod is not None:
            self.localMod.configure(state="disabled")
        if not kind:
            path = filedialog.askopenfilename(filetypes=[("PDF-files", "*.pdf")],
                                              parent=self.app_instance)
            self.app_instance.details_window.reload_excludes_textbox()
            self.app_instance.details_window.clear_deleted_pages()
        else:
            path = filedialog.askopenfilename(filetypes=[("PDF-files", "*.pdf")], parent=self.main_frame)

        if path:
            self.app_instance.generator.set_pdf_handler(Path(path))
            self.app_instance.selected_file = path
            if (kind == True):
                self.app_instance.create_details_window()
                return
            file_name = os.path.basename(self.app_instance.selected_file)[0:20]
            if len(os.path.basename(self.app_instance.selected_file)) > 20:
                file_name = file_name + "..."
            self.app_instance.details_window.file_button.configure(text=file_name)
            self.app_instance.generator.set_pdf_handler(self.app_instance.selected_file)
        else:
            self.file_btn.configure(state="normal")
            self.chooseMod.configure(state="normal")
            if self.localMod is not None:
                self.localMod.configure(state="normal")
            return

    def selectModel(self, choice, installed_models):
        """ Initializes chosen Model. If Ollama is selected, it fetches installed local models and displays a selection menu."""
        self.destroy_local_mod()
        self.localMod = ctk.CTkOptionMenu(self.modelFrame, values=installed_models,
                                          command=self.app_instance.set_model, )
        self.localMod.pack(pady=20)

    def destroy_local_mod(self):
        if hasattr(self, "localMod"):
            try:
                self.localMod.destroy()
                self.localMod = None
            except Exception:
                pass

    def destroy(self):
        self.main_frame.destroy()
