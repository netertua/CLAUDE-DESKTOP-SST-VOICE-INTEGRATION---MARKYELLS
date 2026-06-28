#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Markyells için MLX tabanlı masaüstü uygulaması.

Çalıştırma:
    python main.py

macOS + Apple Silicon için MLX kurulumu:
    pip install -r requirements.txt
"""

from __future__ import annotations

import customtkinter as ctk

from app.main_window import launch_app
from app.settings_store import AppSettings
from app.splash import WarningSplash


def run() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    settings = AppSettings.load()
    root = ctk.CTk()
    root.withdraw()

    def open_main(_dont_show_again: bool = False) -> None:
        if _dont_show_again:
            settings.show_warning_on_startup = False
            settings.save()
        root.destroy()
        launch_app(settings)

    if settings.show_warning_on_startup:
        splash = WarningSplash(
            duration_seconds=settings.warning_duration_seconds,
            on_complete=open_main,
        )
        splash.mainloop()
    else:
        root.destroy()
        launch_app(settings)


if __name__ == "__main__":
    run()