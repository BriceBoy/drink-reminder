import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .config import Settings

Action = Literal["drink", "snooze"]
SNOOZE_SECONDS = 600


@dataclass(frozen=True)
class Reminder:
    token: str
    name: str


class ReminderEngine:
    """Single-threaded state machine, independent of the UI and Windows."""

    def __init__(self, settings: Settings, clock: Callable[[], float] = time.monotonic) -> None:
        self.settings = settings
        self.clock = clock
        self.paused = False
        self.stopped = False
        self.active_token: str | None = None
        self.deadline = clock() + settings.interval_minutes * 60
        self.pause_remaining = float(settings.interval_minutes * 60)

    def remaining(self) -> float:
        if self.stopped:
            return 0
        return self.pause_remaining if self.paused else max(0, self.deadline - self.clock())

    def tick(self) -> Reminder | None:
        if self.stopped or self.paused or self.clock() < self.deadline:
            return None
        return self.remind_now()

    def remind_now(self) -> Reminder | None:
        if self.stopped or self.paused:
            return None
        self.active_token = uuid.uuid4().hex
        self.deadline = self.clock() + self.settings.interval_minutes * 60
        return Reminder(self.active_token, self.settings.name)

    def unlocked(self) -> Reminder | None:
        """Re-show an unanswered or overdue reminder; its interval restarts from the unlock."""
        if self.stopped or self.paused:
            return None
        if self.active_token is None and self.clock() < self.deadline:
            return None
        return self.remind_now()

    def act(self, token: str, action: Action) -> bool:
        if action not in ("drink", "snooze"):
            raise ValueError(f"Action de rappel inconnue : {action}")
        if self.stopped or self.paused or token != self.active_token:
            return False
        self.active_token = None
        delay = SNOOZE_SECONDS if action == "snooze" else self.settings.interval_minutes * 60
        self.deadline = self.clock() + delay
        return True

    def update(self, settings: Settings) -> None:
        interval_changed = settings.interval_minutes != self.settings.interval_minutes
        name_changed = settings.name != self.settings.name
        self.settings = settings
        if interval_changed:
            self.active_token = None
            self.pause_remaining = float(settings.interval_minutes * 60)
            self.deadline = self.clock() + self.pause_remaining
        elif name_changed:
            self.active_token = None

    def pause(self) -> None:
        if self.stopped or self.paused:
            return
        self.pause_remaining = self.remaining()
        self.active_token = None
        self.paused = True

    def resume(self) -> None:
        if self.stopped or not self.paused:
            return
        self.deadline = self.clock() + self.pause_remaining
        self.paused = False

    def stop(self) -> None:
        self.active_token = None
        self.stopped = True
