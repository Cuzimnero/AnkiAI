import logging
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk
from openai import APIError, OpenAI

if TYPE_CHECKING:
    from ui.app import App


class verification:
    def __init__(self, app_instance: App):
        self.logger = logging.getLogger(__name__)
        self.key_frame = None
        self.info_label = None
        self.btn_login = None
        self.escape_button = None
        self.key_entry = None
        self.app_instance = app_instance

    def verify_deepseek_key(self, key: str):
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "This is a test call"},
                    {"role": "user", "content": "Hello"},
                ],
                stream=False
                , max_tokens=1
            )
            self.logger.info("Checked DeepSeek key: Valid")
            return True
        except APIError:
            self.logger.info("Checked DeepSeek key: not Valid")
            return False

    def ask_for_key(self, dialog_message: str, key_exist: bool, escape_message: str):
        """Asking for and safe api key dialog"""
        self.key_frame = ctk.CTkFrame(self.app_instance)
        self.key_frame.pack(expand=True, fill="both")

        self.info_label = ctk.CTkLabel(self.key_frame, text=dialog_message, font=("System", 24, "bold"))
        self.info_label.pack(pady=30)

        self.key_entry = ctk.CTkEntry(self.key_frame, placeholder_text="Your API-Key...", width=300, show="*")
        self.key_entry.pack(pady=10)

        self.btn_login = ctk.CTkButton(self.key_frame, text="Login",
                                       command=lambda: self.login_success(escape_message, key_exist))
        self.btn_login.pack(pady=10)
        self.btn_login.pack(pady=20)

        self.escape_button = ctk.CTkButton(self.key_frame, font=("System", 10, "bold"), text=escape_message,
                                           command=lambda: self.ask_for_key_action_handler(key_exist))
        self.escape_button.pack(pady=10)

    def login_success(self, escape_message: str, key_exist: bool):
        """Safes api key in env file"""
        self.app_instance.chooseMod_state = "normal"
        self.app_instance.key_valid = True
        key = self.key_entry.get().strip()
        if not self.verify_deepseek_key(key):
            messagebox.showerror("ERROR", "Your API Key is invalid")
            self.key_frame.destroy()
            self.ask_for_key("ENTER THE API KEY", key_exist, escape_message)
            return
        self.app_instance.api_key = key
        self.app_instance.text_for_add_key = f"Your API Key {self.app_instance.api_key}"
        input = f"DEEPSEEK_API_KEY={key}\nCHOOSE_MOD_STATE={self.app_instance.chooseMod_state}\nKEY_VALID={self.app_instance.key_valid} "

        self.app_instance.key_file.write_text(input, encoding="utf-8")
        self.key_frame.destroy()
        self.app_instance.start()

    def ask_for_key_action_handler(self, key_exist: bool):
        if (key_exist):
            self.key_frame.destroy()
            self.app_instance.start()
            self.app_instance.text_for_add_key = f"Your API Key {self.app_instance.api_key}"
        else:
            self.has_no_api_key()

    def has_no_api_key(self):
        self.app_instance.chooseMod_state = "disabled"
        self.app_instance.text_for_add_key = "Add DeepSeek Key"
        self.app_instance.key_valid = False
        self.key_frame.destroy()
        self.app_instance.start()
        try:
            self.app_instance.main_ui.set_choose_mod("Local Model (Ollama)")
        except ValueError as e:
            self.logger.error(e)
        self.app_instance.select_model(2)

    def addKey(self):
        self.app_instance.main_ui.destroy()
        if not self.app_instance.key_valid:
            self.ask_for_key("ENTER THE KEY", False, "I dont have a key")
        else:
            self.ask_for_key("ENTER THE NEW KEY", True, "I dont want to change the key")
