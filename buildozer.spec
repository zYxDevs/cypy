[app]

# (str) Title of your application
title = CYPY

# (str) Package name
package.name = cypy

# (str) Package domain (needed for android packaging)
package.domain = org.indravoyager

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let's include py, kv, dat, png, json, onnx)
source.include_exts = py,png,kv,json,dat,onnx

# (str) Application versioning
version = 0.2508

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.3.1,numpy,pillow,opencv-python-headless,onnxruntime

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/favicon.png

# (str) Supported orientations (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (bool) Grant storage permissions on android>=6.0
android.grant_scopes = True

# (list) Android architectures to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (bool) Accept SDK license
android.accept_sdk_license = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
