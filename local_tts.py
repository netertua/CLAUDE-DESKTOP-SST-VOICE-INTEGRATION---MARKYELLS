#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKYELLS — 100% local TTS (pyttsx3 · Windows SAPI · macOS nsss)."""

from __future__ import annotations

import threading
from typing import Callable


class LocalTTS:
    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._ready = False
        self._message = ""

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def message(self) -> str:
        return self._message

    def _ensure(self) -> bool:
        if self._ready:
            return True
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._ready = True
            self._message = "Local TTS ready (offline · no API)"
            return True
        except Exception as exc:
            self._message = f"TTS unavailable: {exc}"
            return False

    def speak(
        self,
        text: str,
        on_done: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        if not text or not text.strip():
            return

        def worker() -> None:
            try:
                with self._lock:
                    if not self._ensure():
                        raise RuntimeError(self._message)
                    self._engine.say(text.strip())
                    self._engine.runAndWait()
                if on_done:
                    on_done()
            except Exception as exc:
                if on_error:
                    on_error(str(exc))

        threading.Thread(target=worker, daemon=True).start()