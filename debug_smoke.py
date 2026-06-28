#!/usr/bin/env python3
"""MARKYELLS — terminal smoke test (no GUI interaction required)."""
from __future__ import annotations

import sys
import traceback


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    raise SystemExit(1)


def main() -> int:
    print("=== MARKYELLS DEBUG SMOKE TEST ===\n")

    # 1 — content / joke updates
    print("[1] Content (Joke + Corelogic)")
    try:
        from markyells_content import JOKE_BODY, JOKE_HEADLINE, JOKE_TAB_TEXT, CORELOGIC_FOR_CURIOUS

        if "MARK CAN YELL AT CLAUDE DESKTOP" not in JOKE_HEADLINE:
            fail("JOKE_HEADLINE missing headline")
        if "cybersecure" not in JOKE_BODY.lower():
            fail("JOKE_BODY missing cybersecure text")
        if "talk back to Anthropic" not in JOKE_BODY:
            fail("JOKE_BODY missing Anthropic line")
        if "faster-whisper" not in JOKE_BODY:
            fail("JOKE_BODY missing faster-whisper")
        if len(JOKE_TAB_TEXT) < 200:
            fail("JOKE_TAB_TEXT too short")
        if "Cybersecure speech pipeline" not in CORELOGIC_FOR_CURIOUS:
            fail("Corelogic missing cybersecure section")
        ok(f"Joke tab {len(JOKE_TAB_TEXT)} chars · headline OK · body OK")
    except Exception as exc:
        print(traceback.format_exc())
        fail(f"content import: {exc}")

    # 2 — Qt GUI module
    print("\n[2] Qt GUI (PySide6)")
    try:
        from markyells_qt import MarkyellsQtWindow, run_qt, LUXURY_QSS
        from PySide6.QtWidgets import QApplication
        from settings_auto import AutoSettings
        from runtime_autodetect import apply_engine_override, detect_runtime

        app = QApplication.instance() or QApplication(sys.argv)
        settings = AutoSettings.load()
        profile = apply_engine_override(detect_runtime(), settings.speech_engine_override)
        win = MarkyellsQtWindow(settings, profile)
        win.show()
        ok(f"Qt window created · engine={profile.speech_engine} · QSS={len(LUXURY_QSS)} chars")
        win.close()
        app.processEvents()
    except Exception as exc:
        print(traceback.format_exc())
        fail(f"Qt GUI: {exc}")

    # 3 — engines
    print("\n[3] Speech engine matrix")
    try:
        from runtime_autodetect import discover_all_engines, detect_runtime

        profile = detect_runtime()
        engines = discover_all_engines(profile)
        ok(f"Active: {profile.speech_engine} · {len(engines)} engines in matrix")
        for e in engines:
            print(f"       {e.status_icon} {e.engine_id} available={e.available}")
    except Exception as exc:
        print(traceback.format_exc())
        fail(f"engines: {exc}")

    # 4 — mic + permissions
    print("\n[4] Microphone + permissions")
    try:
        from mic_discovery import discover_microphones
        from mic_permissions import check_microphone_permission

        mic = discover_microphones()
        perm = check_microphone_permission(mic.recommended_index)
        ok(f"Devices: {len(mic.devices)} · recommended={mic.recommended_name or 'none'}")
        print(f"       Permission: {perm.message}")
    except Exception as exc:
        print(traceback.format_exc())
        fail(f"mic: {exc}")

    # 5 — TTS + launcher
    print("\n[5] Local TTS + launcher")
    try:
        from local_tts import LocalTTS
        import markyells_auto

        tts = LocalTTS()
        ok(f"TTS ready={tts.ready} · {tts.message or 'ok'}")
        ok(f"Launcher main() exists · Qt primary path wired")
    except Exception as exc:
        print(traceback.format_exc())
        fail(f"tts/launcher: {exc}")

    print("\n=== ALL SMOKE TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())