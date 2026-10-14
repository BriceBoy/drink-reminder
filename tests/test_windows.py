import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


@unittest.skipUnless(sys.platform == "win32", "Windows uniquement")
class WindowsTests(unittest.TestCase):
    def test_single_instance_across_processes_and_release(self) -> None:
        from water_reminder.windows import SingleInstance

        name = rf"Local\WaterReminder.Test.{uuid.uuid4().hex}"
        instance = SingleInstance(name)
        self.addCleanup(instance.close)
        self.assertTrue(instance.acquire())
        script = (
            "from water_reminder.windows import SingleInstance;"
            f"m=SingleInstance({name!r});print(m.acquire());m.close()"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=True
        )
        self.assertEqual(result.stdout.strip(), "False")
        instance.close()
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=True
        )
        self.assertEqual(result.stdout.strip(), "True")

    def test_autostart_quotes_command_and_can_disable(self) -> None:
        from water_reminder import windows

        command = [r"C:\Program Files\WaterReminder\WaterReminder.exe"]
        with (
            patch.object(windows.winreg, "CreateKeyEx"),
            patch.object(windows.winreg, "SetValueEx") as set_value,
            patch.object(windows.winreg, "DeleteValue") as delete_value,
        ):
            windows.set_autostart(True, command)
            self.assertEqual(set_value.call_args.args[-1], f'"{command[0]}"')
            windows.set_autostart(False, command)
            self.assertEqual(delete_value.call_args.args[-1], "WaterReminder")

    def test_native_toast_content_callbacks_and_clear(self) -> None:
        from winrt.windows.ui.notifications import NotificationSetting

        from water_reminder.notifications import Notifications
        from water_reminder.reminders import Reminder

        with patch("water_reminder.notifications.InteractableWindowsToaster") as factory:
            toaster = factory.return_value
            toaster.toastNotifier.setting = NotificationSetting.ENABLED
            activated, failed, opened = MagicMock(), MagicMock(), MagicMock()
            notifications = Notifications(activated, failed, opened)
            notifications.show(Reminder("token", "Brice"), "Bonjour Brice <&> !")
            toast = notifications.current
            native = notifications.native
            toaster.toastNotifier.show.assert_called_once_with(native)
            self.assertEqual(toast.images, [])
            self.assertEqual([action.arguments for action in toast.actions], ["drink", "snooze"])
            self.assertEqual(
                [action.content for action in toast.actions], ["J'ai bu !", "Rappeler dans 10 min"]
            )
            toast.on_activated(SimpleNamespace(arguments="drink"))
            activated.assert_called_with("token", "drink")
            toast.on_activated(SimpleNamespace(arguments="snooze"))
            activated.assert_called_with("token", "snooze")
            toast.on_activated(SimpleNamespace(arguments="body"))
            opened.assert_called_once()
            toast.on_failed(SimpleNamespace(error_code=-1))
            failed.assert_called_once()
            notifications.clear()
            toaster.toastNotifier.hide.assert_called_once_with(native)
            self.assertIsNone(notifications.current)
            self.assertIsNone(notifications.native)

    def test_windows_notifications_disabled_is_explicit_error(self) -> None:
        from winrt.windows.ui.notifications import NotificationSetting

        from water_reminder.notifications import Notifications
        from water_reminder.reminders import Reminder

        with patch("water_reminder.notifications.InteractableWindowsToaster") as factory:
            factory.return_value.toastNotifier.setting = NotificationSetting.DISABLED_FOR_USER
            notifications = Notifications(MagicMock(), MagicMock(), MagicMock())
            with self.assertRaisesRegex(RuntimeError, "désactivées"):
                notifications.show(Reminder("token", "Brice"), "Bonjour Brice")

    def test_xml_is_native_and_escapes_text(self) -> None:
        from winrt.windows.ui.notifications import NotificationSetting

        from water_reminder.notifications import Notifications, build_document
        from water_reminder.reminders import Reminder

        with patch("water_reminder.notifications.InteractableWindowsToaster") as factory:
            factory.return_value.toastNotifier.setting = NotificationSetting.ENABLED
            notifications = Notifications(MagicMock(), MagicMock(), MagicMock())
            notifications.show(Reminder("token", "Brice"), "Brice <&> !")
            xml = build_document(notifications.current).get_xml()
            self.assertIn("ToastGeneric", xml)
            self.assertIn("&lt;&amp;&gt;", xml)
            self.assertNotIn("<image", xml)
            self.assertEqual(xml.count("<action "), 2)

    def test_settings_dialog_validates_saves_and_cancels(self) -> None:
        import tkinter as tk

        from water_reminder.config import Settings
        from water_reminder.ui import SettingsDialog, configure_style

        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        configure_style(root)
        save, closed = MagicMock(), MagicMock()
        dialog = SettingsDialog(root, Settings(), save, closed, lambda: "test")
        dialog.name.set("  Brice  ")
        dialog.interval.set("0")
        with patch("water_reminder.ui.messagebox.showerror") as error:
            dialog.submit()
            error.assert_called_once()
            save.assert_not_called()
        dialog.interval.set("30")
        dialog.autostart.set(False)
        dialog.submit()
        save.assert_called_once_with(Settings("Brice", 30, False, True))
        closed.assert_called_once()
        cancelled = SettingsDialog(root, Settings(), save, closed, lambda: "test")
        cancelled.close()
        self.assertEqual(save.call_count, 1)
        self.assertEqual(closed.call_count, 2)

    def test_assets_exist(self) -> None:
        from PIL import Image

        from water_reminder.paths import resource_directory

        for filename in ("water.ico", "water.png"):
            with Image.open(Path(resource_directory()) / filename) as image:
                image.verify()

    def test_real_tray_and_application_event_queue(self) -> None:
        from water_reminder.app import Application
        from water_reminder.config import Settings, SettingsStore

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            SettingsStore(directory / "settings.json").save(Settings("Brice", 1, False, True))
            with (
                patch("water_reminder.app.register_application"),
                patch("water_reminder.app.set_autostart"),
                patch("water_reminder.app.Notifications") as factory,
                patch("water_reminder.app.messagebox.showinfo") as info,
            ):
                app = Application(directory)
                try:
                    app.start_tray()
                    deadline = time.monotonic() + 5
                    while not app.tray.visible and time.monotonic() < deadline:
                        app.root.update()
                        time.sleep(0.05)
                    self.assertTrue(app.tray.visible, "L'icône Windows ne s'est pas affichée.")
                    app.engine.deadline = app.engine.clock()
                    app.pump()
                    factory.return_value.show.assert_called_once()
                    token = app.engine.active_token
                    app.post(lambda: app.action(token, "snooze"))
                    app.pump()
                    self.assertGreater(app.engine.remaining(), 599)
                    self.assertLessEqual(app.engine.remaining(), 600)
                    menu = {str(item.text): item for item in app.tray.menu}
                    menu["Afficher le prochain rappel"](app.tray)
                    app.pump()
                    info.assert_called_once()
                    menu["Mettre en pause"](app.tray)
                    app.pump()
                    self.assertTrue(app.engine.paused)
                    app.toggle_pause()
                    self.assertFalse(app.engine.paused)
                    menu["Quitter l'application"](app.tray)
                    app.pump()
                    self.assertFalse(app.running)
                    self.assertTrue(app.engine.stopped)
                finally:
                    app.shutdown()


if __name__ == "__main__":
    unittest.main()
