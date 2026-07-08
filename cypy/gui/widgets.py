import os
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.button import Button

class FileChooserPopup(Popup):
    def __init__(self, select_mode='file', callback=None, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Select Source File' if select_mode == 'file' else 'Select Source Folder'
        self.size_hint = (0.9, 0.9)
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Build path (default to home folder)
        start_path = os.path.expanduser('~')
        
        self.filechooser = FileChooserIconView(path=start_path, size_hint_y=1)
        if select_mode == 'folder':
            self.filechooser.dirselect = True
        else:
            self.filechooser.dirselect = False

        # Filter out locked Windows system files to prevent sharing violations
        def win_system_filter(directory, filename):
            system_names = {
                'hiberfil.sys', 'pagefile.sys', 'swapfile.sys', 
                'dumpstack.log', 'dumpstack.log.tmp', 'desktop.ini', 
                'ntuser.dat', 'ntuser.dat.log'
            }
            fn_lower = filename.lower()
            if fn_lower in system_names or fn_lower.startswith('$'):
                return False
            
            # If selecting files, only show folders and valid manga formats
            if select_mode == 'file':
                try:
                    if os.path.isdir(os.path.join(directory, filename)):
                        return True
                except Exception:
                    pass
                valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.pdf', '.zip', '.cbz', '.rar', '.cbr')
                return fn_lower.endswith(valid_exts)
                
            return True

        self.filechooser.filters = [win_system_filter]
            
        layout.add_widget(self.filechooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height='36dp', spacing=10)
        
        btn_cancel = Button(
            text='Cancel', 
            background_normal='', 
            background_color=(0.1, 0.1, 0.1, 1),
            font_name='Consolas',
            font_size='11sp',
            bold=True
        )
        btn_cancel.bind(on_release=self.dismiss)
        
        btn_select = Button(
            text='Select', 
            background_normal='', 
            background_color=(0.86, 0.15, 0.47, 1),
            font_name='Consolas',
            font_size='11sp',
            bold=True
        )
        
        def on_select(instance):
            if self.filechooser.selection:
                selected = self.filechooser.selection[0]
            else:
                selected = self.filechooser.path
            if callback:
                callback(selected)
            self.dismiss()
            
        btn_select.bind(on_release=on_select)
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_select)
        
        layout.add_widget(btn_layout)
        self.content = layout

class InfoPopup(Popup):
    pass

class StdoutRedirector:
    def __init__(self, callback):
        self.callback = callback
        
    def write(self, string):
        if string.strip():
            self.callback(string)
            
    def flush(self):
        pass
