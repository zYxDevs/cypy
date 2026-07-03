import os
import sys
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
    "nuitka",
    "ordered-set"
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
                if package in deps:
                    print(f"[Build] Dependency installed: {package}")
                    available_deps.add(package)

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
    try:
        from nuitka.Version import getNuitkaVersion
        print(f"[Build] Nuitka version: {getNuitkaVersion()}")
    except ImportError:
        print("[Build] Nuitka not found. Installing via pip...", file=sys.stderr)
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

    # Clean up old build outputs to avoid Windows locked file issues
    if DIST_DIR.exists():
        print(f"[Build] Cleaning up old build directory: {DIST_DIR}")
        try:
            shutil.rmtree(DIST_DIR)
        except Exception as e:
            print(f"[Build] Warning: Failed to fully delete {DIST_DIR}, error: {e}. Trying to ignore errors...")
            shutil.rmtree(DIST_DIR, ignore_errors=True)

    # Build command using Nuitka (cypy is CLI so console mode is enable)
    cmd: List[str] = [
        EXEC_PATH, "-m", "nuitka",
        "--standalone",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={APP_NAME}",
        f"--include-data-dir={ASSETS_DIR}=assets",
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=tensorboard",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=IPython",
        "--nofollow-import-to=torch",
        "--nofollow-import-to=ultralytics",
        "--assume-yes-for-downloads",
        "--show-progress",
    ]

    curr_system = platform.system().lower()
    is_favicon_exist = ICON_PATH.is_file()
    if not is_favicon_exist:
        print(
            "[Build] Warning: favicon.ico not found, compiling without custom icon.",
            file=sys.stderr
        )

    if curr_system == "windows":
        cmd.extend([
            f"--windows-icon-from-ico={ICON_PATH}" if is_favicon_exist else ''
        ])
    elif curr_system == "darwin":
        cmd.extend([
            f"--macos-app-icon={ICON_PATH}" if is_favicon_exist else ''
        ])

    cmd = [c for c in cmd if c.strip() != '']
    cmd.append(str(APP_ENTRY_POINT))

    print(f"[Build] Running Nuitka compilation command:\n{' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("[Build] Nuitka compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[Build] Nuitka compilation failed with exit code: {e.returncode}")
        sys.exit(1)

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

    nuitka_output = None
    dist_dir_items = list(DIST_DIR.iterdir())
    
    std_dist = DIST_DIR / "app.dist"
    if std_dist.is_dir() and any(std_dist.iterdir()):
        nuitka_output = std_dist
    else:
        for item in dist_dir_items:
            if (item.name.endswith(".dist") or item.name.endswith(".app")) and item.is_dir():
                if not any(item.iterdir()): continue
                nuitka_output = item
                break

    if not nuitka_output or not nuitka_output.is_dir():
        print(
            f"[Build] Error: Nuitka valid output directory not found.\n" +
            f"[Build] Contents of 'dist/': {dist_dir_items if dist_dir_items else 'NOT FOUND'}",
            file=sys.stderr
        )
        sys.exit(2)

    print(f"[Build] Found Nuitka output at: {nuitka_output}")

    app_folder_path = DIST_DIR / f"{APP_NAME}_pkg_temp"
    if app_folder_path.is_dir():
        try: shutil.rmtree(app_folder_path)
        except Exception as e:
            print(f"[Build] Warning: Failed to remove old temporary directory: {e}", file=sys.stderr)
    app_folder_path.mkdir(exist_ok=True)

    # Copy files
    for item in os.listdir(nuitka_output):
        s = nuitka_output / item
        d = app_folder_path / item
        if s.is_dir():
            shutil.copytree(s, d, symlinks=True)
        else:
            shutil.copy2(s, d, follow_symlinks=False)
    print("[Build] Copied all compiled files and folders into release folder.")

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
        print(f"[Build] Zipping folder: {app_folder_path} to {zip_path}...")
        created_zip = safe_zip_directory(app_folder_path, zip_path)
        created_zip_path = Path(created_zip)
        if not created_zip_path.is_file():
            raise FileNotFoundError(f"[Build] Expected archive not found: {created_zip}")

        if RELEASES_DIR not in created_zip_path.parents:
            created_zip_path = Path(shutil.move(created_zip_path, RELEASES_DIR / created_zip_path.name))

        print(f"[Build] Packaged successfully to: {created_zip_path}")
        print(f"[Build] Package size: {created_zip_path.stat().st_size / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"[Build] Packaging failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cleanup()

def safe_zip_directory(folder_path: Union[str, Path], zip_path: Union[str, Path]) -> str:
    folder_path = Path(folder_path).resolve()
    zip_path = Path(zip_path).resolve()

    if not folder_path.is_dir():
        raise NotADirectoryError(folder_path)

    archive_root = folder_path.parent / APP_NAME
    folder_path.rename(archive_root)
    print(f"[Build] Renamed '{folder_path}' -> '{archive_root}'")

    try:
        archive = shutil.make_archive(
            str(zip_path.with_suffix("")),
            "zip",
            archive_root.parent,
            archive_root.name,
        )
        print(f"[Build] Created ZIP archive: {archive}")
        return archive
    finally:
        archive_root.rename(folder_path)
        print(f"[Build] Renamed '{archive_root}' -> '{folder_path}'")

if __name__ == "__main__":
    run_build()
