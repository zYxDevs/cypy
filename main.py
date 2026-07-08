import sys
import traceback
import os

# Ensure the app starts in GUI mode on Android
if '--gui' not in sys.argv:
    sys.argv.append('--gui')

def log_crash(tb_text):
    # Try writing to current directory
    try:
        with open("cypy_crash.txt", "w", encoding="utf-8") as f:
            f.write("CYPY Start Crash Log\n")
            f.write("====================\n")
            f.write(tb_text)
    except Exception:
        pass

    # On Android, try writing to public external app files directory which is easy to read
    try:
        # Check standard android paths
        package_name = "org.indravoyager.cypy"
        public_dir = f"/storage/emulated/0/Android/data/{package_name}/files"
        if os.path.exists(public_dir):
            target_path = os.path.join(public_dir, "cypy_crash.txt")
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("CYPY Start Crash Log\n")
                f.write("====================\n")
                f.write(tb_text)
    except Exception:
        pass

try:
    from cypy.app import main
    if __name__ == '__main__':
        main()
except Exception as e:
    log_crash(traceback.format_exc())
    raise

