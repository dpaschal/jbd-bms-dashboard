from __future__ import annotations
import json
import os
from pathlib import Path

DEFAULT_SETTINGS: dict = {
    "cell_undervolt": 3.0,
    "cell_overvolt": 3.65,
    "pack_undervolt": 44.8,
    "temp_max": 45.0,
    "current_max": 100.0,
    "poll_interval": 1.0,
    "log_enabled": True,
    "log_dir": str(Path.home() / ".jbd-bms"),
}

_CONFIG_PATH = Path.home() / ".jbd-bms" / "settings.json"


def load_settings() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            saved = json.load(f)
        return {**DEFAULT_SETTINGS, **saved}
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(settings, f, indent=2)
