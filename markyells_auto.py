#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Thin launcher (no Tk/CTk loaded unless fallback needed)
  Primary : PySide6 Qt  → markyells_qt.py
  Fallback: CustomTkinter → markyells_ctk_legacy.py (only if PySide6 missing)

Run:
    python markyells_auto.py
"""

from __future__ import annotations


def main() -> None:
    import sys
    import traceback

    try:
        from markyells_qt import run_qt

        print("[MARKYELLS] Backend: PySide6 Qt (luxury GUI)", flush=True)
        run_qt()
    except ImportError as exc:
        print(f"[MARKYELLS] Qt unavailable ({exc})", flush=True)
        print("[MARKYELLS] Backend: CustomTkinter LEGACY fallback", flush=True)
        try:
            from markyells_ctk_legacy import run

            run()
            sys.exit(0)
        except Exception:
            traceback.print_exc()
            sys.exit(1)
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()