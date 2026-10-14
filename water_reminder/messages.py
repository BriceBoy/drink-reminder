import json
import logging
import random
from collections.abc import Callable, Sequence
from pathlib import Path
from string import Formatter

from .config import write_json
from .paths import resource_directory

LOGGER = logging.getLogger(__name__)
DEFAULT_MESSAGES = (
    "Bonjour {name} ! Une petite pause pour boire de l'eau ?",
    "{name}, pense à t'hydrater ! Ton corps te remerciera.",
    "C'est l'heure du verre d'eau, {name} !",
    "Petite pause hydratation pour {name} !",
    "{name}, quelques gorgées d'eau et on repart !",
    "N'oublie pas de boire régulièrement, {name} !",
)


def validate_messages(raw: object) -> list[str]:
    if not isinstance(raw, dict) or not isinstance(raw.get("messages"), list):
        raise ValueError("Un objet contenant une liste 'messages' est nécessaire.")
    values = raw["messages"]
    if not 1 <= len(values) <= 1000:
        raise ValueError("La liste doit contenir de 1 à 1000 messages.")
    messages = []
    for text in values:
        if not isinstance(text, str) or not text.strip() or len(text) > 500:
            raise ValueError("Chaque message doit contenir de 1 à 500 caractères.")
        for _, field, spec, conversion in Formatter().parse(text):
            if field is not None and (field != "name" or spec or conversion):
                raise ValueError("Seul le marqueur {name} est autorisé.")
        if text not in messages:
            messages.append(text)
    return messages


class MessageCatalog:
    def __init__(
        self,
        path: Path,
        choose: Callable[[Sequence[str]], str] = random.choice,
        warn: Callable[[str], None] | None = None,
    ) -> None:
        self.path = path
        self.choose = choose
        self.warn = warn
        self.previous: str | None = None
        self.last_error: str | None = None

    def initialize(self) -> None:
        if not self.path.exists():
            bundled = resource_directory() / "messages.json"
            messages = validate_messages(json.loads(bundled.read_text(encoding="utf-8-sig")))
            write_json(self.path, {"messages": messages})

    def next_message(self, name: str) -> str:
        try:
            messages = validate_messages(json.loads(self.path.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError, UnicodeError) as error:
            warning = f"Messages personnalisés indisponibles ({self.path}) : {error}"
            LOGGER.warning(warning)
            if self.warn is not None and warning != self.last_error:
                self.warn(warning + "\nLes messages intégrés seront utilisés.")
            self.last_error = warning
            messages = list(DEFAULT_MESSAGES)
        else:
            self.last_error = None
        candidates = [text for text in messages if text != self.previous] or messages
        self.previous = self.choose(candidates)
        return self.previous.format(name=name)
