import ctypes
import subprocess
import winreg
from ctypes import wintypes
from pathlib import Path

from .paths import APP_ID, APP_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUMID_KEY = rf"Software\Classes\AppUserModelId\{APP_ID}"
RUN_VALUE = "WaterReminder"
MUTEX_NAME = r"Local\BriceBoy.WaterReminder"

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL


class SingleInstance:
    def __init__(self, name: str = MUTEX_NAME) -> None:
        self.name = name
        self.handle: int | None = None

    def acquire(self) -> bool:
        if self.handle is not None:
            raise RuntimeError("Le verrou est déjà acquis par cet objet.")
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, False, self.name)
        error = ctypes.get_last_error()
        if not handle:
            raise ctypes.WinError(error)
        if error == 183:  # ERROR_ALREADY_EXISTS
            if not kernel32.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())
            return False
        self.handle = handle
        return True

    def close(self) -> None:
        if self.handle is not None:
            if not kernel32.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = None


def register_application(icon: Path, app_id: str = APP_ID) -> None:
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{app_id}"
    ) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, str(icon.resolve()))


def set_autostart(enabled: bool, command: list[str]) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, subprocess.list2cmdline(command))
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass  # An absent Run value is already the requested state.


def native_error(message: str) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.MessageBoxW.argtypes = (wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT)
    user32.MessageBoxW.restype = ctypes.c_int
    user32.MessageBoxW(None, message, APP_NAME, 0x10)
