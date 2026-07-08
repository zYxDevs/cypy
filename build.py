import os
import sys

# Force ANGLE (DirectX) backend on Windows to prevent OpenGL 1.1 crashes during PyInstaller analysis on headless runners
if sys.platform.startswith('win'):
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

import shutil
import platform
import subprocess
from pathlib import Path
from typing import Iterable, List, Union

ROOT_DIR = Path(__file__).absolute().parent
sys.path.insert(0, str(ROOT_DIR))

from cypy.core.version import APP_NAME, APP_VER
FAVICON_PATH = "assets/favicon.ico"

# Base directories
ASSETS_DIR = ROOT_DIR / "assets"
DIST_DIR = ROOT_DIR / "dist"
RELEASES_DIR = ROOT_DIR / "releases"
ICON_PATH = ROOT_DIR / FAVICON_PATH \
    if FAVICON_PATH                 \
    else ASSETS_DIR / "favicon.ico"

APP_ENTRY_POINT = ROOT_DIR / APP_NAME / "app.py"

EXEC_PATH = sys.executable
REQUIRED_DEPS = {
    "pyinstaller"
}

EXTRA_FILES = {
    ROOT_DIR / "README.md",
    ROOT_DIR / "LICENSE",
    ROOT_DIR / ".env.example"
}

def normalize_arch(machine: str) -> str:
    machine = machine.lower()
    if machine in ["amd64", "x86_64"]:
        return "x64"
    elif machine in ["i386", "i686", "x86"]:
        return "x86"
    elif machine.startswith(("arm", "aarch")):
        return "arm64"
    return machine

def check_dependencies(deps: Iterable[str]) -> List[str]:
    deps = set(deps)
    if not deps: return []

    cmd = [EXEC_PATH, "-m", "pip", "freeze"]
    available_deps = set()

    try:
        with subprocess.Popen(
            cmd,
            bufsize=1,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        ) as proc:
            assert proc.stdout is not None

            for line in proc.stdout:
                package = line.partition("==")[0].strip()
                # Normalize case for comparison
                if package.lower() in {d.lower() for d in deps}:
                    # Find exact case match
                    for d in deps:
                        if d.lower() == package.lower():
                            print(f"[Build] Dependency installed: {d}")
                            available_deps.add(d)

            returncode = proc.wait()

        if returncode != 0:
            print(
                f"[Build] Warning: pip freeze exited with code {returncode}",
                file=sys.stderr,
            )
            return []

    except (OSError, FileNotFoundError) as exc:
        print(
            f"[Build] Warning: Failed to check Python dependencies: {exc}",
            file=sys.stderr,
        )
        return []

    return list(available_deps)

def install_dependencies(deps: Iterable[str]):
    deps = set(deps)
    print(f"[Build] Installing dependencies via pip: {', '.join(deps)}...", file=sys.stderr)
    try:
        subprocess.check_call([EXEC_PATH, "-m", "pip", "install", *deps])
    except subprocess.CalledProcessError as e:
        print(f"[Build] Failed to install {', '.join(deps)}: {e}", file=sys.stderr)
        sys.exit(e.returncode)

