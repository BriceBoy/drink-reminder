import os
import sys
from pathlib import Path

APP_ID = "BriceBoy.WaterReminder"
APP_NAME = "Water Reminder"


def data_directory() -> Path:
    return Path(os.environ["APPDATA"]) / "WaterReminder"


def resource_directory() -> Path:
    return Path(__file__).resolve().parent / "assets"


def launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        raise FileNotFoundError(f"Interpréteur sans console introuvable : {pythonw}")
    return [str(pythonw), str(Path(__file__).resolve().parent.parent / "run.pyw")]
