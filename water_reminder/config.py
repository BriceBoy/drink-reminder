import json
import logging
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)
MAX_INTERVAL = 1440


@dataclass(frozen=True)
class Settings:
    name: str = "Vous"
    interval_minutes: int = 45
    autostart: bool = True
    setup_complete: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Le prénom ne peut pas être vide.")
        if len(self.name) > 80 or any(ord(char) < 32 for char in self.name):
            raise ValueError("Le prénom doit contenir au plus 80 caractères, sans saut de ligne.")
        if type(self.interval_minutes) is not int or not 1 <= self.interval_minutes <= MAX_INTERVAL:
            raise ValueError("L'intervalle doit être un entier entre 1 et 1440 minutes.")
        if type(self.autostart) is not bool or type(self.setup_complete) is not bool:
            raise ValueError("Les options de configuration doivent être des booléens.")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.warning: str | None = None

    def load(self) -> Settings:
        self.warning = None
        if not self.path.exists():
            settings = Settings()
            self.save(settings)
            return settings
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
            if not isinstance(raw, dict) or set(raw) != set(asdict(Settings())):
                raise ValueError("Structure des paramètres incorrecte.")
            return Settings(**raw)
        except (ValueError, TypeError, UnicodeError) as error:
            backup = self.path.with_name(f"settings.corrupt-{uuid.uuid4().hex}.json")
            self.path.rename(backup)
            LOGGER.warning("Configuration invalide, conservée dans %s : %s", backup, error)
            self.warning = (
                "Les paramètres étaient invalides. Une copie a été conservée dans "
                f"{backup}. Veuillez refaire la configuration."
            )
            settings = Settings()
            self.save(settings)
            return settings

    def save(self, settings: Settings) -> None:
        write_json(self.path, asdict(settings))
