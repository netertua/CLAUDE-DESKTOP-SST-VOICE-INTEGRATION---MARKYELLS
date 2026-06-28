#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Microphone permission probe + system settings launcher.
Windows · macOS (desktop & laptop · Intel & Apple Silicon)
"""

from __future__ import annotations

import platform
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MicPermissionStatus:
    ok: bool
    has_input_devices: bool
    test_passed: bool
    rms_level: float
    platform_label: str
    message: str
    needs_permission: bool
    settings_label: str
    settings_command: str


def _platform_label() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macOS · Apple Silicon"
    if system == "Darwin":
        return "macOS · Intel"
    if system == "Windows":
        return "Windows"
    return system


def open_microphone_settings() -> bool:
    """Open OS microphone privacy settings. Returns True if launch attempted."""
    try:
        if sys.platform == "win32":
            import os

            os.startfile("ms-settings:privacy-microphone")
            return True
        if sys.platform == "darwin":
            subprocess.Popen(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
    except Exception:
        pass
    return False


def _record_probe(seconds: float = 1.2, device_index: int | None = None) -> tuple[bool, float, str]:
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        return False, 0.0, "sounddevice not installed"

    seconds = max(0.5, min(3.0, seconds))
    try:
        kwargs: dict = {
            "frames": int(16000 * seconds),
            "samplerate": 16000,
            "channels": 1,
            "dtype": "float32",
        }
        if device_index is not None:
            kwargs["device"] = device_index
        audio = sd.rec(**kwargs)
        sd.wait()
        rms = float(np.sqrt(np.mean(np.square(audio))))
        return True, rms, ""
    except Exception as exc:
        return False, 0.0, str(exc)


def check_microphone_permission(device_index: int | None = None) -> MicPermissionStatus:
    """Probe mic list + short capture to detect permission / hardware issues."""
    plat = _platform_label()

    try:
        import sounddevice as sd

        devices = [d for d in sd.query_devices() if d.get("max_input_channels", 0) > 0]
        has_input = len(devices) > 0
    except Exception as exc:
        return MicPermissionStatus(
            ok=False,
            has_input_devices=False,
            test_passed=False,
            rms_level=0.0,
            platform_label=plat,
            message=f"Microphone scan failed: {exc}",
            needs_permission=True,
            settings_label=_settings_label(),
            settings_command=_settings_hint(),
        )

    if not has_input:
        return MicPermissionStatus(
            ok=False,
            has_input_devices=False,
            test_passed=False,
            rms_level=0.0,
            platform_label=plat,
            message="No microphone detected. Grant access in system settings.",
            needs_permission=True,
            settings_label=_settings_label(),
            settings_command=_settings_hint(),
        )

    captured, rms, err = _record_probe(device_index=device_index)
    # Silence threshold — permission denied often yields exception or near-zero with error
    test_passed = captured and not err and rms >= 0.0005
    needs_permission = not test_passed and (
        "permission" in err.lower()
        or "access" in err.lower()
        or "denied" in err.lower()
        or "unavailable" in err.lower()
        or not captured
    )

    if test_passed:
        msg = f"Microphone OK · signal level {rms:.4f}"
    elif needs_permission:
        msg = "Microphone access required. Open system settings and allow MARKYELLS / Python."
        if err:
            msg += f" ({err})"
    else:
        msg = f"Microphone detected but signal very low — check mute/volume. ({err or 'quiet input'})"

    return MicPermissionStatus(
        ok=test_passed,
        has_input_devices=has_input,
        test_passed=test_passed,
        rms_level=rms,
        platform_label=plat,
        message=msg,
        needs_permission=needs_permission or not test_passed,
        settings_label=_settings_label(),
        settings_command=_settings_hint(),
    )


def _settings_label() -> str:
    if sys.platform == "win32":
        return "Open Windows Microphone Privacy"
    if sys.platform == "darwin":
        return "Open macOS Microphone Privacy"
    return "Open System Microphone Settings"


def _settings_hint() -> str:
    if sys.platform == "win32":
        return "Settings → Privacy → Microphone → allow Python / MARKYELLS"
    if sys.platform == "darwin":
        return "System Settings → Privacy & Security → Microphone → enable for Terminal/Python"
    return "Enable microphone access for this application in OS settings."


def save_test_wav(seconds: float = 2.0, device_index: int | None = None) -> Path | None:
    """Record a short test clip; returns WAV path or None."""
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        return None

    kwargs: dict = {
        "frames": int(16000 * seconds),
        "samplerate": 16000,
        "channels": 1,
        "dtype": "float32",
    }
    if device_index is not None:
        kwargs["device"] = device_index

    try:
        audio = sd.rec(**kwargs)
        sd.wait()
        pcm = np.clip(audio[:, 0], -1.0, 1.0)
        pcm16 = (pcm * 32767).astype("int16")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = Path(tmp.name)
        tmp.close()
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(pcm16.tobytes())
        return path
    except Exception:
        return None