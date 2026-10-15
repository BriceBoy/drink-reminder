import logging
import os
import queue
import shutil
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from tkinter import messagebox
from types import TracebackType

import pystray
from PIL import Image

from .config import Settings, SettingsStore
from .messages import MessageCatalog
from .notifications import Notifications
from .paths import APP_NAME, data_directory, launch_command, resource_directory
from .reminders import Action, Reminder, ReminderEngine
from .ui import SettingsDialog, configure_style, remaining_text
from .windows import SingleInstance, native_error, register_application, set_autostart

LOGGER = logging.getLogger(__name__)


class Application:
    def __init__(self, directory: Path) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.iconbitmap(str(resource_directory() / "water.ico"))
        configure_style(self.root)
        self.root.report_callback_exception = self.callback_error
        self.commands: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self.store = SettingsStore(directory / "settings.json")
        self.settings = self.store.load()
        self.engine = ReminderEngine(self.settings)
        self.dialog: SettingsDialog | None = None
        self.running = True
        self.tray: pystray.Icon | None = None
        self.tray_thread: threading.Thread | None = None
        self.catalog = MessageCatalog(
            directory / "messages.json",
            warn=lambda text: self.post(lambda: self.warning(text)),
        )
        self.catalog.initialize()
        icon = directory / "water.ico"
        shutil.copyfile(resource_directory() / "water.ico", icon)
        register_application(icon)
        self.notifications = Notifications(
            activated=lambda token, action: self.post(lambda: self.action(token, action)),
            failed=lambda token, error: self.post(lambda: self.notification_failed(token, error)),
            open_settings=lambda: self.post(self.open_settings),
        )

    def post(self, command: Callable[[], None]) -> None:
        self.commands.put(command)

    def run(self) -> None:
        try:
            if self.store.warning:
                self.warning(self.store.warning)
            if not self.settings.setup_complete:
                self.open_settings(first_run=True)
                if self.dialog is not None:
                    self.root.wait_window(self.dialog.window)
                if not self.settings.setup_complete:
                    return
            set_autostart(self.settings.autostart, launch_command())
            self.engine = ReminderEngine(self.settings)
            self.start_tray()
            self.root.after(250, self.pump)
            self.root.mainloop()
        finally:
            self.shutdown()

    def start_tray(self) -> None:
        def enqueue(command: Callable[[], None]) -> Callable[[], None]:
            return lambda: self.post(command)

        with Image.open(resource_directory() / "water.ico") as image:
            self.tray = pystray.Icon(
                "WaterReminder",
                image.copy(),
                APP_NAME,
                menu=pystray.Menu(
                    pystray.MenuItem("Paramètres", enqueue(self.open_settings), default=True),
                    pystray.MenuItem(
                        "Modifier mon prénom", enqueue(lambda: self.open_settings(focus="name"))
                    ),
                    pystray.MenuItem(
                        "Modifier l'intervalle des rappels",
                        enqueue(lambda: self.open_settings(focus="interval")),
                    ),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(
                        lambda _: "Reprendre les rappels"
                        if self.engine.paused
                        else "Mettre en pause",
                        enqueue(self.toggle_pause),
                    ),
                    pystray.MenuItem("Afficher le prochain rappel", enqueue(self.show_next)),
                    pystray.MenuItem("Tester une notification", enqueue(self.test_notification)),
                    pystray.MenuItem("Modifier les messages", enqueue(self.edit_messages)),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Quitter l'application", enqueue(self.quit)),
                ),
            )
        self.tray_thread = threading.Thread(target=self.tray_loop, name="system-tray", daemon=True)
        self.tray_thread.start()

    def tray_loop(self) -> None:
        try:
            if self.tray is not None:
                self.tray.run()
        except Exception:
            LOGGER.exception("Impossible de démarrer la zone de notification")
            self.post(lambda: self.fatal("L'icône Windows n'a pas pu démarrer."))

    def pump(self) -> None:
        if not self.running:
            return
        try:
            while not self.commands.empty() and self.running:
                self.commands.get_nowait()()
            if self.running:
                reminder = self.engine.tick()
                if reminder is not None:
                    self.show_reminder(reminder)
                if self.dialog is not None:
                    self.dialog.status.set(self.status())
        except Exception:
            LOGGER.exception("Erreur dans la boucle d'événements")
            self.handle_error("Une erreur est survenue. Les rappels ont été mis en pause.")
        finally:
            if self.running:
                self.root.after(250, self.pump)

    def status(self) -> str:
        remaining = remaining_text(self.engine.remaining())
        if self.engine.paused:
            return f"Rappels en pause · {remaining} à la reprise"
        return f"Prochain rappel dans {remaining}"

    def open_settings(self, first_run: bool = False, focus: str = "name") -> None:
        if self.dialog is not None:
            self.dialog.window.deiconify()
            self.dialog.window.lift()
            self.dialog.window.focus_force()
            return
        self.dialog = SettingsDialog(
            self.root,
            self.settings,
            self.save_settings,
            self.dialog_closed,
            self.status,
            first_run,
            focus,
        )

    def dialog_closed(self) -> None:
        self.dialog = None

    def save_settings(self, settings: Settings) -> None:
        command = launch_command()
        set_autostart(settings.autostart, command)
        try:
            self.store.save(settings)
        except OSError:
            try:
                set_autostart(self.settings.autostart, command)
            except OSError:
                LOGGER.exception("Échec de restauration du démarrage automatique")
                self.warning(
                    "Le démarrage automatique n'a pas pu être restauré. "
                    "Vérifiez les applications de démarrage dans les paramètres Windows."
                )
            raise
        content_changed = (
            settings.name != self.settings.name
            or settings.interval_minutes != self.settings.interval_minutes
        )
        self.settings = settings
        self.engine.update(settings)
        if content_changed:
            self.notifications.clear()
        LOGGER.info("Paramètres enregistrés (intervalle=%s min)", settings.interval_minutes)

    def show_reminder(self, reminder: Reminder) -> None:
        message = self.catalog.next_message(reminder.name)
        self.notifications.show(reminder, message)
        LOGGER.info("Rappel envoyé, prochain rappel vers %s", self.next_time())

    def next_time(self) -> str:
        return (datetime.now() + timedelta(seconds=self.engine.remaining())).strftime("%H:%M:%S")

    def action(self, token: str, action: Action) -> None:
        if self.engine.act(token, action):
            self.notifications.clear()
            LOGGER.info("Action de rappel : %s, prochain rappel vers %s", action, self.next_time())
        else:
            LOGGER.info("Action périmée ignorée")

    def notification_failed(self, token: str, error: str) -> None:
        if token == self.engine.active_token:
            LOGGER.error(error)
            self.handle_error(error)

    def toggle_pause(self) -> None:
        if self.engine.paused:
            self.engine.resume()
        else:
            self.engine.pause()
            self.notifications.clear()
        if self.tray is not None:
            self.tray.title = f"{APP_NAME} — {'En pause' if self.engine.paused else 'Actif'}"
            self.tray.update_menu()

    def test_notification(self) -> None:
        if self.engine.paused:
            messagebox.showinfo(APP_NAME, "Reprenez les rappels avant de tester.", parent=self.root)
            return
        reminder = self.engine.remind_now()
        if reminder is not None:
            self.show_reminder(reminder)

    def edit_messages(self) -> None:
        os.startfile(str(self.catalog.path))

    def show_next(self) -> None:
        messagebox.showinfo(APP_NAME, self.status(), parent=self.root)

    def warning(self, text: str) -> None:
        messagebox.showwarning(APP_NAME, text, parent=self.root)

    def handle_error(self, text: str) -> None:
        self.engine.pause()
        try:
            self.notifications.clear()
        except Exception:
            LOGGER.exception("Impossible de retirer la notification après une erreur")
            text += "\nWindows n'a pas permis de retirer l'ancienne notification."
        if self.tray is not None:
            self.tray.title = f"{APP_NAME} — En pause"
            self.tray.update_menu()
        messagebox.showerror(
            APP_NAME,
            text + "\nConsultez le journal dans %APPDATA%\\WaterReminder.",
            parent=self.root,
        )

    def callback_error(
        self, kind: type[BaseException], error: BaseException, trace: TracebackType | None
    ) -> None:
        LOGGER.error("Erreur d'interface", exc_info=(kind, error, trace))
        self.handle_error(str(error))

    def fatal(self, text: str) -> None:
        messagebox.showerror(APP_NAME, text, parent=self.root)
        self.quit()

    def quit(self) -> None:
        self.running = False
        self.engine.stop()
        self.root.quit()

    def shutdown(self) -> None:
        self.running = False
        self.engine.stop()
        try:
            self.notifications.clear()
        finally:
            if self.tray is not None:
                self.tray.stop()
            if self.tray_thread is not None:
                self.tray_thread.join(timeout=3)
                if self.tray_thread.is_alive():
                    LOGGER.error("L'icône Windows n'a pas terminé dans le délai prévu.")
            self.root.destroy()


def configure_logging(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / "water-reminder.log", maxBytes=512_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def main() -> int:
    if sys.platform != "win32":
        print("Water Reminder nécessite Windows 10 ou Windows 11.", file=sys.stderr)
        return 1
    instance = SingleInstance()
    try:
        if not instance.acquire():
            native_error(
                "Water Reminder est déjà lancé. Utilisez son icône dans la zone "
                "de notification (éventuellement sous la flèche des icônes masquées)."
            )
            return 0
        directory = data_directory()
        configure_logging(directory)
        Application(directory).run()
        return 0
    except Exception:
        LOGGER.exception("Échec du lancement ou de l'arrêt de Water Reminder")
        native_error(
            "Water Reminder n'a pas pu fonctionner.\n"
            "Consultez %APPDATA%\\WaterReminder\\water-reminder.log.\n"
            "En cas d'échec d'écriture, vérifiez les permissions du dossier utilisateur."
        )
        return 1
    finally:
        instance.close()
