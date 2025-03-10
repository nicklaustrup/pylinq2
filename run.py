#!/usr/bin/env python3
"""
Video Chat Application Launcher

This script launches the video chat application.
"""

import sys
import os
import logging
from app.gui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point for the application"""
    try:
        # Create and run the main window
        app = MainWindow()
        app.run()
    except Exception as e:
        logging.error(f"Error running application: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main()) 