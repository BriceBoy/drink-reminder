"""Interactive validation of real Windows buttons, not mocked callbacks."""

import queue
import sys
import time
import uuid
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from water_reminder.config import Settings  # noqa: E402
from water_reminder.notifications import Notifications  # noqa: E402
from water_reminder.paths import resource_directory  # noqa: E402
from water_reminder.reminders import Action, ReminderEngine  # noqa: E402
from water_reminder.windows import register_application  # noqa: E402


def main() -> int:
    app_id = f"BriceBoy.WaterReminder.Test.{uuid.uuid4().hex}"
    events: queue.Queue[tuple[str, Action | str]] = queue.Queue()
    register_application(resource_directory() / "water.ico", app_id)
    engine = ReminderEngine(Settings("Test", 45, False, True))
    notifications = Notifications(
        activated=lambda token, action: events.put((token, action)),
        failed=lambda token, error: events.put(("error", error)),
        open_settings=lambda: events.put(("body", "body")),
        app_id=app_id,
    )
    try:
        for action, label, seconds in (
            ("drink", "J'ai bu !", 2700),
            ("snooze", "Rappeler dans 10 min", 600),
        ):
            reminder = engine.remind_now()
            if reminder is None:
                raise RuntimeError("Le moteur de test est arrêté ou en pause.")
            notifications.show(reminder, f"Test : cliquez sur « {label} ».")
            print(f"ATTENTE : {label} (120 s maximum)", flush=True)
            limit = time.monotonic() + 120
            while True:
                try:
                    token, received = events.get(timeout=max(0.01, limit - time.monotonic()))
                except queue.Empty:
                    raise RuntimeError(f"Le bouton « {label} » n'a pas été activé.") from None
                if token == "error":
                    raise RuntimeError(received)
                if token != reminder.token or received != action:
                    raise RuntimeError(f"Action inattendue : {token} / {received}")
                if not engine.act(token, received):
                    raise RuntimeError("Le moteur a refusé l'action native.")
                remaining = engine.remaining()
                if not seconds - 1 <= remaining <= seconds:
                    raise RuntimeError(f"Délai incorrect : {remaining} au lieu de {seconds}.")
                notifications.clear()
                print(f"PASS : bouton natif {action}, délai {remaining:.3f} s", flush=True)
                time.sleep(2)
                break
        print("PASS : les deux boutons Windows ont réellement appelé le moteur.", flush=True)
        return 0
    finally:
        notifications.clear()
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{app_id}")


if __name__ == "__main__":
    raise SystemExit(main())
