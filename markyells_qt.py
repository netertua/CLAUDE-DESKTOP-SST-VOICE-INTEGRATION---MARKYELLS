#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Luxury Qt GUI (primary launcher)
PySide6 · local speech · mic permissions · MLX matrix · local TTS
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from local_tts import LocalTTS
from markyells_content import (
    BACKSTORY_TEXT,
    CORELOGIC_FOR_CURIOUS,
    JOKE_TAB_TEXT,
    LICENSE_TEXT,
)
from mic_discovery import discover_microphones, get_mic_by_index
from mic_permissions import (
    MicPermissionStatus,
    check_microphone_permission,
    open_microphone_settings,
    save_test_wav,
)
from reckon_shortcut import PressToTalkController, ReckonShortcutController
from runtime_autodetect import (
    AutoSpeechEngine,
    RuntimeProfile,
    apply_engine_override,
    detect_runtime,
    discover_all_engines,
)
from settings_auto import AutoSettings

KEY_OPTIONS = ["f8", "f9", "f10", "ctrl", "shift", "alt", "space", "caps lock"]


def _unhook_keyboard_async(timeout: float = 0.4) -> None:
    """keyboard.unhook_all() can block on Windows — never stall Qt close."""
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

LUXURY_QSS = """
QMainWindow, QDialog { background-color: #08080c; }
QWidget { color: #e8e6e3; font-family: 'Segoe UI', 'SF Pro Display', sans-serif; font-size: 13px; }
QTabWidget::pane { border: 1px solid #2a2438; border-radius: 12px; background: #0e0e14; top: -1px; }
QTabBar::tab {
    background: #14141c; color: #9a97a8; padding: 12px 22px; margin-right: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; border: 1px solid #1f1f2a;
}
QTabBar::tab:selected { background: #1a1520; color: #f5d0d6; border-bottom: 2px solid #c41e3a; }
QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #8b1530, stop:1 #c41e3a);
    color: white; border: 1px solid #e8a0ad; border-radius: 12px; padding: 14px 24px; font-weight: 600;
}
QPushButton#primary:hover { background: #a61c3a; }
QPushButton#secondary {
    background: #1a1a28; color: #d8d6e8; border: 1px solid #4a4570; border-radius: 12px; padding: 12px 20px;
}
QPushButton#secondary:hover { border-color: #d4af37; color: #f0e6c8; }
QPushButton#gold {
    background: #1f1a12; color: #d4af37; border: 1px solid #d4af37; border-radius: 12px; padding: 12px 20px;
}
QPushButton#gold:hover { background: #2a2218; }
QTextEdit, QComboBox {
    background: #0a0a10; border: 1px solid #2a2a3d; border-radius: 10px; padding: 8px; color: #eceae6;
}
QComboBox::drop-down { border: none; }
QScrollArea { border: none; background: transparent; }
QFrame#card {
    background: #101018; border: 1px solid #2a2438; border-radius: 16px;
}
QLabel#headline { font-size: 26px; font-weight: 700; color: #f5f2ef; }
QLabel#subtitle { color: #8a8796; }
QLabel#badge_ok { color: #4ade80; font-weight: 600; }
QLabel#badge_warn { color: #fbbf24; font-weight: 600; }
QLabel#accent { color: #c9a227; }
QCheckBox { spacing: 8px; }
QSlider::groove:horizontal { height: 6px; background: #1f1f2a; border-radius: 3px; }
QSlider::handle:horizontal { background: #c41e3a; width: 16px; margin: -5px 0; border-radius: 8px; }
"""


class UiBridge(QObject):
    status = Signal(str)
    transcript = Signal(str)
    error = Signal(str)
    mic_result = Signal(str)
    need_permission = Signal()


