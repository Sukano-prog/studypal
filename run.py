import sys
import os

# PyInstaller sets sys._MEIPASS when bundled
if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(sys._MEIPASS, 'src'))
else:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import main

if __name__ == "__main__":
    main()
