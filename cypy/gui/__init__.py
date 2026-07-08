import os
import sys

# Prevent Kivy from parsing command line arguments meant for CyPy (like --gui)
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.core.text import LabelBase

# Register Consolas font (with safety check/fallback)
font_dir = "C:\\Windows\\Fonts"
if os.path.exists(font_dir) and os.path.exists(os.path.join(font_dir, 'consola.ttf')):
    LabelBase.register(
        name='Consolas',
        fn_regular=os.path.join(font_dir, 'consola.ttf'),
        fn_bold=os.path.join(font_dir, 'consolab.ttf'),
        fn_italic=os.path.join(font_dir, 'consolai.ttf'),
        fn_bolditalic=os.path.join(font_dir, 'consolaz.ttf')
    )
else:
    # Try Courier New as a cross-platform fallback
    courier_regular = os.path.join(font_dir, 'cour.ttf')
    if os.path.exists(courier_regular):
        LabelBase.register(
            name='Consolas',
            fn_regular=courier_regular,
            fn_bold=os.path.join(font_dir, 'courbd.ttf'),
            fn_italic=os.path.join(font_dir, 'couri.ttf'),
            fn_bolditalic=os.path.join(font_dir, 'courbi.ttf')
        )

# Tentukan path dinamis untuk runtime reguler maupun terkompilasi
if getattr(sys, 'frozen', False):
    GUI_DIR = os.path.join(getattr(sys, '_MEIPASS', ''), "cypy", "gui")
else:
    GUI_DIR = os.path.dirname(os.path.abspath(__file__))

kv_path = os.path.join(GUI_DIR, "design.kv")

from cypy.gui.controller import CYPYApp

def main():
    app = CYPYApp()
    app.kv_file = kv_path
    app.run()