class MicPermissionDialog(QDialog):
    """One-button Qt popup → OS microphone privacy settings."""

    def __init__(self, status: MicPermissionStatus, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Microphone Access Required")
        self.setMinimumWidth(520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("Microphone permission needed")
        title.setObjectName("headline")
        layout.addWidget(title)

        body = QLabel(
            f"{status.message}\n\n"
            f"Platform: {status.platform_label}\n"
            f"{status.settings_command}\n\n"
            "MARKYELLS runs 100% locally — your voice never leaves this machine."
        )
        body.setWordWrap(True)
        body.setObjectName("subtitle")
        layout.addWidget(body)

        row = QHBoxLayout()
        open_btn = QPushButton(status.settings_label)
        open_btn.setObjectName("gold")
        open_btn.clicked.connect(self._open_settings)
        retry_btn = QPushButton("Retry microphone test")
        retry_btn.setObjectName("secondary")
        retry_btn.clicked.connect(self.accept)
        row.addWidget(open_btn)
        row.addWidget(retry_btn)
        layout.addLayout(row)

        close_btn = QPushButton("Continue without mic (not recommended)")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _open_settings(self) -> None:
        if open_microphone_settings():
            QMessageBox.information(
                self,
                "Settings opened",
                "Allow microphone access for Python / Terminal, then click Retry.",
            )
        else:
            QMessageBox.warning(self, "Could not open settings", "Open microphone privacy manually in OS settings.")


class WarningSplashDialog(QDialog):
    def __init__(self, settings: AutoSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.dont_show_again = False
        self.setWindowTitle("⚠ WARNING — JOKE SCREEN · MARKYELLS")
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        warn = QLabel("⚠  WARNING — JOKE SCREEN  ·  PRIVATE GIFT EDITION  ·  NOT OPEN SOURCE")
        warn.setStyleSheet("color:#ff6b6b; font-weight:700; font-size:14px;")
        layout.addWidget(warn)

        tabs = QTabWidget()
        for name, text in [
            ("The Joke", JOKE_TAB_TEXT),
            ("Backstory", BACKSTORY_TEXT),
            ("Corelogic", CORELOGIC_FOR_CURIOUS),
            ("License", LICENSE_TEXT),
        ]:
            te = QTextEdit()
            te.setReadOnly(True)
            te.setPlainText(text)
            tabs.addTab(te, name)
        layout.addWidget(tabs)

        row = QHBoxLayout()
        self._dont = QCheckBox("Don't show this again")
        row.addWidget(self._dont)
        row.addStretch()
        go = QPushButton("Continue →")
        go.setObjectName("primary")
        go.clicked.connect(self._finish)
        row.addWidget(go)
        layout.addLayout(row)

    def _finish(self) -> None:
        self.dont_show_again = self._dont.isChecked()
        self.accept()


class MarkyellsQtWindow(QMainWindow):
    def __init__(self, settings: AutoSettings, profile: RuntimeProfile):
        super().__init__()
        self.settings = settings
        self.profile = profile
        self.mic_analysis = discover_microphones()
        self.tts = LocalTTS()
        self.bridge = UiBridge()
        self.bridge.status.connect(self._set_status)
        self.bridge.transcript.connect(self._set_transcript)
        self.bridge.error.connect(self._on_error)
        self.bridge.mic_result.connect(self._set_mic_result)
        self.bridge.need_permission.connect(self._show_permission_popup)

        mic_idx = get_mic_by_index(settings.mic_device_index)
        self.engine = AutoSpeechEngine(profile, settings.record_seconds, mic_idx, settings.speech_language)
        self.shortcut_ctrl: ReckonShortcutController | None = None
        self.ptt_ctrl: PressToTalkController | None = None
        self._ptt_active = False

        self.setWindowTitle(f"MARKYELLS · Private Gift · {profile.backend_label}")
        self.setMinimumSize(1040, 780)
        self._build_ui()
        self._init_controllers()

        if settings.auto_listen_test_on_startup:
            QTimer.singleShot(600, self._run_mic_check)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        brand = QLabel("MARKYELLS")
        brand.setObjectName("headline")
        sub = QLabel("Luxury local speech · Thai + English · Qt GUI")
        sub.setObjectName("subtitle")
        col = QVBoxLayout()
        col.addWidget(brand)
        col.addWidget(sub)
        header.addLayout(col)
        header.addStretch()
        self.badge = QLabel(self.profile.local_badge)
        self.badge.setObjectName("badge_ok" if self.profile.is_local else "badge_warn")
        header.addWidget(self.badge)
        outer.addLayout(header)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)
        self._build_speak_tab()
        self._build_detect_tab()
        self._build_mic_tab()
        self._build_settings_tab()
        self._build_debug_tab()

        self.status = QLabel("Ready.")
        self.status.setObjectName("subtitle")
        outer.addWidget(self.status)

    def _card(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        return f

    def _build_speak_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        card = self._card()
        cl = QVBoxLayout(card)

        cl.addWidget(QLabel(f"Engine: {self.profile.speech_engine} · {self.profile.backend_label}"))
        cl.addWidget(QLabel(self.profile.message))

        row = QHBoxLayout()
        self.shortcut_chk = QCheckBox("Reckon Shortcut (global hotkey)")
        self.shortcut_chk.setChecked(self.settings.reckon_shortcut_enabled)
        self.shortcut_chk.toggled.connect(self._save_controllers)
        row.addWidget(self.shortcut_chk)
        self.paste_chk = QCheckBox("Auto-paste at cursor")
        self.paste_chk.setChecked(self.settings.auto_paste)
        self.paste_chk.toggled.connect(self._save_controllers)
        row.addWidget(self.paste_chk)
        cl.addLayout(row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["auto", "en", "th"])
        self.lang_combo.setCurrentText(self.settings.speech_language)
        self.lang_combo.currentTextChanged.connect(self._on_language)
        lang_row.addWidget(self.lang_combo)
        cl.addLayout(lang_row)

        btn_row = QHBoxLayout()
        rec = QPushButton(f"RECORD {self.settings.record_seconds}s")
        rec.setObjectName("secondary")
        rec.clicked.connect(self._on_record)
        self.mic_btn = QPushButton("HOLD TO TALK")
        self.mic_btn.setObjectName("primary")
        self.mic_btn.pressed.connect(self._mic_press)
        self.mic_btn.released.connect(self._mic_release)
        tts_btn = QPushButton("Speak transcript (local TTS)")
        tts_btn.setObjectName("gold")
        tts_btn.clicked.connect(self._speak_tts)
        btn_row.addWidget(rec)
        btn_row.addWidget(self.mic_btn)
        btn_row.addWidget(tts_btn)
        cl.addLayout(btn_row)

        self.transcript = QTextEdit()
        self.transcript.setPlaceholderText("Transcript appears here…")
        self.transcript.setMinimumHeight(260)
        cl.addWidget(self.transcript)
        lay.addWidget(card)
        self.tabs.addTab(w, "Speak")

    def _build_detect_tab(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self.detect_layout = QVBoxLayout(inner)
        scroll.setWidget(inner)
        self.tabs.addTab(scroll, "Auto Detect")
        self._render_engine_matrix()

        redetect = QPushButton("Re-detect runtime")
        redetect.setObjectName("secondary")
        redetect.clicked.connect(self._redetect)
        self.detect_layout.addWidget(redetect)

    def _build_mic_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        card = self._card()
        cl = QVBoxLayout(card)

        self.mic_info = QLabel(self.mic_analysis.message)
        self.mic_info.setWordWrap(True)
        cl.addWidget(self.mic_info)

        self.mic_combo = QComboBox()
        for d in self.mic_analysis.devices:
            self.mic_combo.addItem(d.label, d.index)
        if self.mic_analysis.devices:
            for i in range(self.mic_combo.count()):
                if self.mic_combo.itemData(i) == get_mic_by_index(self.settings.mic_device_index):
                    self.mic_combo.setCurrentIndex(i)
                    break
        self.mic_combo.currentIndexChanged.connect(self._on_mic_change)
        cl.addWidget(self.mic_combo)

        row = QHBoxLayout()
        scan = QPushButton("Rescan & auto-select best mic")
        scan.setObjectName("secondary")
        scan.clicked.connect(self._rescan_mics)
        test = QPushButton("Test listening (2s)")
        test.setObjectName("primary")
        test.clicked.connect(self._test_listening)
        perm = QPushButton("Open mic permission settings")
        perm.setObjectName("gold")
        perm.clicked.connect(self._show_permission_popup)
        row.addWidget(scan)
        row.addWidget(test)
        row.addWidget(perm)
        cl.addLayout(row)

        self.mic_test_out = QLabel("Mic test: not run yet.")
        self.mic_test_out.setWordWrap(True)
        cl.addWidget(self.mic_test_out)
        lay.addWidget(card)
        self.tabs.addTab(w, "Microphone")

    def _build_settings_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        card = self._card()
        cl = QVBoxLayout(card)

        self.warn_chk = QCheckBox("Show warning on startup")
        self.warn_chk.setChecked(self.settings.show_warning_on_startup)
        cl.addWidget(self.warn_chk)

        self.tts_chk = QCheckBox("Enable local TTS read-back after transcribe")
        self.tts_chk.setChecked(self.settings.tts_enabled)
        cl.addWidget(self.tts_chk)

        self.automic_chk = QCheckBox("Auto mic permission test on startup")
        self.automic_chk.setChecked(self.settings.auto_listen_test_on_startup)
        cl.addWidget(self.automic_chk)

        cl.addWidget(QLabel("Speech engine override"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["auto", "faster_whisper", "mlx_whisper", "apple_speech", "speech_recognition"])
        self.engine_combo.setCurrentText(self.settings.speech_engine_override)
        self.engine_combo.currentTextChanged.connect(self._on_engine_override)
        cl.addWidget(self.engine_combo)

        cl.addWidget(QLabel("Shortcut mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["single", "combined"])
        self.mode_combo.setCurrentText(self.settings.shortcut_mode)
        self.mode_combo.currentTextChanged.connect(lambda _v: self._save_controllers())
        cl.addWidget(self.mode_combo)

        cl.addWidget(QLabel("Mic button mode (when shortcut OFF)"))
        self.ptt_combo = QComboBox()
        self.ptt_combo.addItems(["hold", "toggle"])
        self.ptt_combo.setCurrentText(self.settings.ptt_mode)
        self.ptt_combo.currentTextChanged.connect(self._on_ptt_mode)
        cl.addWidget(self.ptt_combo)

        key_row = QHBoxLayout()
        self.key1 = QComboBox()
        self.key1.addItems(KEY_OPTIONS)
        self.key1.setCurrentText(self.settings.shortcut_key1)
        self.key2 = QComboBox()
        self.key2.addItems(KEY_OPTIONS)
        self.key2.setCurrentText(self.settings.shortcut_key2)
        key_row.addWidget(QLabel("Key1"))
        key_row.addWidget(self.key1)
        key_row.addWidget(QLabel("Key2"))
        key_row.addWidget(self.key2)
        cl.addLayout(key_row)

        cl.addWidget(QLabel("Record duration (seconds)"))
        self.rec_slider = QSlider(Qt.Horizontal)
        self.rec_slider.setRange(3, 15)
        self.rec_slider.setValue(self.settings.record_seconds)
        self.rec_slider.valueChanged.connect(self._on_record_slider)
        cl.addWidget(self.rec_slider)

        save = QPushButton("Save settings")
        save.setObjectName("secondary")
        save.clicked.connect(self._save_settings)
        cl.addWidget(save)
        lay.addWidget(card)
        self.tabs.addTab(w, "Settings")

    def _build_debug_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        lay.addWidget(self.debug_text)
        refresh = QPushButton("Refresh debug dump")
        refresh.setObjectName("secondary")
        refresh.clicked.connect(self._refresh_debug)
        lay.addWidget(refresh)
        self.tabs.addTab(w, "Debug")
        self._refresh_debug()

    def _refresh_debug(self) -> None:
        hw = self.profile.hardware
        lines = [
            "=== MARKYELLS DEBUG ===",
            f"GUI: PySide6 Qt (luxury dark)",
            f"Profile ready: {self.profile.ready}",
            f"Backend: {self.profile.backend}",
            f"Engine: {self.profile.speech_engine}",
            f"Model: {self.profile.speech_model}",
            f"Override: {self.settings.speech_engine_override}",
            f"Hardware: {hw.label}",
            f"CPU: {hw.processor_raw}",
            f"Mac era: {hw.mac_era}",
            f"Python: {hw.python_version}",
            f"TTS: {self.tts.message or 'checking…'}",
            "",
            "=== ENGINE MATRIX ===",
        ]
        for opt in discover_all_engines(self.profile):
            lines.append(f"{opt.status_icon} {opt.engine_id} avail={opt.available} | {opt.summary}")
        perm = check_microphone_permission(get_mic_by_index(self.settings.mic_device_index))
        lines += ["", "=== MIC PERMISSION ===", perm.message, f"RMS: {perm.rms_level:.6f}"]
        self.debug_text.setPlainText("\n".join(lines))

    def _render_engine_matrix(self) -> None:
        if not hasattr(self, "detect_layout"):
            return
        while self.detect_layout.count() > 1:
            item = self.detect_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for opt in discover_all_engines(self.profile):
            card = self._card()
            cl = QVBoxLayout(card)
            title = f"{opt.status_icon} {opt.name}" + (" ★ ACTIVE" if opt.is_recommended else "")
            t = QLabel(title)
            t.setWordWrap(True)
            cl.addWidget(t)
            cl.addWidget(QLabel(opt.summary))
            if opt.available and opt.engine_id != "windows_local_note":
                btn = QPushButton("Use this engine")
                btn.setObjectName("secondary")
                btn.clicked.connect(lambda _c=False, eid=opt.engine_id: self._select_engine(eid))
                cl.addWidget(btn)
            self.detect_layout.insertWidget(self.detect_layout.count() - 1, card)

    def _init_controllers(self) -> None:
        if self.shortcut_ctrl:
            self.shortcut_ctrl.stop()
        mic = get_mic_by_index(self.settings.mic_device_index)
        self.shortcut_ctrl = ReckonShortcutController(
            engine=self.engine,
            key1=self.settings.shortcut_key1,
            key2=self.settings.shortcut_key2,
            mode=self.settings.shortcut_mode,
            enabled=self.settings.reckon_shortcut_enabled and self.profile.ready,
            auto_paste=self.settings.auto_paste,
            mic_index=mic,
            on_status=lambda m: self.bridge.status.emit(m),
            on_transcript=self._on_transcript_done,
            on_error=lambda e: self.bridge.error.emit(e),
        )
        self.shortcut_ctrl.start()
        self.ptt_ctrl = PressToTalkController(
            engine=self.engine,
            mode=self.settings.ptt_mode,
            auto_paste=self.settings.auto_paste,
            mic_index=mic,
            on_status=lambda m: self.bridge.status.emit(m),
            on_transcript=self._on_transcript_done,
            on_error=lambda e: self.bridge.error.emit(e),
        )
        enabled = self.settings.reckon_shortcut_enabled
        self.mic_btn.setEnabled(not enabled and self.profile.ready)

    def _on_transcript_done(self, text: str) -> None:
        self.bridge.transcript.emit(text or "")
        if self.settings.tts_enabled and text:
            self.tts.speak(text)

    def _set_status(self, msg: str) -> None:
        self.status.setText(msg)

    def _set_transcript(self, text: str) -> None:
        self.transcript.setPlainText(text or "(silence…)")

    def _on_error(self, msg: str) -> None:
        self.status.setText(f"Error: {msg}")
        if "mic" in msg.lower() or "permission" in msg.lower() or "audio" in msg.lower():
            self._show_permission_popup()

    def _set_mic_result(self, msg: str) -> None:
        self.mic_test_out.setText(msg)

    def _run_mic_check(self) -> None:
        status = check_microphone_permission(get_mic_by_index(self.settings.mic_device_index))
        self.mic_test_out.setText(status.message)
        if status.needs_permission:
            self._show_permission_popup(status)

    def _show_permission_popup(self, status: MicPermissionStatus | None = None) -> None:
        if status is None:
            status = check_microphone_permission(get_mic_by_index(self.settings.mic_device_index))
        dlg = MicPermissionDialog(status, self)
        if dlg.exec() == QDialog.Accepted:
            self._run_mic_check()

    def _test_listening(self) -> None:
        self.status.setText("Mic test: listening 2s…")

        def worker() -> None:
            idx = get_mic_by_index(self.settings.mic_device_index)
            perm = check_microphone_permission(idx)
            path = save_test_wav(2.0, idx)
            if path and perm.test_passed:
                msg = f"OK — captured audio. RMS={perm.rms_level:.4f} · saved {path.name}"
            else:
                msg = perm.message
            self.bridge.mic_result.emit(msg)
            self.bridge.status.emit("Mic test done.")
            if perm.needs_permission:
                self.bridge.need_permission.emit()

        threading.Thread(target=worker, daemon=True).start()

    def _on_record(self) -> None:
        self.engine.record_and_transcribe(
            on_status=lambda m: self.bridge.status.emit(m),
            on_done=self._on_transcript_done,
            on_error=lambda e: self.bridge.error.emit(e),
        )

    def _mic_press(self) -> None:
        if self.settings.reckon_shortcut_enabled or not self.ptt_ctrl:
            return
        self.ptt_ctrl.mic_press()

    def _mic_release(self) -> None:
        if self.settings.reckon_shortcut_enabled or not self.ptt_ctrl:
            return
        self.ptt_ctrl.mic_release()

    def _speak_tts(self) -> None:
        text = self.transcript.toPlainText().strip()
        if not text:
            return
        self.tts.speak(
            text,
            on_done=lambda: self.bridge.status.emit("TTS done."),
            on_error=lambda e: self.bridge.error.emit(e),
        )

    def _on_language(self, v: str) -> None:
        self.settings.speech_language = v
        self.engine.language = v
        self.settings.save()

    def _on_ptt_mode(self, v: str) -> None:
        self.settings.ptt_mode = v
        if self.ptt_ctrl:
            self.ptt_ctrl.mode = v
        label = "TAP TO TOGGLE" if v == "toggle" else "HOLD TO TALK"
        self.mic_btn.setText(label)
        self.settings.save()

    def _on_mic_change(self) -> None:
        idx = self.mic_combo.currentData()
        if idx is not None:
            self.settings.mic_device_index = int(idx)
            self.engine.mic_device_index = int(idx)
            self._save_controllers()

    def _rescan_mics(self) -> None:
        self.mic_analysis = discover_microphones()
        self.mic_combo.clear()
        for d in self.mic_analysis.devices:
            self.mic_combo.addItem(d.label, d.index)
        self.settings.mic_device_index = self.mic_analysis.recommended_index
        self.mic_info.setText(self.mic_analysis.message)
        self._save_controllers()

    def _on_record_slider(self, v: int) -> None:
        self.settings.record_seconds = v
        self.engine.record_seconds = v

    def _on_engine_override(self, v: str) -> None:
        self.settings.speech_engine_override = v
        self.settings.save()
        self._redetect()

    def _select_engine(self, engine_id: str) -> None:
        self.settings.speech_engine_override = engine_id
        self.engine_combo.setCurrentText(engine_id)
        self.settings.save()
        self._redetect()

    def _redetect(self) -> None:
        self.profile = apply_engine_override(detect_runtime(), self.settings.speech_engine_override)
        mic_idx = get_mic_by_index(self.settings.mic_device_index)
        self.engine = AutoSpeechEngine(self.profile, self.settings.record_seconds, mic_idx, self.settings.speech_language)
        self.setWindowTitle(f"MARKYELLS · Private Gift · {self.profile.backend_label}")
        self._init_controllers()
        self._render_engine_matrix()
        self._refresh_debug()

    def _save_controllers(self) -> None:
        self.settings.reckon_shortcut_enabled = self.shortcut_chk.isChecked()
        self.settings.auto_paste = self.paste_chk.isChecked()
        self.settings.shortcut_mode = self.mode_combo.currentText()
        self.settings.shortcut_key1 = self.key1.currentText()
        self.settings.shortcut_key2 = self.key2.currentText()
        self.settings.ptt_mode = self.ptt_combo.currentText()
        self.settings.save()
        self._init_controllers()

    def _save_settings(self) -> None:
        self.settings.show_warning_on_startup = self.warn_chk.isChecked()
        self.settings.tts_enabled = self.tts_chk.isChecked()
        self.settings.auto_listen_test_on_startup = self.automic_chk.isChecked()
        self.settings.save()
        self.status.setText("Settings saved.")

    def closeEvent(self, event) -> None:
        try:
            if self.shortcut_ctrl:
                self.shortcut_ctrl.stop()
                self.shortcut_ctrl = None
        except Exception:
            pass
        event.accept()
        threading.Thread(target=_unhook_keyboard_async, args=(0.15,), daemon=True).start()
        import os

        os._exit(0)


def run_qt() -> None:
    print("[MARKYELLS] run_qt() · PySide6 · no CustomTkinter in this path", flush=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(LUXURY_QSS)
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#08080c"))
    pal.setColor(QPalette.WindowText, QColor("#e8e6e3"))
    app.setPalette(pal)

    settings = AutoSettings.load()
    if settings.show_warning_on_startup:
        splash = WarningSplashDialog(settings)
        if splash.exec() != QDialog.Accepted:
            sys.exit(0)
        if splash.dont_show_again:
            settings.show_warning_on_startup = False
            settings.save()

    profile = apply_engine_override(detect_runtime(), settings.speech_engine_override)
    win = MarkyellsQtWindow(settings, profile)

    def _on_quit() -> None:
        try:
            if win.shortcut_ctrl:
                win.shortcut_ctrl.stop()
        except Exception:
            pass
        threading.Thread(
            target=lambda: (_unhook_keyboard_async(0.2)),
            daemon=True,
        ).start()

    app.aboutToQuit.connect(_on_quit)
    win.show()
    app.exec()
    _unhook_keyboard_async(0.25)
    sys.exit(0)


def main() -> None:
    run_qt()


if __name__ == "__main__":
    main()