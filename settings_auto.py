#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKYELLS — shared settings (CTk + Qt launchers)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings_auto.json"


@dataclass
class AutoSettings:
    show_warning_on_startup: bool = True
    warning_duration_seconds: int = 10
    record_seconds: int = 5
    reckon_shortcut_enabled: bool = True
    shortcut_mode: str = "single"
    shortcut_key1: str = "f8"
    shortcut_key2: str = "shift"
    auto_paste: bool = True
    ptt_mode: str = "hold"
    mic_device_index: int | None = None
    speech_language: str = "auto"
    speech_engine_override: str = "auto"
    tts_enabled: bool = True
    auto_listen_test_on_startup: bool = True

    @classmethod
    def load(cls) -> "AutoSettings":
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not SETTINGS_FILE.exists():
            return cls()
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            mic_raw = data.get("mic_device_index")
            return cls(
                show_warning_on_startup=bool(data.get("show_warning_on_startup", True)),
                warning_duration_seconds=int(data.get("warning_duration_seconds", 10)),
                record_seconds=int(data.get("record_seconds", 5)),
                reckon_shortcut_enabled=bool(data.get("reckon_shortcut_enabled", True)),
                shortcut_mode=str(data.get("shortcut_mode", "single")),
                shortcut_key1=str(data.get("shortcut_key1", "f8")),
                shortcut_key2=str(data.get("shortcut_key2", "shift")),
                auto_paste=bool(data.get("auto_paste", True)),
                ptt_mode=str(data.get("ptt_mode", "hold")),
                mic_device_index=int(mic_raw) if mic_raw is not None else None,
                speech_language=str(data.get("speech_language", "auto")),
                speech_engine_override=str(data.get("speech_engine_override", "auto")),
                tts_enabled=bool(data.get("tts_enabled", True)),
                auto_listen_test_on_startup=bool(data.get("auto_listen_test_on_startup", True)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )