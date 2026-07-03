import os
import sys
import shutil
import platform
import zipfile
import subprocess

def install_dependencies():
    # Ensure pyinstaller is installed
    try:
        import PyInstaller
        print(f"[Build] PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[Build] PyInstaller not found. Installing via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        except Exception as e:
            print(f"[Build] Failed to install PyInstaller: {e}")
            sys.exit(1)

def run_build():
    # Install dependencies first
    install_dependencies()

    # Path separator: ';' on Windows, ':' on Unix-like (Linux/macOS)
    sep = ";" if platform.system() == "Windows" else ":"
    
    # Base directories
    project_root = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(project_root, "assets")
    
    # Build command for console application (no --windowed/--noconsole because cypy is a CLI app)
    # Using --onedir as requested for lightweight, SSD-friendly, instant startup.
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--name=cypy",
        "--onedir",
        f"--add-data={assets_dir}{sep}assets",
        "--exclude-module=polars",
        "--exclude-module=lxml",
        "--exclude-module=tkinter",
        "--exclude-module=sqlite3",
        "--exclude-module=IPython",
        "--exclude-module=notebook",
        "--exclude-module=pandas",
        "--exclude-module=tensorboard",
        "--exclude-module=torch.testing",
        "--exclude-module=torch.distributed",
        "--exclude-module=triton",
        "--exclude-module=sympy",
        "--exclude-module=mpmath",
        "--exclude-module=jinja2",
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
    ]
    
    # Add icon if available
    icon_path = os.path.join(assets_dir, "favicon.ico")
    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")
    else:
        print("[Build] Warning: favicon.ico not found, compiling without custom icon.")
    
    # Entry point
    entry_point = os.path.join(project_root, "cypy", "app.py")
    cmd.append(entry_point)
    
    print(f"[Build] Running compilation command:\n{' '.join(cmd)}")
    
    # Run PyInstaller
    try:
        subprocess.check_call(cmd)
        print("[Build] PyInstaller compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[Build] PyInstaller compilation failed with exit code: {e.returncode}")
        sys.exit(1)

    # Package the output into a zip file in a 'releases' folder
    package_release(project_root)

def package_release(project_root):
    dist_dir = os.path.join(project_root, "dist")
    releases_dir = os.path.join(project_root, "releases")
    os.makedirs(releases_dir, exist_ok=True)
    
    # Identify OS and Architecture
    os_system = platform.system().lower()
    if os_system == "darwin":
        os_name = "macos"
    else:
        os_name = os_system
        
    raw_arch = platform.machine().lower()
    if raw_arch in ["amd64", "x86_64"]:
        arch = "x64"
    elif raw_arch in ["i386", "i686", "x86"]:
        arch = "x86"
    elif "arm" in raw_arch or "aarch" in raw_arch:
        arch = "arm64"
    else:
        arch = raw_arch
        
    zip_name = f"cypy-{os_name}-{arch}.zip"
    zip_path = os.path.join(releases_dir, zip_name)
    
    print(f"[Build] Packaging application for {os_name} ({arch})...")
    
    # In --onedir mode, we create a temporary directory named 'cypy_pkg_temp' inside 'dist' to bundle everything.
    # This avoids any naming conflicts with the compiled output directory.
    app_folder_path = os.path.join(dist_dir, "cypy_pkg_temp")
    if os.path.exists(app_folder_path):
        try:
            shutil.rmtree(app_folder_path)
        except Exception:
            pass
    os.makedirs(app_folder_path, exist_ok=True)
    
    # 1. Copy the compiled output into our temporary release folder
    if os_name == "macos":
        app_bundle = os.path.join(dist_dir, "cypy.app")
        if os.path.exists(app_bundle):
            shutil.copytree(app_bundle, os.path.join(app_folder_path, "cypy.app"))
            print("[Build] Copied cypy.app bundle into release folder.")
        else:
            # Fallback to binary directory if no bundle exists
            src_dir = os.path.join(dist_dir, "cypy")
            if os.path.exists(src_dir):
                shutil.copytree(src_dir, os.path.join(app_folder_path, "cypy"))
                print("[Build] Copied cypy binary directory into release folder.")
            else:
                print("[Build] Error: Compiled output not found.")
                sys.exit(1)
    else:
        # For Windows/Linux, copy all contents from dist/cypy/ into dist/cypy_pkg_temp/
        src_dir = os.path.join(dist_dir, "cypy")
        if os.path.exists(src_dir):
            for item in os.listdir(src_dir):
                s = os.path.join(src_dir, item)
                d = os.path.join(app_folder_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            print("[Build] Copied all compiled files and folders into release folder.")
        else:
            print(f"[Build] Error: Compiled directory not found at: {src_dir}")
            sys.exit(1)
            
    # 2. Copy README.md into the release folder before zipping
    readme_path = os.path.join(project_root, "README.md")
    if os.path.exists(readme_path):
        try:
            shutil.copy(readme_path, os.path.join(app_folder_path, "README.md"))
            print("[Build] Copied README.md into release folder.")
        except Exception as e:
            print(f"[Build] Warning: Failed to copy README.md: {e}")
            
    # 3. Copy LICENSE into the release folder before zipping
    license_path = os.path.join(project_root, "LICENSE")
    if os.path.exists(license_path):
        try:
            shutil.copy(license_path, os.path.join(app_folder_path, "LICENSE"))
            print("[Build] Copied LICENSE into release folder.")
        except Exception as e:
            print(f"[Build] Warning: Failed to copy LICENSE: {e}")
            
    # 4. Copy .env.example into the release folder before zipping
    env_ex_path = os.path.join(project_root, ".env.example")
    if os.path.exists(env_ex_path):
        try:
            shutil.copy(env_ex_path, os.path.join(app_folder_path, ".env.example"))
            print("[Build] Copied .env.example into release folder.")
        except Exception as e:
            print(f"[Build] Warning: Failed to copy .env.example: {e}")
            
    # 5. Zip the entire folder
    try:
        print(f"[Build] Zipping folder: {app_folder_path} to {zip_path}...")
        zip_directory(app_folder_path, zip_path)
        print(f"[Build] Packaged successfully to: {zip_path}")
        print(f"[Build] Package size: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"[Build] Packaging failed: {e}")
        sys.exit(1)
    finally:
        # 6. Clean up our temporary release folder
        if os.path.exists(app_folder_path):
            try:
                shutil.rmtree(app_folder_path)
            except Exception as e:
                print(f"[Build] Warning: Failed to clean up temporary release folder: {e}")

def zip_directory(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Maintain relative path inside zip, prefixing with 'cypy/'
                rel_path = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, os.path.join("cypy", rel_path))

if __name__ == "__main__":
    run_build()
