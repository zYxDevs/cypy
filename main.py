import sys

# Ensure the app starts in GUI mode on Android
if '--gui' not in sys.argv:
    sys.argv.append('--gui')

from cypy.app import main

if __name__ == '__main__':
    main()
