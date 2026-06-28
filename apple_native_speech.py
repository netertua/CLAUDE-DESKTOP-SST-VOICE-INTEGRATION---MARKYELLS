#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Apple Speech Framework (macOS built-in, on-device)
SFSpeechRecognizer via PyObjC (optional). Desktop + laptop Macs.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppleSpeechStatus:
    available: bool
    framework_present: bool
    pyobjc_installed: bool
    on_device_supported: bool
    macos_version: str
    message: str
    locales: tuple[str, ...] = ()
    details: tuple[str, ...] = ()


def _macos_version() -> str:
    if sys.platform != "darwin":
        return ""
    try:
        out = subprocess.check_output(
            ["sw_vers", "-productVersion"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return platform.mac_ver()[0]


def _framework_present() -> bool:
    if sys.platform != "darwin":
        return False
    return Path("/System/Library/Frameworks/Speech.framework").exists()


def _on_device_likely(macos_version: str) -> bool:
    """On-device recognition broadly available macOS 13+."""
    if not macos_version:
        return False
    try:
        major = int(macos_version.split(".")[0])
        return major >= 13
    except (ValueError, IndexError):
        return False


def probe_apple_speech() -> AppleSpeechStatus:
    """Probe macOS built-in Speech Framework without requiring PyObjC."""
    if sys.platform != "darwin":
        return AppleSpeechStatus(
            available=False,
            framework_present=False,
            pyobjc_installed=False,
            on_device_supported=False,
            macos_version="",
            message="Apple Speech Framework is macOS-only.",
            details=("Windows uses faster-whisper (local) instead.",),
        )

    mac_ver = _macos_version()
    fw = _framework_present()
    on_device = _on_device_likely(mac_ver)

    pyobjc_ok = False
    locales: list[str] = []
    extra: list[str] = [
        "Engine: Apple Speech Framework (SFSpeechRecognizer)",
        "Cost: $0 — built into macOS, no API billing",
        "Works on: MacBook + iMac + Mac mini + Mac Studio (desktop & laptop)",
    ]

    try:
        import Speech  # type: ignore[import-untyped]
        import Foundation  # type: ignore[import-untyped]

        pyobjc_ok = True
        for tag in ("en-US", "th-TH", "en-TH"):
            loc = Foundation.NSLocale.alloc().initWithLocaleIdentifier_(tag)
            rec = Speech.SFSpeechRecognizer.alloc().initWithLocale_(loc)
            if rec is not None and rec.isAvailable():
                locales.append(tag)
        if on_device:
            extra.append("On-device mode: likely supported (macOS 13+)")
        else:
            extra.append("On-device mode: may require network on older macOS")
    except ImportError:
        extra.append("PyObjC missing: pip install pyobjc-framework-Speech pyobjc-framework-AVFoundation")
    except Exception as exc:
        extra.append(f"PyObjC probe error: {exc}")

    if not fw:
        return AppleSpeechStatus(
            available=False,
            framework_present=False,
            pyobjc_installed=pyobjc_ok,
            on_device_supported=on_device,
            macos_version=mac_ver,
            message="Speech.framework not found on this Mac.",
            details=tuple(extra),
        )

    if pyobjc_ok and locales:
        return AppleSpeechStatus(
            available=True,
            framework_present=True,
            pyobjc_installed=True,
            on_device_supported=on_device,
            macos_version=mac_ver,
            message="Apple Speech Framework ready (local, built-in macOS).",
            locales=tuple(locales),
            details=tuple(extra + [f"Locales: {', '.join(locales)}"]),
        )

    if fw:
        return AppleSpeechStatus(
            available=False,
            framework_present=True,
            pyobjc_installed=pyobjc_ok,
            on_device_supported=on_device,
            macos_version=mac_ver,
            message="Speech.framework present — install PyObjC to enable in MARKYELLS.",
            details=tuple(
                extra
                + [
                    "pip install pyobjc-framework-Speech pyobjc-framework-AVFoundation",
                    "Grant Speech Recognition permission in System Settings → Privacy",
                ]
            ),
        )

    return AppleSpeechStatus(
        available=False,
        framework_present=fw,
        pyobjc_installed=pyobjc_ok,
        on_device_supported=on_device,
        macos_version=mac_ver,
        message="Apple Speech Framework unavailable.",
        details=tuple(extra),
    )


def _locale_for_language(language: str) -> str:
    if language == "th":
        return "th-TH"
    if language == "en":
        return "en-US"
    return "en-US"


def transcribe_file(audio_path: Path, language: str = "auto") -> str:
    """Transcribe WAV via Apple SFSpeechRecognizer (macOS only)."""
    if sys.platform != "darwin":
        raise RuntimeError("Apple Speech Framework is macOS-only.")

    status = probe_apple_speech()
    if not status.available:
        raise RuntimeError(status.message)

    import Speech  # type: ignore[import-untyped]
    import Foundation  # type: ignore[import-untyped]

    locale_id = _locale_for_language(language)
    locale = Foundation.NSLocale.alloc().initWithLocaleIdentifier_(locale_id)
    recognizer = Speech.SFSpeechRecognizer.alloc().initWithLocale_(locale)
    if recognizer is None or not recognizer.isAvailable():
        raise RuntimeError(f"Apple Speech not available for locale {locale_id}")

    auth = Speech.SFSpeechRecognizer.authorizationStatus()
    if auth == 0:  # notDetermined
        done = Foundation.NSCondition.alloc().init()
        granted_box: list[bool] = []

        def handler(status_code: int) -> None:
            granted_box.append(status_code == 3)
            done.lock()
            done.signal()
            done.unlock()

        Speech.SFSpeechRecognizer.requestAuthorization_(handler)
        done.lock()
        done.wait()
        done.unlock()
        if not granted_box or not granted_box[0]:
            raise RuntimeError("Speech Recognition permission denied in System Settings.")
    elif auth != 3:  # authorized
        raise RuntimeError("Speech Recognition not authorized. Enable in System Settings → Privacy.")

    url = Foundation.NSURL.fileURLWithPath_(str(audio_path.resolve()))
    request = Speech.SFSpeechURLRecognitionRequest.alloc().initWithURL_(url)
    if request is None:
        raise RuntimeError("Could not create speech recognition request.")

    if status.on_device_supported and hasattr(request, "setRequiresOnDeviceRecognition_"):
        request.setRequiresOnDeviceRecognition_(True)

    result_box: list[str] = []
    error_box: list[str] = []
    done = Foundation.NSCondition.alloc().init()

    def handler(result, error) -> None:
        if error is not None:
            error_box.append(str(error))
        elif result is not None and result.isFinal():
            result_box.append(str(result.bestTranscription().formattedString()))
        if (error is not None) or (result is not None and result.isFinal()):
            done.lock()
            done.signal()
            done.unlock()

    recognizer.recognitionTaskWithRequest_resultHandler_(request, handler)
    done.lock()
    done.wait()
    done.unlock()

    if error_box:
        raise RuntimeError(error_box[0])
    if not result_box:
        return ""
    return result_box[0].strip()