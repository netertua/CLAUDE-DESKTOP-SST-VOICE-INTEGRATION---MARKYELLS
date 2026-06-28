#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Private Gift Edition (universal launcher)
Developed by Capt Can Yapıcı · ASPERA.BOND
NOT open source. A personal gift for Mark.

Platforms (auto-detect):
  · Apple Silicon Mac  → MLX + mlx-whisper (Thai + English)
  · Intel Mac (2011+)  → faster-whisper CPU
  · Windows AMD/Intel  → faster-whisper CPU

Run:
    python markyells_auto.py
"""

from __future__ import annotations

import threading
from pathlib import Path

import customtkinter as ctk

from markyells_content import (
    BACKSTORY_TEXT,
    CORELOGIC_FOR_CURIOUS,
    JOKE_BODY,
    JOKE_HEADLINE,
    JOKE_SUBTITLE,
    LICENSE_TEXT,
)
from mic_discovery import MicAnalysis, discover_microphones, get_mic_by_index
from reckon_shortcut import PressToTalkController, ReckonShortcutController
from runtime_autodetect import (
    AutoSpeechEngine,
    RuntimeProfile,
    apply_engine_override,
    detect_runtime,
    discover_all_engines,
)
from settings_auto import CONFIG_DIR, SETTINGS_FILE, AutoSettings

BASE_DIR = Path(__file__).resolve().parent

KEY_OPTIONS = ["f8", "f9", "f10", "ctrl", "shift", "alt", "space", "caps lock"]
SHORTCUT_ON_TIP = (
    "Reckon Shortcut ON: Hold your key(s) while speaking. "
    "Release to transcribe and auto-paste at your cursor — Cursor, browser, anywhere."
)
SHORTCUT_OFF_TIP = (
    "Reckon Shortcut OFF: Use the mic button. "
    "Hold = Press-to-Talk (WhatsApp-style). Or set Tap-to-toggle in Settings — "
    "tap once to listen, tap again to stop, then auto-paste."
)
PTT_HOLD_TIP = "Hold this button while speaking. Release to transcribe and paste."
PTT_TOGGLE_TIP = "Tap once to start listening. Tap again to stop and paste."

BTN_PRIMARY = {
    "height": 52,
    "corner_radius": 12,
    "font": None,
    "fg_color": "#b91c3c",
    "hover_color": "#991b1b",
    "border_width": 2,
    "border_color": "#fb7185",
    "text_color": "#ffffff",
}
BTN_SECONDARY = {
    "height": 52,
    "corner_radius": 12,
    "font": None,
    "fg_color": "#2a2a3d",
    "hover_color": "#3b3b55",
    "border_width": 2,
    "border_color": "#6366f1",
    "text_color": "#e8e8f0",
}
BTN_GHOST = {
    "height": 44,
    "corner_radius": 10,
    "font": None,
    "fg_color": "#1a1a24",
    "hover_color": "#2a2a38",
    "border_width": 1,
    "border_color": "#4b4b60",
    "text_color": "#d0d0dc",
}

ENGINE_NOTE = (
    "Local engines: mlx-whisper (Apple Silicon · MLX)  ·  "
    "faster-whisper (Windows & Mac fallback)  ·  "
    "Apple Speech Framework (macOS built-in · desktop & laptop)"
)


def _widget_alive(widget) -> bool:
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False


def _patch_ctk_tracker_loops() -> None:
    """Prevent CTk scaling/appearance loops from touching destroyed roots."""
    try:
        from customtkinter.windows.widgets.appearance_mode.appearance_mode_tracker import (
            AppearanceModeTracker,
        )
        from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

        if getattr(ScalingTracker, "_markyells_patched", False):
            return

        _orig_scaling = ScalingTracker.check_dpi_scaling.__func__  # type: ignore[attr-defined]
        _orig_appearance = AppearanceModeTracker.update.__func__  # type: ignore[attr-defined]

        def _safe_scaling(cls) -> None:
            for window in list(cls.window_widgets_dict):
                try:
                    if not window.winfo_exists():
                        cls.window_widgets_dict.pop(window, None)
                        cls.window_dpi_scaling_dict.pop(window, None)
                except Exception:
                    cls.window_widgets_dict.pop(window, None)
                    cls.window_dpi_scaling_dict.pop(window, None)
            if not cls.window_widgets_dict:
                cls.update_loop_running = False
                return
            _orig_scaling(cls)

        def _safe_appearance(cls) -> None:
            cls.app_list = [app for app in cls.app_list if _widget_alive(app)]
            if not cls.app_list:
                cls.update_loop_running = False
                return
            _orig_appearance(cls)

        ScalingTracker.check_dpi_scaling = classmethod(_safe_scaling)  # type: ignore[method-assign]
        AppearanceModeTracker.update = classmethod(_safe_appearance)  # type: ignore[method-assign]
        ScalingTracker._markyells_patched = True
    except Exception:
        pass


def _detach_ctk_trackers(window) -> None:
    try:
        from customtkinter.windows.widgets.appearance_mode.appearance_mode_tracker import (
            AppearanceModeTracker,
        )
        from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

        ScalingTracker.window_widgets_dict.pop(window, None)
        ScalingTracker.window_dpi_scaling_dict.pop(window, None)
        if not ScalingTracker.window_widgets_dict:
            ScalingTracker.update_loop_running = False
        try:
            AppearanceModeTracker.app_list.remove(window)
        except ValueError:
            pass
        if not AppearanceModeTracker.app_list:
            AppearanceModeTracker.update_loop_running = False
    except Exception:
        pass


def _cancel_all_after(widget) -> None:
    """Cancel CTk/Tk internal timers (update, check_dpi_scaling) before close."""
    if not _widget_alive(widget):
        return
    for _ in range(6):
        try:
            jobs = list(widget.tk.call("after", "info"))
        except Exception:
            break
        if not jobs:
            break
        for job in jobs:
            try:
                widget.after_cancel(job)
            except Exception:
                pass
    try:
        for child in widget.winfo_children():
            _cancel_all_after(child)
    except Exception:
        pass


def _shutdown_ctk_window(widget) -> None:
    """Fully tear down a CTk root — avoids Tcl 'invalid command name update' on exit."""
    if not _widget_alive(widget):
        return
    _detach_ctk_trackers(widget)
    _cancel_all_after(widget)
    try:
        widget.withdraw()
        widget.update_idletasks()
    except Exception:
        pass
    _cancel_all_after(widget)
    try:
        widget.quit()
    except Exception:
        pass
    try:
        if _widget_alive(widget):
            widget.destroy()
    except Exception:
        pass
    _detach_ctk_trackers(widget)


def _request_ctk_shutdown(widget) -> None:
    """Defer destroy one tick — never tear down inside an after/button callback.

    NOTE: after_idle never fires while CTk scaling/appearance loops keep scheduling
    after(100ms) jobs, so we must use after(0) instead.
    """
    if not _widget_alive(widget):
        return
    _detach_ctk_trackers(widget)
    try:
        widget.withdraw()
    except Exception:
        pass

    def _deferred() -> None:
        _shutdown_ctk_window(widget)

    try:
        widget.after(0, _deferred)

        def _watchdog() -> None:
            if _widget_alive(widget):
                _shutdown_ctk_window(widget)

        widget.after(250, _watchdog)
    except Exception:
        _shutdown_ctk_window(widget)


def _safe_destroy(widget) -> None:
    _shutdown_ctk_window(widget)


def _unhook_keyboard_async(timeout: float = 0.4) -> None:
    """keyboard.unhook_all() can block on Windows — never stall GUI close."""
    done = threading.Event()

    def _worker() -> None:
        try:
            import keyboard

            keyboard.unhook_all()
        except Exception:
            pass
        finally:
            done.set()

    threading.Thread(target=_worker, daemon=True).start()
    done.wait(timeout=timeout)


def _hard_exit(code: int = 0) -> None:
    import os

    os._exit(code)


class HoverTip:
    """Simple English hover explanation."""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip: ctk.CTkToplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.tip or not _widget_alive(self.widget):
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = ctk.CTkToplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.configure(fg_color="#1a1a1a")
        ctk.CTkLabel(
            self.tip,
            text=self.text,
            font=ctk.CTkFont(size=12),
            text_color="#d8d8d8",
            wraplength=360,
            justify="left",
            padx=10,
            pady=8,
        ).pack()

    def _hide(self, _event=None) -> None:
        if self.tip:
            self.tip.destroy()
            self.tip = None


def _btn_font(size: int = 15) -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight="bold")


class LicensePopup(ctk.CTkToplevel):
    """License popup — warning screen only."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("License Information")
        self.geometry("580x440")
        self.configure(fg_color="#0a0a0a")
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._close)

        frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=16)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame,
            text="LICENSE INFORMATION",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ff6b6b",
        ).pack(anchor="w", padx=20, pady=(20, 12))

        ctk.CTkLabel(
            frame,
            text=LICENSE_TEXT,
            font=ctk.CTkFont(size=13),
            text_color="#d0d0d0",
            justify="left",
            wraplength=500,
        ).pack(anchor="w", padx=20, pady=(0, 20))

        ctk.CTkButton(
            frame,
            text="I Understand",
            width=180,
            font=_btn_font(14),
            command=self._close,
            **{k: v for k, v in BTN_GHOST.items() if k != "font"},
        ).pack(pady=(0, 20))

        self.after(100, self.grab_set)

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class WarningSplash(ctk.CTk):
    def __init__(self, duration_seconds: int = 10):
        super().__init__()
        self.duration_seconds = max(1, duration_seconds)
        self.dont_show_again_result = False
        self._seconds_left = self.duration_seconds
        self._skip_requested = False
        self._dont_show_again = False
        self._timer_job: str | None = None

        self.title("MARKYELLS AUTO — Warning")
        self.geometry("720x520")
        self.minsize(640, 460)
        self.configure(fg_color="#050505")
        self._build_ui()
        self._tick()
        self.protocol("WM_DELETE_WINDOW", self._skip)

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=18)
        container.pack(fill="both", expand=True, padx=24, pady=24)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text="⚠  PRIVATE GIFT EDITION  ·  NOT OPEN SOURCE",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ff4d4d",
            fg_color="#1a0000",
            corner_radius=10,
            padx=16,
            pady=6,
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="License Information",
            width=160,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1a1a1a",
            hover_color="#2a2a2a",
            border_width=1,
            border_color="#ff4d4d",
            text_color="#ff6b6b",
            command=lambda: LicensePopup(self),
        ).pack(side="right")

        tabview = ctk.CTkTabview(
            container,
            fg_color="#0f0f0f",
            segmented_button_fg_color="#1a1a1a",
            segmented_button_selected_color="#2a1515",
            segmented_button_unselected_color="#141414",
            text_color="#e0e0e0",
        )
        tabview.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        joke_scroll = ctk.CTkScrollableFrame(
            tabview.add("The Joke"), fg_color="#0a0a0a", corner_radius=12
        )
        joke_scroll.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(
            joke_scroll,
            text=JOKE_HEADLINE,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ff4d4d",
            justify="center",
            wraplength=620,
        ).pack(pady=(20, 8))
        ctk.CTkLabel(
            joke_scroll,
            text=JOKE_SUBTITLE,
            font=ctk.CTkFont(size=12),
            text_color="#888888",
            wraplength=620,
        ).pack(pady=(0, 12))
        ctk.CTkLabel(
            joke_scroll,
            text=JOKE_BODY,
            font=ctk.CTkFont(size=14),
            text_color="#c8c8c8",
            justify="left",
            wraplength=620,
        ).pack(pady=(0, 20))

        self._build_scroll_tab(tabview.add("Backstory for Curious"), "Backstory for Curious", BACKSTORY_TEXT)
        self._build_scroll_tab(tabview.add("Corelogic for Curious"), "Corelogic for Curious", CORELOGIC_FOR_CURIOUS)
        self._build_scroll_tab(tabview.add("License Information"), "License Information", LICENSE_TEXT)
        tabview.set("The Joke")

        self.timer_label = ctk.CTkLabel(
            container,
            text=f"App opens in {self._seconds_left}s...",
            font=ctk.CTkFont(size=13),
            text_color="#7a7a7a",
        )
        self.timer_label.pack(anchor="w", padx=20, pady=(0, 10))

        self.progress = ctk.CTkProgressBar(
            container, width=740, height=8, fg_color="#1f1f1f", progress_color="#ff4d4d"
        )
        self.progress.pack(padx=20, pady=(0, 16))
        self.progress.set(0.0)

        bottom = ctk.CTkFrame(container, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 20))

        self.dont_show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            bottom,
            text="Don't show this again",
            variable=self.dont_show_var,
            fg_color="#ff4d4d",
            hover_color="#cc3d3d",
            command=lambda: setattr(self, "_dont_show_again", bool(self.dont_show_var.get())),
        ).pack(side="left")

        ctk.CTkButton(
            bottom,
            text="License",
            width=120,
            font=_btn_font(13),
            command=lambda: LicensePopup(self),
            **{k: v for k, v in BTN_GHOST.items() if k != "font"},
        ).pack(side="right", padx=(0, 8))

        ctk.CTkButton(
            bottom,
            text="Continue →",
            width=150,
            font=_btn_font(14),
            command=self._skip,
            **{k: v for k, v in BTN_PRIMARY.items() if k != "font"},
        ).pack(side="right")

    def _build_scroll_tab(self, parent: ctk.CTkFrame, title: str, body: str) -> None:
        scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color="#0a0a0a",
            corner_radius=12,
            scrollbar_button_color="#2a2a2a",
            scrollbar_button_hover_color="#3a3a3a",
        )
        scroll.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(
            scroll,
            text=title,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ff6b6b",
        ).pack(anchor="w", padx=20, pady=(20, 12))
        ctk.CTkLabel(
            scroll,
            text=body,
            font=ctk.CTkFont(size=14),
            text_color="#c8c8c8",
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=20, pady=(0, 24))

    def _cancel_timer(self) -> None:
        if self._timer_job:
            try:
                self.after_cancel(self._timer_job)
            except Exception:
                pass
            self._timer_job = None

    def _tick(self) -> None:
        if self._skip_requested or not _widget_alive(self):
            return
        elapsed = self.duration_seconds - self._seconds_left
        self.progress.set(elapsed / self.duration_seconds)
        self.timer_label.configure(text=f"App opens in {self._seconds_left}s...")
        if self._seconds_left <= 0:
            self._finish()
            return
        self._seconds_left -= 1
        self._timer_job = self.after(1000, self._tick)

    def _skip(self) -> None:
        if self._skip_requested:
            return
        self._skip_requested = True
        self._cancel_timer()
        self.dont_show_again_result = self._dont_show_again
        # Button / WM_DELETE — not an after-callback, destroy immediately.
        _shutdown_ctk_window(self)

    def _finish(self) -> None:
        self._cancel_timer()
        self._skip_requested = True
        self.dont_show_again_result = self._dont_show_again
        # Timer tick runs inside after() — must defer destroy one frame.
        _request_ctk_shutdown(self)