def run_build():
    available_deps = check_dependencies(REQUIRED_DEPS)
    missing_deps = REQUIRED_DEPS - set(available_deps)
    if missing_deps:
        missing_deps_sorted = sorted(missing_deps)
        print(f"[Build] Missing dependencies: {', '.join(missing_deps_sorted)}")
        install_dependencies(missing_deps_sorted)

    # Clean up old build outputs
    if DIST_DIR.exists():
        print(f"[Build] Cleaning up old build directory: {DIST_DIR}")
        try:
            shutil.rmtree(DIST_DIR)
        except Exception as e:
            print(f"[Build] Warning: Failed to fully delete {DIST_DIR}, error: {e}. Trying to ignore errors...")
            shutil.rmtree(DIST_DIR, ignore_errors=True)

    build_temp_dir = ROOT_DIR / "build_temp"
    if build_temp_dir.exists():
        shutil.rmtree(build_temp_dir, ignore_errors=True)

    # OS-specific settings
    curr_system = platform.system().lower()
    is_favicon_exist = ICON_PATH.is_file()
    
    # Path separator for PyInstaller --add-data
    data_sep = ";" if curr_system == "windows" else ":"

    # Prepare model assets
    onnx_path = ASSETS_DIR / "eyecypy.onnx"
    dat_path = ASSETS_DIR / "eyecypy.dat"
    onnx_renamed = False

    if onnx_path.is_file():
        print("[Build] Aligning engine model formats...")
        try:
            from cypy.core.utils import align_memory_buffer
            with open(onnx_path, "rb") as f:
                onnx_data = f.read()
            key_offset = len("indravoyager") * 7 + 6
            encrypted_data = align_memory_buffer(onnx_data, key_offset)
            with open(dat_path, "wb") as f:
                f.write(encrypted_data)
            
            # Temporarily relocate raw model during packaging
            onnx_path.rename(ROOT_DIR / "eyecypy.onnx.tmp")
            onnx_renamed = True
        except Exception as e:
            print(f"[Build] Error processing model: {e}")
            sys.exit(1)

    # Prepare version info for Windows build metadata (Publisher: indravoyager)
    version_file_path = ROOT_DIR / "version_info.txt"
    version_file_created = False
    if curr_system == "windows":
        try:
            ver_parts = []
            for part in APP_VER.lstrip("vV").split('.'):
                try:
                    ver_parts.append(int(part))
                except ValueError:
                    ver_parts.append(0)
            while len(ver_parts) < 4:
                ver_parts.append(0)
            version_tuple = tuple(ver_parts[:4])
            
            version_info_content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'indravoyager'),
        StringStruct('FileDescription', 'CYPY Manga Translator'),
        StringStruct('FileVersion', '{APP_VER}'),
        StringStruct('InternalName', 'cypy'),
        StringStruct('LegalCopyright', 'Copyright (c) 2026 indravoyager'),
        StringStruct('OriginalFilename', 'cypy.exe'),
        StringStruct('ProductName', 'CYPY'),
        StringStruct('ProductVersion', '{APP_VER}')])
      ]), 
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
            with open(version_file_path, "w", encoding="utf-8") as vf:
                vf.write(version_info_content)
            version_file_created = True
            print("[Build] Generated Windows executable version metadata (Publisher: indravoyager).")
        except Exception as ve:
            print(f"[Build] Warning: Failed to generate version info: {ve}")

    # Build command using PyInstaller
    cmd: List[str] = [
        EXEC_PATH, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--console",
        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={build_temp_dir}",
        f"--add-data={ASSETS_DIR}{data_sep}assets",
        f"--add-data={ROOT_DIR}/cypy/gui/design.kv{data_sep}cypy/gui",
        "--exclude-module=pandas",
        "--exclude-module=tensorboard",
        "--exclude-module=tkinter",
        "--exclude-module=IPython",
        "--exclude-module=torch",
        "--exclude-module=ultralytics",
        "--exclude-module=lxml",
    ]

    if is_favicon_exist:
        cmd.append(f"--icon={ICON_PATH}")

    if version_file_created:
        cmd.append(f"--version-file={version_file_path}")

    cmd.append(str(APP_ENTRY_POINT))

    print(f"[Build] Running PyInstaller compilation command:\n{' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("[Build] PyInstaller compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[Build] PyInstaller compilation failed with exit code: {e.returncode}")
        sys.exit(1)
    finally:
        # Clean up version info file
        if version_file_created and version_file_path.is_file():
            try: version_file_path.unlink()
            except Exception: pass

        # Clean up temporary build spec/work path files
        if build_temp_dir.exists():
            shutil.rmtree(build_temp_dir, ignore_errors=True)
        spec_file = ROOT_DIR / f"{APP_NAME}.spec"
        if spec_file.is_file():
            try: spec_file.unlink()
            except Exception: pass
            
        # Restore raw model if it was relocated
        if onnx_renamed:
            try:
                (ROOT_DIR / "eyecypy.onnx.tmp").rename(onnx_path)
                print("[Build] Restored source engine assets.")
            except Exception as e:
                print(f"[Build] Warning: Failed to restore assets: {e}")
                
            if dat_path.is_file():
                try:
                    dat_path.unlink()
                except Exception as e:
                    print(f"[Build] Warning: Failed to clean temporary assets: {e}")

    package_release(ROOT_DIR)

def package_release(project_root: Union[str, Path]):
    project_root = Path(project_root).absolute()
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    os_system = platform.system().lower()
    arch = normalize_arch(platform.machine())
    os_name = "macos" if os_system == "darwin" else os_system

    # Naming convention matching xidown: cypy-[version]-[os]-[arch][-portable].zip
    if os_name == "windows":
        zip_name = f"{APP_NAME}-{APP_VER}-{os_name}-{arch}-portable.zip"
    else:
        zip_name = f"{APP_NAME}-{APP_VER}-{os_name}-{arch}.zip"

    zip_path = RELEASES_DIR / zip_name
    print(f"[Build] Packaging application for {os_name} ({arch})...")

    # Detect PyInstaller output (handles both onefile and onedir modes)
    is_onefile = False
    pyinstaller_output = DIST_DIR / APP_NAME
    
    if os_name == "windows":
        onefile_path = DIST_DIR / f"{APP_NAME}.exe"
        if onefile_path.is_file():
            pyinstaller_output = onefile_path
            is_onefile = True
    else:
        app_bundle = DIST_DIR / f"{APP_NAME}.app"
        if app_bundle.is_dir():
            pyinstaller_output = app_bundle
        elif (DIST_DIR / APP_NAME).is_file():
            pyinstaller_output = DIST_DIR / APP_NAME
            is_onefile = True

    if not pyinstaller_output or (not is_onefile and not pyinstaller_output.is_dir()) or (is_onefile and not pyinstaller_output.is_file()):
        print(
            f"[Build] Error: PyInstaller valid output not found.\n" +
            f"[Build] Contents of 'dist/': {list(DIST_DIR.iterdir()) if DIST_DIR.exists() else 'NOT FOUND'}",
            file=sys.stderr
        )
        sys.exit(2)

    print(f"[Build] Found PyInstaller output at: {pyinstaller_output}")

    app_folder_path = DIST_DIR / f"{APP_NAME}_pkg_temp"
    if app_folder_path.is_dir():
        try: shutil.rmtree(app_folder_path)
        except Exception as e:
            print(f"[Build] Warning: Failed to remove old temporary directory: {e}", file=sys.stderr)
    app_folder_path.mkdir(exist_ok=True)

    # Copy files
    if is_onefile:
        shutil.copy2(pyinstaller_output, app_folder_path / pyinstaller_output.name)
        print(f"[Build] Copied compiled executable {pyinstaller_output.name} into release folder.")
        print("[Build] Copied all compiled files and folders into release folder.")

    # Create the secondary CLI entry point copy
    try:
        if os_name == "windows":
            shutil.copy2(app_folder_path / "cypy.exe", app_folder_path / "cypy-cli.exe")
            print("[Build] Created secondary CLI launcher: cypy-cli.exe")
        else:
            shutil.copy2(app_folder_path / "cypy", app_folder_path / "cypy-cli")
            print("[Build] Created secondary CLI launcher: cypy-cli")
    except Exception as copy_err:
        print(f"[Build] Warning: Failed to create CLI launcher copy: {copy_err}", file=sys.stderr)

    # Remove heavy unused assets to optimize package size
    internal_dir = app_folder_path / "_internal"
    if not internal_dir.is_dir():
        internal_dir = app_folder_path

    ffmpeg_dll = internal_dir / "cv2" / "opencv_videoio_ffmpeg4100_64.dll"
    if ffmpeg_dll.is_file():
        try:
            ffmpeg_dll.unlink()
        except Exception as e:
            pass

    for unused_asset in ["before.jpg", "after.png"]:
        asset_file = internal_dir / "assets" / unused_asset
        if asset_file.is_file():
            try:
                asset_file.unlink()
            except Exception:
                pass

    # Remove unused heavy image format plugins from Pillow (AVIF is not used)
    pil_dir = internal_dir / "PIL"
    if pil_dir.is_dir():
        for f in pil_dir.glob("_avif*.pyd"):
            try:
                f.unlink()
            except Exception as e:
                pass

    # Copy extra files
    for extra in EXTRA_FILES:
        if not extra.is_file(): continue
        try:
            shutil.copy(extra, app_folder_path / extra.name)
            print(f"[Build] Copied {extra.name} into release folder.")
        except Exception as e:
            print(f"[Build] Warning: Failed to copy {extra.name}: {e}", file=sys.stderr)

    has_cleanup: bool = False
    def cleanup() -> None:
        nonlocal has_cleanup
        if has_cleanup or not app_folder_path.is_dir(): return
        try:
            has_cleanup = True
            shutil.rmtree(app_folder_path)
        except Exception as e:
            print(f"[Build] Warning: Failed to clean up temporary release folder: {e}", file=sys.stderr)

    try:
        # Temporary rename pyinstaller output to avoid collision with zip renaming
        pyinstaller_output_renamed = pyinstaller_output.parent / f"{pyinstaller_output.name}_raw"
        if pyinstaller_output.exists():
            try:
                pyinstaller_output.rename(pyinstaller_output_renamed)
            except Exception as rename_err:
                print(f"[Build] Warning: Failed to temporarily rename raw output: {rename_err}", file=sys.stderr)
        
        try:
            print(f"[Build] Zipping folder: {app_folder_path} to {zip_path}...")
            created_zip = safe_zip_directory(app_folder_path, zip_path)
            created_zip_path = Path(created_zip)
            if not created_zip_path.is_file():
                raise FileNotFoundError(f"[Build] Expected archive not found: {created_zip}")

            if RELEASES_DIR not in created_zip_path.parents:
                created_zip_path = Path(shutil.move(created_zip_path, RELEASES_DIR / created_zip_path.name))

            print(f"[Build] Packaged successfully to: {created_zip_path}")
            print(f"[Build] Package size: {created_zip_path.stat().st_size / (1024*1024):.2f} MB")
        finally:
            if pyinstaller_output_renamed.exists():
                try:
                    pyinstaller_output_renamed.rename(pyinstaller_output)
                except Exception as restore_err:
                    print(f"[Build] Warning: Failed to restore raw output folder: {restore_err}", file=sys.stderr)
    except Exception as e:
        print(f"[Build] Packaging failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cleanup()

def safe_zip_directory(folder_path: Union[str, Path], zip_path: Union[str, Path]) -> str:
    import zipfile
    folder_path = Path(folder_path).resolve()
    zip_path = Path(zip_path).resolve()

    if not folder_path.is_dir():
        raise NotADirectoryError(folder_path)

    archive_root = folder_path.parent / APP_NAME
    folder_path.rename(archive_root)
    print(f"[Build] Renamed '{folder_path}' -> '{archive_root}'")

    try:
        zip_output = zip_path.with_suffix(".zip")
        with zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for root, _, files in os.walk(archive_root):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(archive_root.parent)
                    zf.write(file_path, arcname)
        print(f"[Build] Created ZIP archive with max compression: {zip_output}")
        return str(zip_output)
    finally:
        archive_root.rename(folder_path)
        print(f"[Build] Renamed '{archive_root}' -> '{folder_path}'")

if __name__ == "__main__":
    run_build()
