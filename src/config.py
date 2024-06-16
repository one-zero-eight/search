import os
from pathlib import Path

from src.config_schema import Settings, ApiSettings, BotSettings

settings_path = os.getenv("SETTINGS_PATH", "settings.yaml")
settings = Settings.from_yaml(Path(settings_path))
api_settings: ApiSettings | None = settings.api_settings
bot_settings: BotSettings | None = settings.bot_settings
