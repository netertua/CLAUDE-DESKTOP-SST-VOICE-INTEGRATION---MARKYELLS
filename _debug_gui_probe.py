#!/usr/bin/env python3
"""Probe: open GUI 3s, close, report fallback/traceback."""
import sys
import traceback

FALLBACK_MARKERS = (
    "CustomTkinter LEGACY",
    "BACKEND_TRACE: CustomTkinter_FALLBACK",
    "Qt unavailable",
)
TRACEBACK_MARKERS = ("Traceback (most recent call last)", "Error:", "Exception:")


def main() -> int:
    lines: list[str] = []
    rc = 0
    try:
        import markyells_qt
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from settings_auto import AutoSettings
        from runtime_autodetect import apply_engine_override, detect_runtime

        def _safe_close(self, event) -> None:
            event.accept()

        markyells_qt.MarkyellsQtWindow.closeEvent = _safe_close

        def _probe_run_qt() -> None:
            app = QApplication.instance() or QApplication(sys.argv)
            s = AutoSettings.load()
            p = apply_engine_override(detect_runtime(), s.speech_engine_override)
            w = markyells_qt.MarkyellsQtWindow(s, p)
            w.show()
            lines.append("GUI_OPEN: OK")
            QTimer.singleShot(2500, w.close)
            QTimer.singleShot(2700, app.quit)
            app.exec()
            lines.append("GUI_CLOSE: OK")

        markyells_qt.run_qt = _probe_run_qt
        import markyells_auto

        lines.append("CALLING: markyells_auto.main()")
        markyells_auto.main()
        lines.append(f"CTK_LOADED: {'customtkinter' in sys.modules}")
        lines.append(f"TK_LOADED: {'tkinter' in sys.modules}")
        lines.append("MAIN_RETURN: OK")
    except Exception:
        lines.append("MAIN_RETURN: FAIL")
        lines.append(traceback.format_exc())
        rc = 1

    out = "\n".join(lines)
    print(out)
    text = out.lower()
    if any(m.lower() in text for m in FALLBACK_MARKERS):
        print("VERDICT: FALLBACK DETECTED")
        rc = 1
    elif "CTK_LOADED: True" in out:
        print("VERDICT: CTk loaded on Qt path")
        rc = 1
    elif any(m in out for m in TRACEBACK_MARKERS):
        print("VERDICT: TRACEBACK DETECTED")
        rc = 1
    else:
        print("VERDICT: CLEAN — PySide6 Qt, no fallback, no traceback")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())