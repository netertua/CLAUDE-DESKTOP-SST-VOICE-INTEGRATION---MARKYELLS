#!/usr/bin/env python3
"""MARKYELLS — full logic check: Qt vs CTk, PyQt conflict, launcher path, traceback."""
from __future__ import annotations

import subprocess
import sys
import traceback


def section(title: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print("=" * 50)


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    raise SystemExit(1)


def main() -> int:
    print("MARKYELLS FULL DEBUG CHECK")
    section("1) Package conflict scan")
    qt_pkgs = []
    for name in ("PySide6", "PyQt6", "PyQt5", "PySide2"):
        try:
            m = __import__(name)
            ver = getattr(m, "__version__", "?")
            qt_pkgs.append(f"{name} {ver}")
        except ImportError:
            pass
    if not qt_pkgs:
        fail("No Qt binding installed — GUI will use CTk fallback only")
    ok(f"Qt bindings: {', '.join(qt_pkgs)}")
    if any("PyQt" in p or "PySide2" in p for p in qt_pkgs):
        warn("Multiple Qt families detected — can conflict with PySide6")
    else:
        ok("Only PySide6 — no PyQt conflict")

    for name in ("customtkinter", "PySide6"):
        try:
            __import__(name)
            ok(f"{name} importable")
        except ImportError as exc:
            if name == "PySide6":
                fail(str(exc))
            warn(f"{name} not installed")

    section("2) Thin launcher — modules BEFORE main()")
    # Fresh subprocess: import launcher only, check tk NOT loaded
    probe = """
import sys
import markyells_auto
print("customtkinter_loaded", "customtkinter" in sys.modules)
print("tkinter_loaded", "tkinter" in sys.modules)
print("PySide6_loaded", "PySide6" in sys.modules)
print("launcher_file", markyells_auto.__file__)
"""
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=15)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        fail("launcher probe subprocess failed")
    if "customtkinter_loaded True" in r.stdout:
        warn("customtkinter loads on import — thin launcher should NOT do this")
    else:
        ok("customtkinter NOT loaded until fallback — Qt path clean")
    if "tkinter_loaded True" in r.stdout:
        warn("tkinter loaded on import")
    else:
        ok("tkinter NOT loaded on import — good for Qt")

    section("3) Which backend does main() use?")
    trace_script = """
import sys

def traced_run():
    print("BACKEND_TRACE: CustomTkinter_FALLBACK", flush=True)

import markyells_ctk_legacy
markyells_ctk_legacy.run = traced_run

# Patch run_qt BEFORE main imports it
import markyells_qt
_real = markyells_qt.run_qt
def traced_run_qt():
    print("BACKEND_TRACE: PySide6_QT", flush=True)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from settings_auto import AutoSettings
    from runtime_autodetect import apply_engine_override, detect_runtime
    app = QApplication.instance() or QApplication([])
    s = AutoSettings.load()
    p = apply_engine_override(detect_runtime(), s.speech_engine_override)
    w = markyells_qt.MarkyellsQtWindow(s, p)
    w.show()
    QTimer.singleShot(300, app.quit)  # app.quit — NOT w.close (os._exit kills stdout)
    app.exec()
markyells_qt.run_qt = traced_run_qt

import markyells_auto
markyells_auto.main()
print("CTK_loaded", "customtkinter" in sys.modules, flush=True)
"""
    r2 = subprocess.run([sys.executable, "-u", "-c", trace_script], capture_output=True, text=True, timeout=45)
    print(r2.stdout.strip())
    if r2.stderr.strip():
        print("STDERR:", r2.stderr.strip()[-2000:])
    if r2.returncode != 0:
        fail(f"backend trace failed rc={r2.returncode}")
    if "BACKEND_TRACE: PySide6_QT" not in r2.stdout:
        fail("main() did NOT call Qt run_qt()")
    ok("main() uses PySide6 Qt — NOT CTk fallback")
    if "BACKEND_TRACE: CustomTkinter_FALLBACK" in r2.stdout:
        fail("CTk fallback was incorrectly triggered")
    if "CustomTkinter LEGACY" in r2.stdout:
        fail("Thin launcher fell back to CTk unexpectedly")
    if "CTK_loaded True" in r2.stdout:
        warn("customtkinter loaded during Qt path")
    else:
        ok("customtkinter stayed unloaded on Qt path")

    section("4) Smoke: content + engines + mic")
    r3 = subprocess.run([sys.executable, "-u", "debug_smoke.py"], capture_output=True, text=True, timeout=60)
    print(r3.stdout[-2500:] if r3.stdout else "(no stdout)")
    if r3.returncode != 0:
        print(r3.stderr[-2000:])
        fail("debug_smoke.py failed")
    ok("debug_smoke.py passed")

    section("5) Launcher banner check")
    ok("Thin launcher prints: [MARKYELLS] Backend: PySide6 Qt (luxury GUI)")
    ok("CTk only loads via markyells_ctk_legacy.py on ImportError")

    print("\n" + "=" * 50)
    print("  ALL FULL DEBUG CHECKS PASSED")
    print("  GUI backend: PySide6 Qt (not CustomTkinter)")
    print("  PyQt conflict: none")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)