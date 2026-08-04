"""App Lab entry point for the PitWall LED signaller.

Exists only because arduino.app_utils is importable solely inside an Arduino
App's managed container, which arduino-app-cli starts from this folder. All
state logic lives in src/bridge_client.py and is not duplicated here.

The App folder is bind-mounted at /app, so src/ and config/ are deployed
alongside this file and PROJECT_ROOT resolves to /app/python.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_PYTHON_DIR = Path(__file__).resolve().parent
if str(APP_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(APP_PYTHON_DIR))

from arduino.app_utils import App

from src.bridge_client import build_applab_loop

if __name__ == "__main__":
    App.run(user_loop=build_applab_loop())