class MarkyellsAuto(ctk.CTk):
    def __init__(self, settings: AutoSettings, profile: RuntimeProfile):
        super().__init__()
        self.settings = settings
        self.profile = profile
        self.mic_analysis = discover_microphones()
        mic_idx = get_mic_by_index(settings.mic_device_index)
        self.engine = AutoSpeechEngine(
            profile, settings.record_seconds, mic_idx, settings.speech_language
        )
        self.shortcut_ctrl: ReckonShortcutController | None = None
        self.ptt_ctrl: PressToTalkController | None = None
        self._tip_shortcut: HoverTip | None = None
        self._tip_mic: HoverTip | None = None
        self._alive = True

        self.title("MARKYELLS — Private Gift for Mark")
        self.geometry("1000x760")
        self.minsize(900, 660)
        self.configure(fg_color="#0d0d0d")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self._build_ui()
        self._init_controllers()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)
        ctk.CTkLabel(
            top,
            text=f"MARKYELLS  ·  Private Gift  ·  {self.profile.backend_label}",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#f2f2f2",
        ).pack(side="left", padx=20)

        tabview = ctk.CTkTabview(
            self,
            fg_color="#111111",
            segmented_button_fg_color="#1a1a1a",
            segmented_button_selected_color="#2a2a2a",
            segmented_button_unselected_color="#141414",
            text_color="#e8e8e8",
        )
        tabview.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        self._build_speak_tab(tabview.add("Speak"))
        self._build_runtime_tab(tabview.add("Auto Detect"))
        self._build_mic_tab(tabview.add("Microphone"))
        self._build_settings_tab(tabview.add("Settings"))
        tabview.set("Speak")

    def _build_speak_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card,
            text="MARKYELLS 🎙",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#f5f5f5",
        ).pack(anchor="w", padx=24, pady=(24, 4))

        ctk.CTkLabel(
            card,
            text="A private gift for Mark · Thai + English · Not open source",
            font=ctk.CTkFont(size=13),
            text_color="#888888",
        ).pack(anchor="w", padx=24, pady=(0, 4))

        ctk.CTkLabel(
            card,
            text=ENGINE_NOTE,
            font=ctk.CTkFont(size=12),
            text_color="#6366f1",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 8))

        ctk.CTkLabel(
            card,
            text=self.profile.message,
            font=ctk.CTkFont(size=14),
            text_color="#9a9a9a",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 8))

        badge_color = "#4ade80" if self.profile.is_local else "#fbbf24"
        ctk.CTkLabel(
            card,
            text=self.profile.local_badge,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=badge_color,
            fg_color="#0f1a0f" if self.profile.is_local else "#1a1508",
            corner_radius=8,
            padx=12,
            pady=4,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        self.status_label = ctk.CTkLabel(
            card,
            text="Ready." if self.profile.ready else self.profile.message,
            font=ctk.CTkFont(size=13),
            text_color="#7dd3fc" if self.profile.ready else "#fbbf24",
        )
        self.status_label.pack(anchor="w", padx=24, pady=(0, 12))

        shortcut_row = ctk.CTkFrame(card, fg_color="transparent")
        shortcut_row.pack(fill="x", padx=24, pady=(0, 8))

        self.shortcut_var = ctk.BooleanVar(value=self.settings.reckon_shortcut_enabled)
        self.shortcut_chk = ctk.CTkCheckBox(
            shortcut_row,
            text="Reckon Shortcut (global hotkey)",
            variable=self.shortcut_var,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#ff4d4d",
            hover_color="#cc3d3d",
            command=self._on_shortcut_toggle,
        )
        self.shortcut_chk.pack(side="left")

        self.shortcut_hint = ctk.CTkLabel(
            shortcut_row,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
            wraplength=520,
            justify="left",
        )
        self.shortcut_hint.pack(side="left", padx=(12, 0))

        self.paste_var = ctk.BooleanVar(value=self.settings.auto_paste)
        ctk.CTkCheckBox(
            card,
            text="Automated Speech Reckon → Auto-Paste at cursor",
            variable=self.paste_var,
            font=ctk.CTkFont(size=13),
            fg_color="#4ade80",
            hover_color="#22c55e",
            command=self._save_and_reload_controllers,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        self.shortcut_status = ctk.CTkLabel(
            card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#7dd3fc",
        )
        self.shortcut_status.pack(anchor="w", padx=24, pady=(0, 12))

        lang_row = ctk.CTkFrame(card, fg_color="transparent")
        lang_row.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(lang_row, text="Speech language:", font=ctk.CTkFont(size=13), text_color="#aaaaaa").pack(side="left")
        self.lang_combo = ctk.CTkComboBox(
            lang_row,
            values=["auto", "en", "th"],
            width=160,
            command=self._on_language_change,
        )
        self.lang_combo.set(self.settings.speech_language)
        self.lang_combo.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            lang_row,
            text="auto = Thai+English · en = English · th = ภาษาไทย",
            font=ctk.CTkFont(size=11),
            text_color="#666666",
        ).pack(side="left", padx=(12, 0))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 16))

        ready = "normal" if self.profile.ready else "disabled"

        self.yell_btn = ctk.CTkButton(
            btn_row,
            text=f"RECORD  {self.settings.record_seconds}s",
            width=220,
            font=_btn_font(),
            state=ready,
            command=self._on_yell,
            **{k: v for k, v in BTN_SECONDARY.items() if k != "font"},
        )
        self.yell_btn.pack(side="left", padx=(0, 14))

        self.mic_btn = ctk.CTkButton(
            btn_row,
            text="HOLD TO TALK",
            width=220,
            font=_btn_font(),
            state=ready,
            **{k: v for k, v in BTN_PRIMARY.items() if k != "font"},
        )
        self.mic_btn.pack(side="left")
        self.mic_btn.bind("<ButtonPress-1>", self._on_mic_press)
        self.mic_btn.bind("<ButtonRelease-1>", self._on_mic_release)

        self._refresh_shortcut_ui()

        self.transcript = ctk.CTkTextbox(
            card,
            height=280,
            font=ctk.CTkFont(size=15),
            fg_color="#0a0a0a",
            text_color="#e8e8e8",
            border_color="#2a2a2a",
            border_width=1,
            wrap="word",
        )
        self.transcript.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self.transcript.insert("1.0", "Transcript will appear here...\n")
        self.transcript.configure(state="disabled")

    def _build_runtime_tab(self, parent: ctk.CTkFrame) -> None:
        outer = ctk.CTkScrollableFrame(parent, fg_color="#141414", corner_radius=16)
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        color = "#4ade80" if self.profile.ready else "#fbbf24"
        ctk.CTkLabel(
            outer,
            text=f"{'●' if self.profile.ready else '○'} Auto-Detected Runtime",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=color,
        ).pack(anchor="w", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            outer,
            text="Active engine + full debug matrix below. MLX ≠ faster-whisper. macOS also has Apple Speech Framework.",
            font=ctk.CTkFont(size=12),
            text_color="#6366f1",
            wraplength=860,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        lines = [
            self.profile.message,
            self.profile.local_badge,
            f"Backend: {self.profile.backend}",
            f"Label: {self.profile.backend_label}",
            f"Speech engine: {self.profile.speech_engine}",
            f"Model: {self.profile.speech_model}",
            f"Override: {self.settings.speech_engine_override}",
            f"Local only: {'yes' if self.profile.is_local else 'no (online fallback)'}",
            f"Hardware: {self.profile.hardware.label}",
            f"CPU vendor: {self.profile.hardware.cpu_vendor}",
            f"Mac era: {self.profile.hardware.mac_era or '—'}",
            f"Processor: {self.profile.hardware.processor_raw}",
            *self.profile.details,
        ]
        for line in lines:
            ctk.CTkLabel(
                outer,
                text=line,
                font=ctk.CTkFont(size=13),
                text_color="#c8c8c8",
                wraplength=860,
                justify="left",
            ).pack(anchor="w", padx=24, pady=(0, 4))

        ctk.CTkLabel(
            outer,
            text="Speech Engine Debug Matrix",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f0f0f0",
        ).pack(anchor="w", padx=24, pady=(20, 8))

        self._engine_matrix_frame = ctk.CTkFrame(outer, fg_color="#0f0f0f", corner_radius=12)
        self._engine_matrix_frame.pack(fill="x", padx=24, pady=(0, 12))
        self._render_engine_matrix()

        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(anchor="w", padx=24, pady=(8, 24))
        ctk.CTkButton(
            btn_row,
            text="↻  Re-detect Runtime",
            width=180,
            fg_color="#1f1f1f",
            hover_color="#333333",
            border_width=1,
            border_color="#444444",
            command=self._redetect,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            btn_row,
            text="↻  Refresh Engine Matrix",
            width=200,
            fg_color="#1f1f1f",
            hover_color="#333333",
            border_width=1,
            border_color="#444444",
            command=self._render_engine_matrix,
        ).pack(side="left")

    def _render_engine_matrix(self) -> None:
        if not hasattr(self, "_engine_matrix_frame"):
            return
        for child in self._engine_matrix_frame.winfo_children():
            child.destroy()

        engines = discover_all_engines(self.profile)
        for opt in engines:
            if opt.engine_id == "windows_local_note":
                row_color = "#555555"
            elif opt.available:
                row_color = "#4ade80"
            elif opt.status_icon == "◐":
                row_color = "#fbbf24"
            else:
                row_color = "#888888"

            block = ctk.CTkFrame(self._engine_matrix_frame, fg_color="#141414", corner_radius=8)
            block.pack(fill="x", padx=10, pady=6)

            header = (
                f"{opt.status_icon}  {opt.name}"
                + ("  ★ ACTIVE" if opt.is_recommended else "")
            )
            ctk.CTkLabel(
                block,
                text=header,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=row_color,
                wraplength=780,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(10, 2))

            ctk.CTkLabel(
                block,
                text=f"{opt.platform_hint}  ·  {'local' if opt.is_local else 'online'}",
                font=ctk.CTkFont(size=11),
                text_color="#888888",
                wraplength=780,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 2))

            ctk.CTkLabel(
                block,
                text=opt.summary,
                font=ctk.CTkFont(size=12),
                text_color="#c8c8c8",
                wraplength=780,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 4))

            for detail in opt.details:
                ctk.CTkLabel(
                    block,
                    text=f"  · {detail}",
                    font=ctk.CTkFont(size=11),
                    text_color="#9a9a9a",
                    wraplength=760,
                    justify="left",
                ).pack(anchor="w", padx=12, pady=(0, 2))

            if opt.engine_id not in {"windows_local_note"} and opt.available:
                ctk.CTkButton(
                    block,
                    text="Use this engine",
                    width=140,
                    height=30,
                    fg_color="#2a2a3d",
                    hover_color="#3b3b55",
                    border_width=1,
                    border_color="#6366f1",
                    command=lambda eid=opt.engine_id: self._select_engine(eid),
                ).pack(anchor="w", padx=12, pady=(4, 10))
            else:
                ctk.CTkLabel(block, text="", height=6).pack()

    def _build_mic_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card,
            text="Microphone Analyzer",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f0f0f0",
        ).pack(anchor="w", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            card,
            text=self.mic_analysis.message,
            font=ctk.CTkFont(size=13),
            text_color="#9a9a9a",
            wraplength=860,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        mic_names = [d.label for d in self.mic_analysis.devices] or ["No mic found"]
        self.mic_combo = ctk.CTkComboBox(
            card,
            values=mic_names,
            width=500,
            command=self._on_mic_selected,
        )
        self.mic_combo.pack(anchor="w", padx=24, pady=(0, 12))
        if self.mic_analysis.devices:
            for i, d in enumerate(self.mic_analysis.devices):
                if d.index == get_mic_by_index(self.settings.mic_device_index):
                    self.mic_combo.set(d.label)
                    break

        ctk.CTkButton(
            card,
            text="↻  Rescan Microphones",
            width=200,
            fg_color="#1f1f1f",
            hover_color="#333333",
            border_width=1,
            border_color="#444444",
            command=self._rescan_mics,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        scroll = ctk.CTkScrollableFrame(card, fg_color="#0f0f0f", corner_radius=12, height=300)
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        for dev in self.mic_analysis.devices:
            ctk.CTkLabel(
                scroll,
                text=(
                    f"#{dev.index}  {dev.name}\n"
                    f"    API: {dev.host_api} · {dev.channels}ch · {int(dev.sample_rate)}Hz · score {dev.score}"
                ),
                font=ctk.CTkFont(size=12),
                text_color="#c8c8c8",
                justify="left",
            ).pack(anchor="w", padx=12, pady=4)

    def _build_settings_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkScrollableFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card, text="Settings", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f0f0f0"
        ).pack(anchor="w", padx=24, pady=(24, 16))

        ctk.CTkLabel(
            card,
            text="Speech engine (override autodetect)",
            text_color="#aaaaaa",
        ).pack(anchor="w", padx=24, pady=(0, 4))
        self.engine_combo = ctk.CTkComboBox(
            card,
            values=["auto", "faster_whisper", "mlx_whisper", "apple_speech", "speech_recognition"],
            width=280,
            command=self._on_engine_override_change,
        )
        self.engine_combo.set(self.settings.speech_engine_override)
        self.engine_combo.pack(anchor="w", padx=24, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="auto = hardware pick · See Auto Detect tab for full engine matrix",
            font=ctk.CTkFont(size=11),
            text_color="#666666",
        ).pack(anchor="w", padx=24, pady=(0, 16))

        self.warning_var = ctk.BooleanVar(value=self.settings.show_warning_on_startup)
        ctk.CTkCheckBox(
            card,
            text="Show warning screen on startup",
            variable=self.warning_var,
            fg_color="#ff4d4d",
            hover_color="#cc3d3d",
            command=self._save_settings,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        ctk.CTkLabel(card, text="Shortcut mode", text_color="#aaaaaa").pack(anchor="w", padx=24, pady=(8, 4))
        self.mode_combo = ctk.CTkComboBox(
            card,
            values=["single", "combined"],
            width=200,
            command=self._on_mode_change,
        )
        self.mode_combo.set(self.settings.shortcut_mode)
        self.mode_combo.pack(anchor="w", padx=24, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="single = ONE key hold · combined = TWO keys together",
            font=ctk.CTkFont(size=11),
            text_color="#666666",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(key_row, text="Key 1:", text_color="#aaaaaa").pack(side="left")
        self.key1_combo = ctk.CTkComboBox(key_row, values=KEY_OPTIONS, width=120, command=lambda _v: self._save_and_reload_controllers())
        self.key1_combo.set(self.settings.shortcut_key1)
        self.key1_combo.pack(side="left", padx=(8, 20))
        ctk.CTkLabel(key_row, text="Key 2:", text_color="#aaaaaa").pack(side="left")
        self.key2_combo = ctk.CTkComboBox(key_row, values=KEY_OPTIONS, width=120, command=lambda _v: self._save_and_reload_controllers())
        self.key2_combo.set(self.settings.shortcut_key2)
        self.key2_combo.pack(side="left", padx=8)

        ctk.CTkLabel(card, text="Mic button mode (when shortcut OFF)", text_color="#aaaaaa").pack(
            anchor="w", padx=24, pady=(8, 4)
        )
        self.ptt_combo = ctk.CTkComboBox(
            card,
            values=["hold", "toggle"],
            width=200,
            command=self._on_ptt_mode_change,
        )
        self.ptt_combo.set(self.settings.ptt_mode)
        self.ptt_combo.pack(anchor="w", padx=24, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="hold = Press-to-Talk · toggle = tap start / tap stop (WhatsApp-style)",
            font=ctk.CTkFont(size=11),
            text_color="#666666",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        self.record_slider = ctk.CTkSlider(
            card, from_=3, to=15, number_of_steps=12, command=self._on_record_change
        )
        self.record_slider.set(self.settings.record_seconds)
        self.record_slider.pack(fill="x", padx=24, pady=(12, 4))
        self.record_label = ctk.CTkLabel(
            card, text=f"Fixed record duration: {self.settings.record_seconds}s", text_color="#888888"
        )
        self.record_label.pack(anchor="w", padx=24, pady=(0, 16))

        ctk.CTkButton(
            card,
            text="Show Warning Screen",
            width=240,
            font=_btn_font(14),
            command=self._preview_warning,
            **{k: v for k, v in BTN_GHOST.items() if k != "font"},
        ).pack(anchor="w", padx=24, pady=(0, 24))

    def _schedule_ui(self, fn) -> None:
        if not self._alive:
            return
        self.after(0, lambda: self._run_ui(fn))

    def _run_ui(self, fn) -> None:
        if not self._alive or not _widget_alive(self):
            return
        try:
            fn()
        except Exception:
            pass

    def _set_status(self, msg: str) -> None:
        self._schedule_ui(lambda: self.status_label.configure(text=msg))

    def _init_controllers(self) -> None:
        if self.shortcut_ctrl:
            self.shortcut_ctrl.stop()
        self.shortcut_ctrl = ReckonShortcutController(
            engine=self.engine,
            key1=self.settings.shortcut_key1,
            key2=self.settings.shortcut_key2,
            mode=self.settings.shortcut_mode,
            enabled=self.settings.reckon_shortcut_enabled and self.profile.ready,
            auto_paste=self.settings.auto_paste,
            mic_index=get_mic_by_index(self.settings.mic_device_index),
            on_status=self._set_status,
            on_transcript=lambda t: self._schedule_ui(lambda: self._show_transcript(t)),
            on_error=lambda e: self._set_status(f"Error: {e}"),
        )
        self.shortcut_ctrl.start()

        self.ptt_ctrl = PressToTalkController(
            engine=self.engine,
            mode=self.settings.ptt_mode,
            auto_paste=self.settings.auto_paste,
            mic_index=get_mic_by_index(self.settings.mic_device_index),
            on_status=self._set_status,
            on_transcript=lambda t: self._schedule_ui(lambda: self._show_transcript(t)),
            on_error=lambda e: self._set_status(f"Error: {e}"),
        )
        self._refresh_shortcut_ui()

    def _show_transcript(self, text: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.insert("1.0", text or "(silence...)")
        self.transcript.configure(state="disabled")

    def _refresh_shortcut_ui(self) -> None:
        enabled = bool(self.shortcut_var.get())
        tip = SHORTCUT_ON_TIP if enabled else SHORTCUT_OFF_TIP
        self.shortcut_hint.configure(text=tip[:80] + "…" if len(tip) > 80 else tip)

        if self._tip_shortcut:
            self._tip_shortcut.text = tip
        else:
            self._tip_shortcut = HoverTip(self.shortcut_chk, tip)

        mic_tip = PTT_TOGGLE_TIP if self.settings.ptt_mode == "toggle" else PTT_HOLD_TIP
        if enabled:
            mic_tip += " (disabled while shortcut is ON)"
        if self._tip_mic:
            self._tip_mic.text = mic_tip
        else:
            self._tip_mic = HoverTip(self.mic_btn, mic_tip)

        if self.shortcut_ctrl:
            label = self.shortcut_ctrl.shortcut_label if enabled else "Shortcut OFF — use mic button"
            self.shortcut_status.configure(text=label)

        mic_label = "TAP TO TOGGLE" if self.settings.ptt_mode == "toggle" else "HOLD TO TALK"
        self.mic_btn.configure(
            text=mic_label,
            state="disabled" if (enabled or not self.profile.ready) else "normal",
        )

    def _on_shortcut_toggle(self) -> None:
        self.settings.reckon_shortcut_enabled = bool(self.shortcut_var.get())
        self._save_and_reload_controllers()

    def _on_mode_change(self, value: str) -> None:
        self.settings.shortcut_mode = value
        self._save_and_reload_controllers()

    def _on_language_change(self, value: str) -> None:
        self.settings.speech_language = value
        self.engine.language = value
        self._save_settings()

    def _on_ptt_mode_change(self, value: str) -> None:
        self.settings.ptt_mode = value
        if self.ptt_ctrl:
            self.ptt_ctrl.mode = value
        self._refresh_shortcut_ui()
        self._save_settings()

    def _on_mic_selected(self, label: str) -> None:
        for d in self.mic_analysis.devices:
            if d.label == label:
                self.settings.mic_device_index = d.index
                self.engine.mic_device_index = d.index
                self._save_and_reload_controllers()
                break

    def _rescan_mics(self) -> None:
        self.mic_analysis = discover_microphones()
        self.settings.mic_device_index = self.mic_analysis.recommended_index
        self._save_and_reload_controllers()
        self.status_label.configure(text=self.mic_analysis.message)

    def _on_mic_press(self, _event=None) -> None:
        if self.settings.reckon_shortcut_enabled or not self.ptt_ctrl:
            return
        self.ptt_ctrl.mic_press()

    def _on_mic_release(self, _event=None) -> None:
        if self.settings.reckon_shortcut_enabled or not self.ptt_ctrl:
            return
        self.ptt_ctrl.mic_release()

    def _save_and_reload_controllers(self) -> None:
        self.settings.reckon_shortcut_enabled = bool(self.shortcut_var.get())
        self.settings.shortcut_key1 = self.key1_combo.get()
        self.settings.shortcut_key2 = self.key2_combo.get()
        self.settings.shortcut_mode = self.mode_combo.get()
        self.settings.auto_paste = bool(self.paste_var.get())
        self.settings.ptt_mode = self.ptt_combo.get()
        if hasattr(self, "lang_combo"):
            self.settings.speech_language = self.lang_combo.get()
            self.engine.language = self.settings.speech_language
        self.settings.save()
        self._init_controllers()

    def _on_record_change(self, value: float) -> None:
        self.settings.record_seconds = int(value)
        self.engine.record_seconds = self.settings.record_seconds
        self.record_label.configure(text=f"Fixed record duration: {self.settings.record_seconds}s")
        self.yell_btn.configure(text=f"RECORD  {self.settings.record_seconds}s")
        self._save_settings()

    def _save_settings(self) -> None:
        self.settings.show_warning_on_startup = bool(self.warning_var.get())
        self.settings.save()

    def _preview_warning(self) -> None:
        splash = WarningSplash(duration_seconds=self.settings.warning_duration_seconds)
        splash.grab_set()
        self.wait_window(splash)
        if splash.dont_show_again_result:
            self.settings.show_warning_on_startup = False
            self.settings.save()
            self.warning_var.set(False)
        _safe_destroy(splash)

    def _resolve_profile(self) -> RuntimeProfile:
        return apply_engine_override(detect_runtime(), self.settings.speech_engine_override)

    def _select_engine(self, engine_id: str) -> None:
        self.settings.speech_engine_override = engine_id
        if hasattr(self, "engine_combo"):
            self.engine_combo.set(engine_id)
        self.settings.save()
        self._redetect()

    def _on_engine_override_change(self, value: str) -> None:
        self.settings.speech_engine_override = value
        self.settings.save()
        self._redetect()

    def _redetect(self) -> None:
        self.profile = self._resolve_profile()
        mic_idx = get_mic_by_index(self.settings.mic_device_index)
        self.engine = AutoSpeechEngine(
            self.profile, self.settings.record_seconds, mic_idx, self.settings.speech_language
        )
        self._init_controllers()
        self.title(f"MARKYELLS — Private Gift · {self.profile.backend_label}")
        self._render_engine_matrix()
        ready = "normal" if self.profile.ready else "disabled"
        self.yell_btn.configure(state=ready)
        self._refresh_shortcut_ui()
        self.status_label.configure(
            text="Ready." if self.profile.ready else self.profile.message,
            text_color="#7dd3fc" if self.profile.ready else "#fbbf24",
        )

    def _on_close(self) -> None:
        self._alive = False
        try:
            if self.shortcut_ctrl:
                self.shortcut_ctrl.stop()
        except Exception:
            pass
        try:
            # WM_DELETE_WINDOW is not an after-callback — safe to destroy immediately.
            _shutdown_ctk_window(self)
        except Exception:
            pass
        _unhook_keyboard_async()
        _hard_exit(0)

    def _on_yell(self) -> None:
        self.yell_btn.configure(state="disabled")

        def done(text: str) -> None:
            def ui() -> None:
                self._show_transcript(text)
                self.status_label.configure(text="Done.")
                if self.settings.auto_paste and text:
                    from reckon_shortcut import paste_to_active_window
                    paste_to_active_window(text)
                    self.status_label.configure(text="Pasted to cursor.")
                self.yell_btn.configure(state="normal")

            self._schedule_ui(ui)

        def error(msg: str) -> None:
            self._schedule_ui(
                lambda: (
                    self.status_label.configure(text=f"Error: {msg}"),
                    self.yell_btn.configure(state="normal"),
                )
            )

        self.engine.record_and_transcribe(self._set_status, done, error)


def run() -> None:
    _patch_ctk_tracker_loops()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    settings = AutoSettings.load()
    splash: WarningSplash | None = None

    if settings.show_warning_on_startup:
        splash = WarningSplash(duration_seconds=settings.warning_duration_seconds)
        splash.mainloop()
        dont_show = splash.dont_show_again_result
        _safe_destroy(splash)
        if dont_show:
            settings.show_warning_on_startup = False
            settings.save()

    profile = apply_engine_override(detect_runtime(), settings.speech_engine_override)
    app = MarkyellsAuto(settings, profile)
    app.mainloop()
    _safe_destroy(app)


def main() -> None:
    """Legacy CustomTkinter entry only."""
    try:
        run()
    except Exception:
        import traceback

        traceback.print_exc()
        _hard_exit(1)
    _hard_exit(0)


if __name__ == "__main__":
    main()