import queue
import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from ui.app import App


class ExcludeWindow(ctk.CTkToplevel):
    def __init__(self, app_instance: App):
        super().__init__(app_instance)
        self.deleted_pages = []
        self.app = app_instance
        self.title("Exclude pages")
        self.focus_force()
        self.grab_set()
        self.lift()
        self.geometry("820x950")
        self.attributes("-topmost", True)
        self.after(200, lambda: self.iconbitmap(str(self.app.icon_path)))
        self.page_states = {}

        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            width=720,
            height=800,
            label_text="Pages"
        )
        self.loading_label = ctk.CTkLabel(self, text="Loading pages...", font=("Arial", 24, "bold"),
                                          text_color="green")
        self.finish_button = ctk.CTkButton(self, anchor="s", text="Finish", corner_radius=32,
                                           command=self.exclude_window_finish, border_color="#3B8ED0",
                                           fg_color="#2B2B2B", hover_color="#3B8ED0", text_color="white",
                                           font=("Segoe UI", 13, "bold"), width=400, height=300)

        # initalize queue for pdf pages
        self.image_queue = queue.Queue()
        self.current_page_index = 0
        self.columns = 2

        threading.Thread(target=self._image_generation_thread, daemon=True).start()
        self.load_next_page()

    def _image_generation_thread(self):
        """Adds pdf pages to queue for loading in the window"""
        for image in self.app.generator.handler.convert_to_pic():
            self.image_queue.put(image)
        self.image_queue.put(None)

    def load_next_page(self):
        """handles page loading for exclude ui loads 20 pages in one iteration"""

        if not self.winfo_exists():
            return

        batch_size = 20
        images_loaded = False

        for _ in range(batch_size):
            try:
                image = self.image_queue.get_nowait()
            except queue.Empty:
                break

            # function stops at the last image
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
            TARGET_SIZE = (400, 350)
            img_w, img_h = image.size
            ratio = min(TARGET_SIZE[0] / img_w, TARGET_SIZE[1] / img_h)
            display_w = int(img_w * ratio)
            display_h = int(img_h * ratio)

            state = ctk.BooleanVar(value=False)
            self.page_states[page_num] = state
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(display_w, display_h))

            cell_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            cell_frame.grid(row=row, column=col, padx=10, pady=10)

            checkbox = ctk.CTkCheckBox(cell_frame, text=f"exclude {page_num}", text_color="green",
                                       font=("Arial", 14, "bold"), variable=state)
            checkbox.pack()
            img_label = ctk.CTkLabel(cell_frame, image=ctk_img, text="")
            img_label._safe_image_reference = ctk_img
            img_label.pack(pady=10)

        if images_loaded:
            self.update_idletasks()
            # recursive call for next iteration
        self.after(10, self.load_next_page)

    def exclude_window_finish(self):
        """safes deleted pages for removing and closes  exclude window"""
        self.app.pages_to_delete_sorted = [page_num for page_num, var in self.page_states.items() if var.get()]
        for page_num in self.app.pages_to_delete_sorted:
            if page_num not in self.app.deleted_pages:
                self.deleted_pages.append(page_num)
        self.deleted_pages.sort()
        self.app.pages_to_delete_sorted.sort(reverse=True)
        output_str = ",".join(map(str, self.deleted_pages))
        self.app.details_window.exclude_textbox.configure(state="normal")
        self.app.details_window.exclude_textbox.delete(1.0, "end")
        self.app.details_window.exclude_textbox.insert("end", output_str)
        self.app.details_window.exclude_textbox.configure(state="disabled")
        self.destroy()

    def show(self):
        self.loading_label.pack(expand=True)
