import sys
import os
from app.gui.main_window import MainWindow

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    app = MainWindow()
    app.run() 