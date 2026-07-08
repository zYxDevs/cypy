import os
import sys
import threading
import time
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty

import cypy.core.config as config
from cypy.core.yolo_onnx import YOLOONNX
from cypy.core.providers import create_provider
from cypy.core.translator import process_single_image, process_pdf, process_folder, process_archive
from cypy.core.version import APP_VER

from cypy.gui.widgets import FileChooserPopup, StdoutRedirector

class CYPYApp(App):
    app_version = StringProperty(APP_VER)

    def build(self):
        self.title = "CYPY Manga Translator"
        self.yolo_model = None
        self.translating = False
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'favicon.png')
        if os.path.exists(icon_path):
            self.icon = icon_path
            
        # Kivy secara otomatis memuat berkas yang ditunjuk oleh `self.kv_file`
        # sebelum fungsi ini dipanggil, dan menyimpannya di `self.root`.
        # Oleh karena itu, kita hanya perlu mengembalikan `self.root` saja.
        return self.root

    def on_start(self):
        # Redirect stdout and stderr to the log panel in the GUI
        sys.stdout = StdoutRedirector(self.append_log)
        sys.stderr = StdoutRedirector(self.append_log)
        
        # Load config details from config.py and update GUI widgets
        self.load_settings_into_ui()
        
        # Request Android permissions if running on Android
        from kivy.utils import platform
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_MEDIA_IMAGES
                ])
            except Exception as e:
                print(f"[Android] Error requesting permissions: {e}")
        
        # Bind Drag & Drop berkas ke Jendela GUI
        from kivy.core.window import Window
        Window.bind(on_drop_file=self._on_file_drop)
        
        # Initialize YOLO in the background
        threading.Thread(target=self.load_yolo_model, daemon=True).start()

    def _on_file_drop(self, window, file_path, *args):
        # Decode path jika bertipe bytes (tergantung versi Kivy/OS)
        if isinstance(file_path, bytes):
            decoded_path = file_path.decode('utf-8', errors='ignore')
        else:
            decoded_path = str(file_path)
            
        decoded_path = decoded_path.strip('"\' ')
        self.root.ids.path_input.text = decoded_path
        self.append_log(f"Dropped source: {decoded_path}\n")

    def load_settings_into_ui(self):
        # 1. Target Language
        lang = config.TARGET_LANGUAGE or "Indonesian"
        self.root.ids.lang_spinner.text = lang
        
        # 2. Provider Mapping
        provider_name = config.LLM_PROVIDER.lower()
        provider_text_map = {
            "gemini": "Google Gemini",
            "openai": "OpenAI",
            "zen": "Zen (opencode.ai)",
            "opencodego": "OpenCode Go",
            "openrouter": "OpenRouter",
            "custom": "Custom"
        }
        self.root.ids.provider_spinner.text = provider_text_map.get(provider_name, "Google Gemini")
        
        # 3. SFX Mode
        sfx_mode = config.FILTER_SFX_MODE
        self.root.ids.sfx_spinner.text = sfx_mode
        
        # 4. Load API and Model info based on provider
        self.update_provider_fields(provider_name)

    def update_provider_fields(self, provider_code):
        api_key, model_name = config.get_provider_config(provider_code)
        self.root.ids.api_key_input.text = api_key
        self.root.ids.model_input.text = model_name
        
        # Disable/Enable custom base URL
        if provider_code == 'custom':
            self.root.ids.base_url_label.disabled = False
            self.root.ids.base_url_input.disabled = False
            self.root.ids.base_url_input.text = config.CUSTOM_BASE_URL
        else:
            self.root.ids.base_url_label.disabled = True
            self.root.ids.base_url_input.disabled = True
            self.root.ids.base_url_input.text = ''

    def on_lang_changed(self, value):
        config.TARGET_LANGUAGE = value
        config.save_settings()
        self.append_log(f"Target language updated to: {value}\n")

    def on_provider_changed(self, value):
        provider_map = {
            "Google Gemini": "gemini",
            "OpenAI": "openai",
            "Zen (opencode.ai)": "zen",
            "OpenCode Go": "opencodego",
            "OpenRouter": "openrouter",
            "Custom": "custom"
        }
        provider_code = provider_map.get(value, "gemini")
        config.LLM_PROVIDER = provider_code
        config.save_settings()
        
        self.update_provider_fields(provider_code)
        self.append_log(f"Provider updated to: {value}\n")

    def on_api_key_changed(self, value):
        provider_code = config.LLM_PROVIDER
        
        # Update config fields dynamically
        if provider_code == "gemini": config.GEMINI_API_KEY = value
        elif provider_code == "openai": config.OPENAI_API_KEY = value
        elif provider_code == "zen": config.ZEN_API_KEY = value
        elif provider_code == "opencodego": config.OPENCODEGO_API_KEY = value
        elif provider_code == "openrouter": config.OPENROUTER_API_KEY = value
        elif provider_code == "custom": config.CUSTOM_API_KEY = value
        
        config.save_settings()

    def on_model_changed(self, value):
        provider_code = config.LLM_PROVIDER
        
        if provider_code == "gemini": config.MODEL_GEMINI = value
        elif provider_code == "openai": config.MODEL_OPENAI = value
        elif provider_code == "zen": config.MODEL_ZEN = value
        elif provider_code == "opencodego": config.MODEL_OPENCODEGO = value
        elif provider_code == "openrouter": config.MODEL_OPENROUTER = value
        elif provider_code == "custom": config.MODEL_CUSTOM = value
        
        config.save_settings()

    def on_base_url_changed(self, value):
        if config.LLM_PROVIDER == "custom":
            config.CUSTOM_BASE_URL = value
            config.save_settings()

    def on_sfx_changed(self, value):
        config.FILTER_SFX_MODE = value
        self.append_log(f"SFX Mode updated to: {value}\n")

    def load_yolo_model(self):
        try:
            # Check model paths
            base_model_path, _ = os.path.splitext(config.MODEL_YOLO)
            if not os.path.exists(config.MODEL_YOLO) and not os.path.exists(base_model_path + ".dat"):
                self.set_status('YOLO Missing!', (0.9, 0.2, 0.2, 1))
                self.append_log("[!] YOLO model file not found in assets!\n")
                return
                
            self.yolo_model = YOLOONNX(config.MODEL_YOLO)
            self.set_status('Ready', (0.06, 0.73, 0.51, 1)) # Emerald green status
        except Exception as e:
            self.set_status('Error loading YOLO', (0.9, 0.2, 0.2, 1))
            self.append_log(f"[!] Error loading YOLO model: {e}\n")

    def open_file_selector(self, select_mode):
        def callback(selected_path):
            self.root.ids.path_input.text = selected_path
            self.append_log(f"Selected source: {selected_path}\n")
            
        popup = FileChooserPopup(select_mode=select_mode, callback=callback)
        popup.open()

    def show_info_popup(self):
        from cypy.gui.widgets import InfoPopup
        popup = InfoPopup()
        popup.open()

    def open_url(self, url):
        import webbrowser
        try:
            webbrowser.open(url)
            self.append_log(f"Opening URL: {url}\n")
        except Exception as e:
            self.append_log(f"[!] Failed to open URL: {e}\n")

    def append_log(self, text):
        def update(dt):
            self.root.ids.log_output.text += text
            # Auto scroll to bottom
            self.root.ids.log_output.cursor = (0, len(self.root.ids.log_output.text))
        Clock.schedule_once(update)

    def set_status(self, text, color):
        def update(dt):
            self.root.ids.status_label.text = text
            self.root.ids.status_label.color = color
        Clock.schedule_once(update)

    def start_translation(self):
        if self.translating:
            self.append_log("Translation already in progress...\n")
            return
            
        input_path = self.root.ids.path_input.text.strip()
        if not input_path:
            self.append_log("[!] Please select a file or folder first.\n")
            return
            
        if self.yolo_model is None:
            self.append_log("[!] Please wait for the YOLO model to finish loading.\n")
            return
            
        self.translating = True
        self.root.ids.translate_btn.text = 'TRANSLATING...'
        self.root.ids.translate_btn.background_color = (0.3, 0.3, 0.3, 1)
        self.root.ids.translate_btn.disabled = True
        
        # Run translation in a separate thread so the GUI does not freeze
        threading.Thread(target=self.run_translation_task, args=(input_path,), daemon=True).start()

    def run_translation_task(self, input_path):
        try:
            self.set_status('Translating...', (0.9, 0.6, 0.2, 1))
            
            # Setup active LLM provider
            provider_code = config.LLM_PROVIDER
            api_key, model_name = config.get_provider_config(provider_code)
            
            extra = {}
            if provider_code == 'custom':
                extra['base_url'] = config.CUSTOM_BASE_URL
                
            provider = create_provider(provider_code, api_key=api_key, model_name=model_name, **extra)
            target_lang = config.TARGET_LANGUAGE or "Indonesian"
            
            start_time = time.time()
            
            if os.path.isdir(input_path):
                process_folder(input_path, self.yolo_model, provider=provider, target_language=target_lang)
            elif os.path.exists(input_path):
                if input_path.lower().endswith(".pdf"):
                    process_pdf(input_path, self.yolo_model, provider=provider, target_language=target_lang)
                elif input_path.lower().endswith(('.zip', '.cbz', '.rar', '.cbr')):
                    process_archive(input_path, self.yolo_model, provider=provider, target_language=target_lang)
                elif input_path.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                    process_single_image(input_path, self.yolo_model, provider=provider, target_language=target_lang)
                else:
                    self.append_log("[!] Unsupported file format.\n")
            else:
                self.append_log("[!] Selected path does not exist.\n")
                
            elapsed = time.time() - start_time
            self.append_log(f"\n[Timer] Translation completed in {elapsed:.1f}s!\n")
            
        except Exception as e:
            self.append_log(f"[!] Error during translation: {e}\n")
            
        finally:
            self.translating = False
            
            def reset_btn(dt):
                self.root.ids.translate_btn.text = 'TRANSLATE NOW'
                self.root.ids.translate_btn.background_color = (0.86, 0.15, 0.47, 1)
                self.root.ids.translate_btn.disabled = False
                self.set_status('Ready', (0.06, 0.73, 0.51, 1))
                
            Clock.schedule_once(reset_btn)
