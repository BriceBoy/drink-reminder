import ctypes
import os
import subprocess
import sys
import tempfile
import time
import unittest
from ctypes import wintypes
from pathlib import Path


@unittest.skipUnless(
    sys.platform == "win32" and os.environ.get("WATER_REMINDER_EXE"),
    "Définir WATER_REMINDER_EXE pour tester le binaire compilé",
)
class FrozenTests(unittest.TestCase):
    def test_executable_opens_first_run_and_closes_cleanly(self) -> None:
        import winreg

        from water_reminder.windows import AUMID_KEY, SingleInstance

        probe = SingleInstance()
        if not probe.acquire():
            self.skipTest("Quittez Water Reminder avant de tester l'exécutable.")
        probe.close()
        previous: dict[str, tuple[str, int]] = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUMID_KEY) as key:
                for name in ("DisplayName", "IconUri"):
                    try:
                        previous[name] = winreg.QueryValueEx(key, name)
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            pass

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows.argtypes = (callback_type, wintypes.LPARAM)
        user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        )
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        executable = Path(os.environ["WATER_REMINDER_EXE"]).resolve()
        self.assertTrue(executable.is_file())
        windows: list[int] = []

        @callback_type
        def find_window(hwnd, _):
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value != "Bienvenue dans Water Reminder":
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = kernel32.OpenProcess(0x1000, False, pid.value)
            if handle:
                try:
                    path = ctypes.create_unicode_buffer(32768)
                    size = wintypes.DWORD(len(path))
                    if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                        if Path(path.value) == executable:
                            windows.append(hwnd)
                finally:
                    kernel32.CloseHandle(handle)
            return True

        try:
            with tempfile.TemporaryDirectory() as temporary:
                environment = dict(os.environ, APPDATA=temporary)
                process = subprocess.Popen([str(executable)], env=environment)
                try:
                    deadline = time.monotonic() + 45
                    while not windows and process.poll() is None and time.monotonic() < deadline:
                        user32.EnumWindows(find_window, 0)
                        time.sleep(0.1)
                    self.assertTrue(windows, "L'assistant compilé ne s'est pas ouvert.")
                    self.assertTrue(user32.PostMessageW(windows[0], 0x10, 0, 0))
                    self.assertEqual(process.wait(timeout=15), 0)
                    data = Path(temporary) / "WaterReminder"
                    self.assertTrue((data / "settings.json").exists())
                    self.assertTrue((data / "messages.json").exists())
                    log = (data / "water-reminder.log").read_text(encoding="utf-8")
                    self.assertNotIn("ERROR", log)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=15)
        finally:
            if previous:
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, AUMID_KEY) as key:
                    for name in ("DisplayName", "IconUri"):
                        if name in previous:
                            value, kind = previous[name]
                            winreg.SetValueEx(key, name, 0, kind, value)
                        else:
                            try:
                                winreg.DeleteValue(key, name)
                            except FileNotFoundError:
                                pass
            else:
                try:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, AUMID_KEY)
                except FileNotFoundError:
                    pass
