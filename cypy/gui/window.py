import os
import sys
import queue
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image

import cypy.core.config as config
from cypy.core.yolo_onnx import YOLOONNX
from cypy.core.providers import create_provider
from cypy.core.translator import process_single_image, process_pdf, process_folder, process_archive
from cypy.core.version import APP_VER
from cypy.gui.info import InfoDialog
from cypy.gui.widgets import QueueWriteDescriptor, RetroOptionMenu

COLOR_BG = "#121212"          # Outer window background (charcoal grey)
COLOR_CARD = "#1a1a1a"        # Cards background (medium dark grey)
COLOR_WIDGET = "#121212"      # Inputs / Dropdowns / Log Textbox (recessed dark grey)
COLOR_BORDER = "#2c2c2c"      # 1px border lines
COLOR_PINK = "#db2777"        # Vibrant Magenta Pink Accent
COLOR_WHITE = "#ffffff"       # Titles and major texts
COLOR_GRAY = "#aaaaaa"        # Subdued labels
COLOR_DARK_BTN = "#2b2b2b"    # Secondary buttons (FILE, FOLDER)
COLOR_DARK_BTN_HOVER = "#3a3a3a"

class CYPYWindow(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        ctk.CTk.__init__(self)
        TkinterDnD.DnDWrapper.__init__(self)
        
        # Initialize DnD capabilities
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except Exception as e:
            try: print(f"[!] Failed to initialize drag and drop: {e}")
            except: pass
            
        # Load folder icon
        self.ic_folder = None
        self.ic_settings = None
        try:
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets')
            icon_file = os.path.join(assets_dir, 'icons', 'folder.png')
            if os.path.exists(icon_file):
                pil_img = Image.open(icon_file)
                self.ic_folder = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(20, 20))
            
            icon_settings_file = os.path.join(assets_dir, 'icons', 'settings.png')
            if os.path.exists(icon_settings_file):
                pil_img_settings = Image.open(icon_settings_file)
                self.ic_settings = ctk.CTkImage(light_image=pil_img_settings, dark_image=pil_img_settings, size=(14, 14))
        except Exception as e:
            print(f"[!] Failed to load icons: {e}")
        
        # [ANTI-GLITCH] Hide window first and set geometry centered
        try:
            self.withdraw()
            self.attributes("-alpha", 0.0)
        except Exception:
            pass
            
        self.title(f"cypy {APP_VER}")
        w_awal, h_awal = 750, 460
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (w_awal // 2)
        y = (screen_height // 2) - (h_awal // 2)
        self.geometry(f"{w_awal}x{h_awal}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        
        self.yolo_model = None
        self.yolo_loading_done = False
        self.translating = False
                
        # Main layout structure (2 Column Layout)
        self.grid_columnconfigure(0, weight=1) # Column 0 (Left Side - Inputs)
        self.grid_columnconfigure(1, weight=1) # Column 1 (Right Side - Log Console)
        self.grid_rowconfigure(0, weight=0)    # Header
        self.grid_rowconfigure(1, weight=1)    # Content Area
        
        self.create_header()
        self.create_main_panel()
        
        # Stdout/Stderr Redirector setup
        self.log_queue = queue.Queue()
        sys.stdout = QueueWriteDescriptor(self.log_queue.put, sys.__stdout__)
        sys.stderr = QueueWriteDescriptor(self.log_queue.put, sys.__stderr__)
        
        # Start queue processing
        self.after(100, self.process_log_queue)
        
        # Initialize configuration values in UI
        self.load_settings_into_ui()
        
        # Initialize YOLO in a background thread
        threading.Thread(target=self.load_yolo_model, daemon=True).start()
        
        # Clean closing protocol
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Show loading screen
        self.show_loading_screen()

    def show_loading_screen(self):
        splash = ctk.CTkToplevel(self)
        w_splash, h_splash = 250, 280
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x_pos = (screen_width // 2) - (w_splash // 2)
        y_pos = (screen_height // 2) - (h_splash // 2)
        
        splash.geometry(f"{w_splash}x{h_splash}+{x_pos}+{y_pos}")
        splash.overrideredirect(True)
        try:
            splash.attributes("-topmost", True)
        except Exception:
            pass
            
        transparent_color = "#000001"
        splash.configure(fg_color=transparent_color)
        if sys.platform == 'win32':
            try:
                splash.attributes("-transparentcolor", transparent_color)
            except Exception:
                pass

        # Border for splash screen
        card_frame = ctk.CTkFrame(splash, fg_color="#121212", corner_radius=0, border_width=1, border_color="#333333")
        card_frame.pack(fill="both", expand=True, padx=2, pady=2)

        frame_pusat = ctk.CTkFrame(card_frame, fg_color="transparent")
        frame_pusat.pack(expand=True, fill="both", padx=15, pady=20)

        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'favicon.ico')
        try:
            if os.path.exists(icon_path):
                img_asli = Image.open(icon_path)
                img_logo = ctk.CTkImage(light_image=img_asli, dark_image=img_asli, size=(90, 90))
                lbl_logo = ctk.CTkLabel(frame_pusat, text="", image=img_logo)
                lbl_logo.pack(pady=(5, 10))
            else:
                ctk.CTkLabel(frame_pusat, text="◇", font=("Terminal", 60), text_color="#db2777").pack(pady=(5, 10))
        except Exception as e:
            print(f"Error loading splash logo: {e}")
            ctk.CTkLabel(frame_pusat, text="◇", font=("Terminal", 60), text_color="#db2777").pack(pady=(5, 10))

        ctk.CTkLabel(frame_pusat, text="cypy", font=("Terminal", 22, "bold"), text_color="#db2777").pack(pady=(0, 2))
        lbl_status = ctk.CTkLabel(frame_pusat, text="Initializing...", font=("Terminal", 10, "italic"), text_color="#888888")
        lbl_status.pack(pady=(0, 15))

        progress_loading = ctk.CTkProgressBar(frame_pusat, width=180, height=4, corner_radius=0, progress_color="#db2777", fg_color="#2b2b2b")
        progress_loading.pack()
        progress_loading.set(0)

        def run_loading(value=0):
            if value < 0.9:
                progress_loading.set(value)
                lbl_status.configure(text="Loading neural engine...")
                splash.after(15, lambda: run_loading(value + 0.02))
            else:
                base_model_path, _ = os.path.splitext(config.MODEL_YOLO)
                model_missing = not os.path.exists(config.MODEL_YOLO) and not os.path.exists(base_model_path + ".dat")
                
                if getattr(self, 'yolo_loading_done', False) or model_missing:
                    if value <= 1.0:
                        progress_loading.set(value)
                        lbl_status.configure(text="Engine Ready!" if self.yolo_model else "Engine Failed!")
                        splash.after(15, lambda: run_loading(value + 0.05))
                    else:
                        try:
                            self.deiconify()
                            self.lift()
                            self.focus_force()
                            self.attributes("-topmost", True)
                            self.after(50, lambda: self.attributes("-topmost", False))
                            self.update()
                        except Exception:
                            pass
                        splash.destroy()
                        try:
                            self.attributes("-alpha", 1.0)
                        except Exception:
                            pass
                        
                        # Set main window iconbitmap safely
                        try:
                            if os.path.exists(icon_path):
                                self.iconbitmap(icon_path)
                        except Exception:
                            pass
                else:
                    progress_loading.set(0.9)
                    lbl_status.configure(text="Initializing YOLO model...")
                    splash.after(50, lambda: run_loading(0.9))

        splash.after(200, lambda: run_loading(0))

    def create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_BG, height=38, corner_radius=0, border_width=1, border_color=COLOR_BORDER)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)
        header_frame.grid_columnconfigure(2, weight=0)
        
        # Title Container for Side-by-Side Logo and Title
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.grid(row=0, column=0, padx=12, pady=6, sticky="w")
        
        lbl_logo = ctk.CTkLabel(
            title_container, text="◇ cypy ◇", 
            font=("Fixedsys", 16), text_color=COLOR_PINK
        )
        lbl_logo.pack(side="left")
        
        lbl_desc = ctk.CTkLabel(
            title_container, text="Manga Translator", 
            font=("Terminal", 10), text_color="#888888"
        )
        lbl_desc.pack(side="left", padx=(8, 0))
        

        
        # Status Label (Top-Right, next to info button)
        self.lbl_status = ctk.CTkLabel(
            header_frame, text="Initializing...", 
            font=("Terminal", 10, "bold"), text_color="#e69933"
        )
        self.lbl_status.grid(row=0, column=1, padx=(0, 8), pady=6, sticky="e")

        # Info Button
        btn_info = ctk.CTkButton(
            header_frame, text="", image=self.ic_settings, width=22, height=22,
            fg_color="transparent", hover_color="#333333", border_width=0,
            corner_radius=0, command=self.show_info_popup
        )
        btn_info.grid(row=0, column=2, padx=(0, 12), pady=6, sticky="e")

    def create_main_panel(self):
        # ----------------------------------------------------
        # LEFT COLUMN: Inputs and Settings
        # ----------------------------------------------------
        left_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        left_container.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(8, 12))
        left_container.grid_columnconfigure(0, weight=1)
        left_container.grid_rowconfigure(0, weight=0) # Card 1
        left_container.grid_rowconfigure(1, weight=0) # Card 2
        left_container.grid_rowconfigure(2, weight=1) # Spacer
        left_container.grid_rowconfigure(3, weight=0) # Translate Button
        
        # CARD 1: SOURCE FILE OR FOLDER
        card1 = ctk.CTkFrame(left_container, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_BORDER, corner_radius=0)
        card1.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        card1.grid_columnconfigure(0, weight=1)
        card1.grid_columnconfigure(1, weight=0)
        card1.grid_columnconfigure(2, weight=0)
        
        lbl_card1 = ctk.CTkLabel(
            card1, text="SOURCE SELECTOR", 
            font=("Terminal", 10, "bold"), text_color=COLOR_WHITE
        )
        lbl_card1.grid(row=0, column=0, columnspan=3, padx=10, pady=(6, 3), sticky="w")
        
        self.path_entry = ctk.CTkEntry(
            card1, placeholder_text="Select file/folder to translate...", 
            font=("Consolas", 10), fg_color=COLOR_WIDGET, text_color=COLOR_WHITE,
            border_color=COLOR_BORDER, border_width=1, corner_radius=0, height=26
        )
        self.path_entry.configure(state="disabled")
        self.path_entry.grid(row=1, column=0, padx=(10, 6), pady=(0, 8), sticky="ew")
        
        btn_file = ctk.CTkButton(
            card1, text="FILE", width=55, height=26,
            font=("Terminal", 10, "bold"), text_color=COLOR_WHITE,
            fg_color=COLOR_DARK_BTN, hover_color=COLOR_DARK_BTN_HOVER, border_width=1, border_color=COLOR_BORDER,
            corner_radius=0, command=lambda: self.open_file_selector("file")
        )
        btn_file.grid(row=1, column=1, padx=3, pady=(0, 8), sticky="e")
        
        btn_folder = ctk.CTkButton(
            card1, text="FOLDER", width=55, height=26,
            font=("Terminal", 10, "bold"), text_color=COLOR_WHITE,
            fg_color=COLOR_DARK_BTN, hover_color=COLOR_DARK_BTN_HOVER, border_width=1, border_color=COLOR_BORDER,
            corner_radius=0, command=lambda: self.open_file_selector("folder")
        )
        btn_folder.grid(row=1, column=2, padx=(3, 10), pady=(0, 8), sticky="e")
        
        # Register Drag & Drop targets
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.handle_file_drop)
            
            # Also register the entry's inner native text widget
            self.path_entry._entry.drop_target_register(DND_FILES)
            self.path_entry._entry.dnd_bind('<<Drop>>', self.handle_file_drop)
        except Exception:
            pass
        
        # CARD 2: CONFIGURATION & LANGUAGE
        card2 = ctk.CTkFrame(left_container, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_BORDER, corner_radius=0)
        card2.grid(row=1, column=0, sticky="ew", pady=0)
        card2.grid_columnconfigure(0, weight=1)
        card2.grid_columnconfigure(1, weight=1)
        
        lbl_card2 = ctk.CTkLabel(
            card2, text="TRANSLATION SETTINGS", 
            font=("Terminal", 10, "bold"), text_color=COLOR_WHITE
        )
        lbl_card2.grid(row=0, column=0, columnspan=2, padx=10, pady=(6, 4), sticky="w")
        
        # Helper function to create clean stacked label/widget sub-grids
        def create_field(parent, label_text, row, col, widget_class, **kwargs):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.grid(row=row, column=col, padx=10, pady=3, sticky="ew")
            frame.grid_columnconfigure(0, weight=1)
            
            lbl = ctk.CTkLabel(frame, text=label_text, font=("Terminal", 9, "bold"), text_color=COLOR_GRAY, anchor="w")
            lbl.grid(row=0, column=0, sticky="w", pady=(0, 2))
            
            widget = widget_class(frame, **kwargs)
            widget.grid(row=1, column=0, sticky="ew")
            return widget
            
        # Row 1 of Settings Card
        self.lang_spinner = create_field(
            card2, "TARGET LANGUAGE", 1, 0, RetroOptionMenu,
            values=['English', 'Indonesian', 'Japanese', 'Mandarin', 'Spanish', 'Portuguese', 'Javanese', 'Korean', 'Russian', 'Thai'],
            font=("Consolas", 10), height=26, command=self.on_lang_changed
        )
        
        self.provider_spinner = create_field(
            card2, "AI PROVIDER", 1, 1, RetroOptionMenu,
            values=['Google Gemini', 'OpenAI', 'Zen (opencode.ai)', 'OpenCode Go', 'OpenRouter', 'Custom'],
            font=("Consolas", 10), height=26, command=self.on_provider_changed
        )
        
        # Row 2 of Settings Card
        self.api_key_entry = create_field(
            card2, "API KEY", 2, 0, ctk.CTkEntry,
            show="•", placeholder_text="Enter provider API key...",
            font=("Consolas", 10), fg_color=COLOR_WIDGET, text_color=COLOR_WHITE,
            border_color=COLOR_BORDER, border_width=1, corner_radius=0, height=26
        )
        self.api_key_entry.bind("<KeyRelease>", lambda e: self.on_api_key_changed(self.api_key_entry.get()))
        
        self.model_entry = create_field(
            card2, "MODEL NAME", 2, 1, ctk.CTkEntry,
            placeholder_text="e.g. gemini-3.1-flash-lite",
            font=("Consolas", 10), fg_color=COLOR_WIDGET, text_color=COLOR_WHITE,
            border_color=COLOR_BORDER, border_width=1, corner_radius=0, height=26
        )
        self.model_entry.bind("<KeyRelease>", lambda e: self.on_model_changed(self.model_entry.get()))
        
        # Row 3 of Settings Card
        self.sfx_spinner = create_field(
            card2, "SFX FILTER MODE", 3, 0, RetroOptionMenu,
            values=['seimbang', 'longgar', 'ketat'],
            font=("Consolas", 10), height=26, command=self.on_sfx_changed
        )
        
        self.base_url_entry = create_field(
            card2, "BASE URL (CUSTOM PROVIDER)", 3, 1, ctk.CTkEntry,
            placeholder_text="https://api.yourprovider.com/v1",
            font=("Consolas", 10), fg_color=COLOR_WIDGET, text_color=COLOR_WHITE,
            border_color=COLOR_BORDER, border_width=1, corner_radius=0, height=26
        )
        self.base_url_entry.bind("<KeyRelease>", lambda e: self.on_base_url_changed(self.base_url_entry.get()))
        
        # Add bottom spacing to settings card
        ctk.CTkLabel(card2, text="", height=4).grid(row=4, column=0, columnspan=2)
        
        # Action Frame (Translate Now + Open Folder)
        action_frame = ctk.CTkFrame(left_container, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=0)
        
        # TRANSLATE ACTION BUTTON
        self.translate_btn = ctk.CTkButton(
            action_frame, text="Translate Now", font=("Terminal", 13), text_color=COLOR_WHITE,
            fg_color=COLOR_PINK, hover_color="#be185d", corner_radius=0, height=32,
            command=self.start_translation
        )
        self.translate_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        
        # OPEN FOLDER BUTTON
        self.open_folder_btn = ctk.CTkButton(
            action_frame, text="" if self.ic_folder else "Folder", image=self.ic_folder,
            fg_color=COLOR_DARK_BTN, hover_color=COLOR_DARK_BTN_HOVER, border_width=1, border_color=COLOR_BORDER,
            corner_radius=0, height=32, width=32,
            command=self.open_output_folder
        )
        self.open_folder_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # ----------------------------------------------------
        # RIGHT COLUMN: Log Console (Full Height)
        # ----------------------------------------------------
        right_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        right_container.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(8, 12))
        right_container.grid_columnconfigure(0, weight=1)
        right_container.grid_rowconfigure(0, weight=1) # Let the card stretch fully
        
        # CARD 3: LOG CONSOLE
        card3 = ctk.CTkFrame(right_container, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_BORDER, corner_radius=0)
        card3.grid(row=0, column=0, sticky="nsew")
        card3.grid_columnconfigure(0, weight=1)
        card3.grid_rowconfigure(0, weight=0) # Label
        card3.grid_rowconfigure(1, weight=1) # Log textbox stretches fully
        
        lbl_log = ctk.CTkLabel(card3, text="LOG CONSOLE", font=("Terminal", 10, "bold"), text_color=COLOR_WHITE, anchor="w")
        lbl_log.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="w")
        
        self.log_textbox = ctk.CTkTextbox(
            card3, font=("Consolas", 10), fg_color=COLOR_WIDGET, text_color="#00ff00",
            border_color=COLOR_BORDER, border_width=1, corner_radius=0
        )
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_textbox.insert("end", "Welcome to CYPY! GUI initialized successfully.\n")
        self.log_textbox.configure(state="disabled")

    def process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", msg)
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self.process_log_queue)

    def load_settings_into_ui(self):
        # 1. Target Language
        lang = config.TARGET_LANGUAGE or "Indonesian"
        self.lang_spinner.set(lang)
        
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
        self.provider_spinner.set(provider_text_map.get(provider_name, "Google Gemini"))
        
        # 3. SFX Mode
        sfx_mode = config.FILTER_SFX_MODE
        self.sfx_spinner.set(sfx_mode)
        
        # 4. Load API and Model info based on provider
        self.update_provider_fields(provider_name)

    def update_provider_fields(self, provider_code):
        api_key, model_name = config.get_provider_config(provider_code)
        
        self.api_key_entry.configure(state="normal")
        self.api_key_entry.delete(0, "end")
        self.api_key_entry.insert(0, api_key)
        
        self.model_entry.configure(state="normal")
        self.model_entry.delete(0, "end")
        self.model_entry.insert(0, model_name)
        
        # Disable/Enable custom base URL
        if provider_code == 'custom':
            self.base_url_entry.configure(state="normal")
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.insert(0, config.CUSTOM_BASE_URL)
        else:
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.configure(state="disabled")

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
        config.save_settings()
        self.append_log(f"SFX Mode updated to: {value}\n")

    def load_yolo_model(self):
        try:
            base_model_path, _ = os.path.splitext(config.MODEL_YOLO)
            if not os.path.exists(config.MODEL_YOLO) and not os.path.exists(base_model_path + ".dat"):
                self.set_status('YOLO Missing!', "#ff3333")
                self.append_log("[!] YOLO model file not found in assets!\n")
                return
                
            self.yolo_model = YOLOONNX(config.MODEL_YOLO)
            self.set_status('Ready', "#00ff00") # Emerald green status
        except Exception as e:
            self.set_status('Error loading YOLO', "#ff3333")
            self.append_log(f"[!] Error loading YOLO model: {e}\n")
        finally:
            self.yolo_loading_done = True

    def open_file_selector(self, select_mode):
        if select_mode == 'folder':
            selected_path = filedialog.askdirectory(
                title="Select Source Folder",
                initialdir=os.path.expanduser('~')
            )
        else:
            exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.pdf", "*.zip", "*.cbz", "*.rar", "*.cbr")
            filetypes = [
                ("Manga Images/Archives/PDF", " ".join(exts)),
                ("All Files", "*.*")
            ]
            selected_path = filedialog.askopenfilename(
                title="Select Source File",
                initialdir=os.path.expanduser('~'),
                filetypes=filetypes
            )
            
        if selected_path:
            selected_path = selected_path.replace('\\', '/')
            
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, selected_path)
            self.path_entry.configure(state="readonly")
            
            self.append_log(f"Selected source: {selected_path}\n")

    def handle_file_drop(self, event):
        if not event.data:
            return
            
        try:
            paths = self.tk.splitlist(event.data)
            if not paths:
                return
            path = paths[0]
        except Exception:
            # Fallback manual parser
            path = event.data
            if path.startswith('{') and path.endswith('}'):
                path = path[1:-1]
            if ' {' in path or '} {' in path:
                import re
                matches = re.findall(r'\{([^}]+)\}|(\S+)', path)
                paths = [m[0] if m[0] else m[1] for m in matches]
                if paths:
                    path = paths[0]
                
        path = path.replace('\\', '/').strip()
        
        if os.path.exists(path):
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
            self.path_entry.configure(state="readonly")
            
            self.append_log(f"Dropped source: {path}\n")

    def open_output_folder(self):
        path = self.path_entry.get().strip()
        if not path:
            self.append_log("[!] Please select a source path first.\n")
            return
            
        if os.path.isfile(path):
            parent = os.path.dirname(path)
        else:
            parent = path
            
        lang = config.TARGET_LANGUAGE or "Indonesian"
        lang_code = config.LANG_CODES.get(lang.lower(), lang[:2].lower()).upper()
        
        target_dir = os.path.join(parent, lang_code)
        if os.path.exists(target_dir):
            dir_to_open = target_dir
        else:
            dir_to_open = parent
            
        if os.path.exists(dir_to_open):
            self.append_log(f"Opening folder: {dir_to_open}\n")
            try:
                os.startfile(os.path.abspath(dir_to_open))
            except Exception as e:
                webbrowser.open(dir_to_open)
        else:
            self.append_log(f"[!] Folder does not exist: {dir_to_open}\n")

    def show_info_popup(self):
        InfoDialog(self)

    def append_log(self, text):
        self.log_queue.put(text)

    def set_status(self, text, color):
        self.after(0, lambda: self._set_status_raw(text, color))
        
    def _set_status_raw(self, text, color):
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text=text, text_color=color)

    def start_translation(self):
        if self.translating:
            self.cancel_translation()
            return
            
        input_path = self.path_entry.get().strip()
        if not input_path:
            self.append_log("[!] Please select a file or folder first.\n")
            return
            
        if self.yolo_model is None:
            self.append_log("[!] Please wait for the YOLO model to finish loading.\n")
            return
            
        self.translating = True
        config.CANCEL_TRANSLATION = False
        self.translate_btn.configure(text="Cancel", fg_color="#dc2626", hover_color="#b91c1c")
        
        threading.Thread(target=self.run_translation_task, args=(input_path,), daemon=True).start()

    def cancel_translation(self):
        if not self.translating:
            return
        self.append_log("\n[!] Cancelling translation, please wait...\n")
        config.CANCEL_TRANSLATION = True
        self.translate_btn.configure(text="Cancelling...", fg_color="#555555", state="disabled")

    def run_translation_task(self, input_path):
        try:
            self.set_status('Translating...', "#e69933")
            
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
            if config.CANCEL_TRANSLATION:
                self.append_log(f"\n[Timer] Translation cancelled after {elapsed:.1f}s.\n")
            else:
                self.append_log(f"\n[Timer] Translation completed in {elapsed:.1f}s!\n")
            
        except Exception as e:
            self.append_log(f"[!] Error during translation: {e}\n")
            
        finally:
            self.translating = False
            self.after(0, self.reset_translate_button)

    def reset_translate_button(self):
        self.translate_btn.configure(text="Translate Now", fg_color=COLOR_PINK, hover_color="#be185d", state="normal")
        self.set_status('Ready', "#00ff00")

    def on_closing(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.destroy()

def main():
    ctk.set_appearance_mode("dark")
    app = CYPYWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
