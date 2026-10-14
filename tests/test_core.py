import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from water_reminder.config import Settings, SettingsStore, write_json
from water_reminder.messages import DEFAULT_MESSAGES, MessageCatalog
from water_reminder.reminders import ReminderEngine


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "settings.json"
        self.store = SettingsStore(self.path)

    def test_defaults_created(self) -> None:
        self.assertEqual(self.store.load(), Settings())
        self.assertTrue(self.path.exists())
        self.assertIsNone(self.store.warning)

    def test_roundtrip_and_restart(self) -> None:
        settings = Settings("Brice", 45, False, True)
        self.store.save(settings)
        self.assertEqual(SettingsStore(self.path).load(), settings)

    def test_corruption_preserved_and_reported(self) -> None:
        self.path.write_text("{invalid", encoding="utf-8")
        with self.assertLogs("water_reminder.config", level="WARNING"):
            self.assertEqual(self.store.load(), Settings())
        backup = list(self.path.parent.glob("settings.corrupt-*.json"))
        self.assertEqual(len(backup), 1)
        self.assertEqual(backup[0].read_text(encoding="utf-8"), "{invalid")
        self.assertIsNotNone(self.store.warning)

    def test_invalid_configuration_loaded(self) -> None:
        for raw in (
            [],
            {},
            {"name": "Brice"},
            {"name": "Brice", "interval_minutes": 0, "autostart": True, "setup_complete": True},
        ):
            with self.subTest(raw=raw):
                write_json(self.path, raw)
                with self.assertLogs("water_reminder.config", level="WARNING"):
                    self.assertEqual(self.store.load(), Settings())

    def test_validation(self) -> None:
        for kwargs in (
            {"name": ""},
            {"name": " "},
            {"name": "x" * 81},
            {"name": "A\nB"},
            {"interval_minutes": 0},
            {"interval_minutes": -1},
            {"interval_minutes": 1441},
            {"interval_minutes": True},
            {"interval_minutes": 1.5},
            {"interval_minutes": "45"},
            {"autostart": "yes"},
            {"setup_complete": 1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Settings(**kwargs)
        self.assertEqual(Settings("Élodie", 1440).interval_minutes, 1440)
        self.assertEqual(Settings(interval_minutes=1).interval_minutes, 1)

    def test_atomic_save_failure_preserves_old_data(self) -> None:
        self.store.save(Settings("Brice"))
        with patch("water_reminder.config.os.replace", side_effect=PermissionError("Denied")):
            with self.assertRaises(PermissionError):
                self.store.save(Settings("Alice"))
        self.assertEqual(self.store.load().name, "Brice")
        self.assertFalse(list(self.path.parent.glob("*.tmp")))

    def test_io_error_not_hidden_as_default(self) -> None:
        self.store.save(Settings())
        with patch.object(Path, "read_text", side_effect=PermissionError("Denied")):
            with self.assertRaises(PermissionError):
                self.store.load()


class ReminderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = Clock()
        self.settings = Settings("Brice", 45, False, True)
        self.engine = ReminderEngine(self.settings, self.clock)

    def due(self):
        self.clock.advance(self.engine.remaining())
        reminder = self.engine.tick()
        self.assertIsNotNone(reminder)
        return reminder

    def test_exact_interval_and_no_duplicate(self) -> None:
        self.clock.advance(2699.999)
        self.assertIsNone(self.engine.tick())
        self.clock.advance(0.001)
        reminder = self.engine.tick()
        self.assertEqual(reminder.name, "Brice")
        self.assertIsNone(self.engine.tick())
        self.assertEqual(self.engine.remaining(), 2700)

    def test_drink_resets_from_click(self) -> None:
        reminder = self.due()
        self.clock.advance(13)
        self.assertTrue(self.engine.act(reminder.token, "drink"))
        self.assertEqual(self.engine.remaining(), 2700)
        self.assertFalse(self.engine.act(reminder.token, "drink"))
        self.assertIsNone(self.engine.tick())

    def test_snooze_exact_600_seconds_and_repeat(self) -> None:
        for _ in range(3):
            reminder = self.due()
            self.clock.advance(17)
            self.assertTrue(self.engine.act(reminder.token, "snooze"))
            self.assertEqual(self.engine.remaining(), 600)
            self.clock.advance(599.999)
            self.assertIsNone(self.engine.tick())
            self.clock.advance(0.001)
        self.assertEqual(self.engine.settings.interval_minutes, 45)
        reminder = self.engine.tick()
        self.assertTrue(self.engine.act(reminder.token, "drink"))
        self.assertEqual(self.engine.remaining(), 2700)

    def test_stale_action_ignored_after_new_reminder(self) -> None:
        first = self.due()
        second = self.due()
        deadline = self.engine.deadline
        self.assertNotEqual(first.token, second.token)
        self.assertFalse(self.engine.act(first.token, "snooze"))
        self.assertEqual(self.engine.deadline, deadline)

    def test_ignored_or_closed_notification_repeats_normally(self) -> None:
        first = self.due()
        self.clock.advance(2700)
        second = self.engine.tick()
        self.assertNotEqual(first.token, second.token)

    def test_interval_change_cancels_snooze(self) -> None:
        reminder = self.due()
        self.engine.act(reminder.token, "snooze")
        self.clock.advance(40)
        self.engine.update(replace(self.settings, interval_minutes=30))
        self.assertEqual(self.engine.remaining(), 1800)
        self.assertIsNone(self.engine.active_token)

    def test_name_change_preserves_timer_but_invalidates_old_action(self) -> None:
        reminder = self.due()
        deadline = self.engine.deadline
        self.engine.update(replace(self.settings, name="Alice"))
        self.assertEqual(self.engine.deadline, deadline)
        self.assertFalse(self.engine.act(reminder.token, "drink"))
        self.assertEqual(self.due().name, "Alice")

    def test_autostart_only_change_preserves_notification(self) -> None:
        reminder = self.due()
        self.engine.update(replace(self.settings, autostart=True))
        self.assertEqual(self.engine.active_token, reminder.token)

    def test_pause_resume_freezes_remaining_and_invalidates_actions(self) -> None:
        reminder = self.due()
        self.clock.advance(60)
        self.engine.pause()
        self.clock.advance(50000)
        self.assertIsNone(self.engine.tick())
        self.assertEqual(self.engine.remaining(), 2640)
        self.assertFalse(self.engine.act(reminder.token, "snooze"))
        self.engine.pause()
        self.engine.resume()
        self.assertEqual(self.engine.remaining(), 2640)
        self.engine.resume()
        self.assertEqual(self.engine.remaining(), 2640)

    def test_change_interval_while_paused(self) -> None:
        self.engine.pause()
        self.engine.update(replace(self.settings, interval_minutes=10))
        self.clock.advance(500)
        self.engine.resume()
        self.assertEqual(self.engine.remaining(), 600)

    def test_resume_from_sleep_only_sends_one(self) -> None:
        self.clock.advance(8 * 3600)
        self.assertIsNotNone(self.engine.tick())
        self.assertIsNone(self.engine.tick())
        self.assertEqual(self.engine.remaining(), 2700)

    def test_stop_and_restart_uses_full_interval(self) -> None:
        reminder = self.due()
        self.engine.stop()
        self.clock.advance(50000)
        self.assertIsNone(self.engine.tick())
        self.assertIsNone(self.engine.remind_now())
        self.assertFalse(self.engine.act(reminder.token, "drink"))
        restarted = ReminderEngine(self.settings, self.clock)
        self.assertEqual(restarted.remaining(), 2700)
        self.assertIsNone(restarted.active_token)

    def test_invalid_action_explicit_error(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.act("invalid", "unknown")


class MessagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "messages.json"
        self.warnings: list[str] = []
        self.catalog = MessageCatalog(
            self.path, choose=lambda values: values[0], warn=self.warnings.append
        )
        self.catalog.initialize()

    def save(self, messages: object) -> None:
        write_json(self.path, {"messages": messages})

    def test_initial_defaults(self) -> None:
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8"))["messages"], list(DEFAULT_MESSAGES)
        )

    def test_markers_personalization_and_live_reload(self) -> None:
        self.save(["Salut {name} / {name}"])
        self.assertEqual(self.catalog.next_message("Brice"), "Salut Brice / Brice")
        self.save(["Bienvenue {name}"])
        self.assertEqual(self.catalog.next_message("Élodie"), "Bienvenue Élodie")

    def test_no_repeat_and_duplicate_entries_removed(self) -> None:
        self.save(["A {name}", "A {name}", "B {name}"])
        results = [self.catalog.next_message("Brice") for _ in range(4)]
        self.assertEqual(results, ["A Brice", "B Brice", "A Brice", "B Brice"])

    def test_one_message_can_repeat(self) -> None:
        self.save(["A {name}"])
        self.assertEqual(self.catalog.next_message("Brice"), self.catalog.next_message("Brice"))

    def test_absent_file_falls_back_with_warning(self) -> None:
        self.path.unlink()
        with self.assertLogs("water_reminder.messages", level="WARNING"):
            self.assertIn("Brice", self.catalog.next_message("Brice"))
            self.catalog.next_message("Brice")
        self.assertEqual(len(self.warnings), 1)

    def test_invalid_catalogs_fall_back(self) -> None:
        for invalid in (
            [],
            [" "],
            [42],
            ["{unknown}"],
            ["{name.upper}"],
            ["{name!r}"],
            ["{name:>20}"],
            ["{"],
            ["x" * 501],
        ):
            with self.subTest(invalid=invalid):
                self.save(invalid)
                with self.assertLogs("water_reminder.messages", level="WARNING"):
                    self.assertIn("Brice", self.catalog.next_message("Brice"))

    def test_broken_json_and_permission_error_fall_back(self) -> None:
        self.path.write_text("broken", encoding="utf-8")
        with self.assertLogs("water_reminder.messages", level="WARNING"):
            self.assertIn("Brice", self.catalog.next_message("Brice"))
        with patch.object(Path, "read_text", side_effect=PermissionError("Denied")):
            with self.assertLogs("water_reminder.messages", level="WARNING"):
                self.assertIn("Alice", self.catalog.next_message("Alice"))


if __name__ == "__main__":
    unittest.main()
