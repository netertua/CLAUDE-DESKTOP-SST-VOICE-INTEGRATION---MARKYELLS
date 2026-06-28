#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Reckon Shortcut + Auto-Paste + Press-to-Talk
Hold shortcut key(s) → record → transcribe → paste at Cursor caret.
"""

from __future__ import annotations

import platform
import queue
import tempfile
import threading
import wave
from pathlib import Path
from typing import Callable

import keyboard

from runtime_autodetect import AutoSpeechEngine, RuntimeProfile


def paste_to_active_window(text: str) -> None:
    """Paste transcribed text wherever the cursor is focused."""
    if not text:
        return
    try:
        import pyperclip

        pyperclip.copy(text)
    except ImportError:
        keyboard.write(text)
        return

    if platform.system() == "Darwin":
        keyboard.send("command+v")
    else:
        keyboard.send("ctrl+v")


class HoldRecorder:
    """Record audio while key/button is held."""

    def __init__(self, device_index: int | None = None, sample_rate: int = 16000):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self._frames: list = []
        self._stream = None
        self._lock = threading.Lock()

    def _callback(self, indata, _frames, _time, _status) -> None:
        with self._lock:
            self._frames.append(indata.copy())

    def start(self) -> None:
        import sounddevice as sd

        self._frames = []
        kwargs = {
            "samplerate": self.sample_rate,
            "channels": 1,
            "dtype": "float32",
            "callback": self._callback,
        }
        if self.device_index is not None:
            kwargs["device"] = self.device_index

        self._stream = sd.InputStream(**kwargs)
        self._stream.start()

    def stop(self) -> Path:
        import numpy as np

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._frames:
                raise RuntimeError("No audio captured. Hold longer or check microphone.")

            audio = np.concatenate(self._frames, axis=0)
            pcm = np.clip(audio[:, 0], -1.0, 1.0)
            pcm16 = (pcm * 32767).astype("int16")

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = Path(tmp.name)
        tmp.close()

        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm16.tobytes())

        return path


class ReckonShortcutController:
    """
    Global shortcut listener.
    - single: hold ONE key → record → release → transcribe → paste
    - combined: hold TWO keys together → record → release both → transcribe → paste
    """

    def __init__(
        self,
        engine: AutoSpeechEngine,
        key1: str = "f8",
        key2: str = "",
        mode: str = "single",
        enabled: bool = True,
        auto_paste: bool = True,
        mic_index: int | None = None,
        on_status: Callable[[str], None] | None = None,
        on_transcript: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self.engine = engine
        self.key1 = (key1 or "f8").strip().lower()
        self.key2 = (key2 or "").strip().lower()
        self.mode = mode if mode in {"single", "combined"} else "single"
        self.enabled = enabled
        self.auto_paste = auto_paste
        self.mic_index = mic_index
        self.on_status = on_status or (lambda _m: None)
        self.on_transcript = on_transcript or (lambda _t: None)
        self.on_error = on_error or (lambda _e: None)

        self._recorder: HoldRecorder | None = None
        self._recording = False
        self._pressed: set[str] = set()
        self._lock = threading.Lock()
        self._hooks: list = []

    @property
    def shortcut_label(self) -> str:
        if not self.enabled:
            return "Shortcut OFF"
        if self.mode == "combined" and self.key2:
            return f"Hold [{self.key1.upper()} + {self.key2.upper()}]"
        return f"Hold [{self.key1.upper()}]"

    def start(self) -> None:
        self.stop()
        if not self.enabled:
            return

        keys = {self.key1}
        if self.mode == "combined" and self.key2:
            keys.add(self.key2)

        for key in keys:
            self._hooks.append(keyboard.on_press_key(key, self._on_press, suppress=False))
            self._hooks.append(keyboard.on_release_key(key, self._on_release, suppress=False))

    def stop(self) -> None:
        for hook in self._hooks:
            try:
                hook()
            except Exception:
                pass
        self._hooks.clear()
        self._pressed.clear()
        self._recording = False
        self._recorder = None

    def _normalize(self, name: str) -> str:
        return (name or "").strip().lower()

    def _on_press(self, event) -> None:
        key = self._normalize(event.name)
        with self._lock:
            self._pressed.add(key)
            if self._should_start():
                self._begin_record()

    def _on_release(self, event) -> None:
        key = self._normalize(event.name)
        with self._lock:
            was_recording = self._recording
            self._pressed.discard(key)
            if was_recording and not self._should_hold():
                self._finish_record()

    def _should_start(self) -> bool:
        if self._recording:
            return False
        if self.mode == "combined" and self.key2:
            return self.key1 in self._pressed and self.key2 in self._pressed
        return self.key1 in self._pressed

    def _should_hold(self) -> bool:
        if self.mode == "combined" and self.key2:
            return self.key1 in self._pressed and self.key2 in self._pressed
        return self.key1 in self._pressed

    def _begin_record(self) -> None:
        self._recording = True
        self._recorder = HoldRecorder(device_index=self.mic_index)
        try:
            self._recorder.start()
            self.on_status(f"Listening… ({self.shortcut_label})")
        except Exception as exc:
            self._recording = False
            self._recorder = None
            self.on_error(str(exc))

    def _finish_record(self) -> None:
        recorder = self._recorder
        self._recording = False
        self._recorder = None

        if recorder is None:
            return

        def worker() -> None:
            try:
                self.on_status("Transcribing…")
                wav = recorder.stop()
                text = self.engine.transcribe_file(wav)
                wav.unlink(missing_ok=True)
                self.on_transcript(text)
                if self.auto_paste and text:
                    paste_to_active_window(text)
                    self.on_status("Pasted to cursor.")
                else:
                    self.on_status("Done.")
            except Exception as exc:
                self.on_error(str(exc))

        threading.Thread(target=worker, daemon=True).start()


class PressToTalkController:
    """
    Mic button modes when shortcut is OFF (WhatsApp-style).
    - hold: press and hold mic button to record, release to transcribe
    - toggle: click once to start, click again to stop
    """

    def __init__(
        self,
        engine: AutoSpeechEngine,
        mode: str = "hold",
        auto_paste: bool = True,
        mic_index: int | None = None,
        on_status: Callable[[str], None] | None = None,
        on_transcript: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self.engine = engine
        self.mode = mode if mode in {"hold", "toggle"} else "hold"
        self.auto_paste = auto_paste
        self.mic_index = mic_index
        self.on_status = on_status or (lambda _m: None)
        self.on_transcript = on_transcript or (lambda _t: None)
        self.on_error = on_error or (lambda _e: None)
        self._recorder: HoldRecorder | None = None
        self._toggle_active = False

    def mic_press(self) -> None:
        if self.mode == "hold":
            self._start()
        else:
            if self._toggle_active:
                self._stop_and_process()
            else:
                self._start()
                self._toggle_active = True

    def mic_release(self) -> None:
        if self.mode == "hold" and self._recorder is not None:
            self._stop_and_process()

    def _start(self) -> None:
        if self._recorder is not None:
            return
        self._recorder = HoldRecorder(device_index=self.mic_index)
        try:
            self._recorder.start()
            self.on_status("Listening… (release to stop)" if self.mode == "hold" else "Listening… (tap to stop)")
        except Exception as exc:
            self._recorder = None
            self.on_error(str(exc))

    def _stop_and_process(self) -> None:
        recorder = self._recorder
        self._recorder = None
        self._toggle_active = False
        if recorder is None:
            return

        def worker() -> None:
            try:
                self.on_status("Transcribing…")
                wav = recorder.stop()
                text = self.engine.transcribe_file(wav)
                wav.unlink(missing_ok=True)
                self.on_transcript(text)
                if self.auto_paste and text:
                    paste_to_active_window(text)
                    self.on_status("Pasted to cursor.")
                else:
                    self.on_status("Done.")
            except Exception as exc:
                self.on_error(str(exc))

        threading.Thread(target=worker, daemon=True).start()