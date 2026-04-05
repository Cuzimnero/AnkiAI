import os
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from ui.app import App


class details_window(ctk.CTkToplevel):
    def __init__(self, app_instance: App):
        """Starts config page when a file is selected """
        super().__init__(app_instance)
        self.resizable(False, False)
        self.app_instance = app_instance
        self.title("Config")
        self.geometry("400x550")
        self.attributes("-topmost", True)
        self.after(200, lambda: self.iconbitmap(str(self.app_instance.icon_path)))
        self.file_frame = ctk.CTkFrame(self, border_color="#4a4a4a", border_width=4, width=380, height=140)
        self.file_label_frame = ctk.CTkFrame(self.file_frame, border_color="#4a4a4a", border_width=4, width=100,
                                             height=25)
        self.app_instance.generator.set_pdf_handler(self.app_instance.selected_file)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Creates file frame giving the opportunity to see and  change the selected file
        ctk.CTkLabel(self.file_label_frame, text="File", font=("Arial", 16, "bold"), width=20, height=25).pack(pady=5)
        file_name = os.path.basename(app_instance.selected_file)[0:20]
        if len(os.path.basename(self.app_instance.selected_file)) > 20:
            file_name = file_name + "..."
        self.file_button = (
            ctk.CTkButton(self.file_frame, text=str(file_name),
                          command=lambda: self.app_instance.main_ui.select_file(False),
                          fg_color="green",
                          hover_color="darkgreen", width=290, height=40, border_color="#004d00", border_width=5,
                          corner_radius=80))
        self.reload_file_button = ctk.CTkButton(self.file_frame, text="↻", width=40, height=40, corner_radius=20,
                                                fg_color="green", hover_color="darkgreen", command=self.execute_reload,
                                                border_color="#004d00", border_width=5)

        # Creates exclude frame which opens the exclude page ui and shows excluded pages
        self.exclude_frame = ctk.CTkFrame(self, border_color="#4a4a4a", border_width=4, width=380, height=45)
        self.exclude_textbox = ctk.CTkTextbox(self.exclude_frame, width=200, height=40, state="disabled")
        self.exclude_button = (
            ctk.CTkButton(self.exclude_frame, text="Exclude pages", corner_radius=32,
                          command=self.app_instance.create_exclude_window,
                          width=25))

        # Creates context frame giving the opportunity to select the deck name and giving context for card generation
        self.context_frame = ctk.CTkFrame(self, border_color="#4a4a4a", border_width=4, width=380, height=120)
        self.context_label_frame = ctk.CTkFrame(self.context_frame, border_color="#4a4a4a", border_width=4, width=130,
                                                height=25)
        self.context_label = ctk.CTkLabel(self.context_label_frame, text="Deck-Name", font=("Arial", 16, "bold"),
                                          width=20, height=25)
        self.context_text = ctk.CTkTextbox(self.context_frame, width=380, height=50)

        # Creates language frame to choose the card language
        self.language_frame = ctk.CTkFrame(self, border_color="#4a4a4a", border_width=4, width=380, height=50)
        self.language_info = ctk.CTkLabel(self.language_frame, text="Choose language:", font=("Arial", 16, "bold"))
        self.lang_switch = ctk.CTkOptionMenu(self.language_frame, values=["Default", "English", "Spanish", "German"])
        self.info_label = ctk.CTkLabel(self, text="generate cards", text_color="green")

        # Finish button to start the card generation process
        self.start_btn = ctk.CTkButton(self, text="generate cards",
                                       fg_color="green", hover_color="darkgreen",
                                       command=self.app_instance.start_generation, border_color="#004d00",
                                       border_width=5,
                                       corner_radius=40, width=200, height=40)

    def execute_reload(self):
        """reloads document and exclude textbox"""
        self.app_instance.generator.handler.doc_reload()
        self.reload_excludes_textbox()
        self.clear_deleted_pages()

    def clear_deleted_pages(self):
        if self.app_instance.pages_to_delete_sorted and self.app_instance.exclude_window.deleted_pages:
            self.app_instance.pages_to_delete_sorted.clear()
            self.app_instance.exclude_window.deleted_pages.clear()

    def show(self):
        self.file_frame.pack(pady=10)
        self.file_label_frame.pack(pady=(5, 0))

        self.exclude_frame.pack(pady=5)
        self.context_frame.pack(pady=5)
        self.language_frame.pack(pady=5)
        self.language_info.pack(pady=5, side="left", padx=(60, 0))

        self.file_button.pack(pady=20, padx=10, side="left")
        self.reload_file_button.pack(side="right", padx=(4, 15))

        self.exclude_button.pack(pady=5, side="left", padx=10)
        self.exclude_textbox.pack(pady=5, padx=10, side="right")

        self.context_label_frame.pack(pady=5)
        self.context_label.pack(pady=5)
        self.context_text.pack(pady=10, padx=20)
        self.lang_switch.pack(pady=10, side="right", padx=10)

        self.start_btn.pack(pady=20)

        self.file_frame.pack_propagate(False)
        self.exclude_frame.pack_propagate(False)
        self.context_frame.pack_propagate(False)
        self.context_label_frame.pack_propagate(False)
        self.language_frame.pack_propagate(False)

    def reload_excludes_textbox(self):
        self.deleted_pages = []
        self.exclude_textbox.configure(state="normal")
        self.exclude_textbox.delete(1.0, "end")
        self.exclude_textbox.configure(state="disabled")

    def start_progress_bar(self):
        self.bar = ctk.CTkProgressBar(self, orientation="horizontal", progress_color="#5353ec",
                                      determinate_speed=0.5, border_color="blue", fg_color="#3B8ED0")
        self.bar.pack(pady=10)
        self.bar.start()
        self.info_label = ctk.CTkLabel(self, text="generating cards ...", text_color="green")
        self.info_label.pack(pady=5)

    def on_closing(self):
        self.app_instance.main_ui.file_btn.configure(state="normal")
        self.app_instance.main_ui.chooseMod.configure(state="normal")
        if self.app_instance.main_ui.localMod is not None:
            self.app_instance.main_ui.localMod.configure(state="normal")
        self.destroy()
