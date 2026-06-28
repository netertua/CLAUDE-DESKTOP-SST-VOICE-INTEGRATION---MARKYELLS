#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — MLX FINAL (single-file, Apple Silicon)
Developed by Capt Can Yapıcı

Mark'ın Mac'i için (M1/M2/M3/M4):
    pip install -r requirements_mlx.txt
    python markyells_mlx_final.py

CODELOGIC BASE (markyells_corelog.py) bittikten sonra bu final MLX build'i.
"""

from __future__ import annotations

import json
import platform
import tempfile
import threading
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import customtkinter as ctk

from markyells_content import BACKSTORY_TEXT, CORELOGIC_FOR_CURIOUS, JOKE_HEADLINE, LICENSE_TEXT

# ── paths ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings_mlx.json"
DEFAULT_WHISPER_MODEL = "mlx-community/whisper-tiny"

# ── settings ─────────────────────────────────────────────────────────────────


@dataclass
class MLXSettings:
    show_warning_on_startup: bool = True
    warning_duration_seconds: int = 10
    whisper_model: str = DEFAULT_WHISPER_MODEL
    record_seconds: int = 5

    @classmethod
    def load(cls) -> "MLXSettings":
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not SETTINGS_FILE.exists():
            return cls()
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return cls(
                show_warning_on_startup=bool(data.get("show_warning_on_startup", True)),
                warning_duration_seconds=int(data.get("warning_duration_seconds", 10)),
                whisper_model=str(data.get("whisper_model", DEFAULT_WHISPER_MODEL)),
                record_seconds=int(data.get("record_seconds", 5)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ── mlx engine ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MLXRuntime:
    ready: bool
    platform: str
    message: str
    mlx_version: str | None = None
    device: str | None = None
    benchmark: str | None = None


class MLXEngine:
    """Apple Silicon üzerinde MLX + Whisper speech recognition."""

    def __init__(self, settings: MLXSettings):
        self.settings = settings
        self.runtime = self._probe()
        self._mx = None
        self._whisper = None

        if self.runtime.ready:
            import mlx.core as mx

            self._mx = mx
            import mlx_whisper

            self._whisper = mlx_whisper

    @staticmethod
    def _probe() -> MLXRuntime:
        system = platform.system()
        machine = platform.machine().lower()
        plat = f"{system} ({machine})"

        if system != "Darwin" or machine not in {"arm64", "aarch64"}:
            return MLXRuntime(
                ready=False,
                platform=plat,
                message="MLX FINAL yalnızca macOS + Apple Silicon (M serisi) üzerinde çalışır.",
            )

        try:
            import mlx
            import mlx.core as mx

            a = mx.random.uniform(shape=(2048, 2048))
            b = mx.random.uniform(shape=(2048, 2048))
            mx.eval(mx.matmul(a, b))

            return MLXRuntime(
                ready=True,
                platform=plat,
                message="MLX FINAL hazır. Metal GPU + unified memory aktif.",
                mlx_version=getattr(mlx, "__version__", "unknown"),
                device="Apple Silicon (Metal)",
                benchmark="2048×2048 matmul OK",
            )
        except ImportError:
            return MLXRuntime(
                ready=False,
                platform=plat,
                message="MLX kurulu değil. Kurulum: pip install mlx mlx-whisper",
            )
        except Exception as exc:
            return MLXRuntime(
                ready=False,
                platform=plat,
                message=f"MLX başlatma hatası: {exc}",
            )

    def transcribe_file(self, audio_path: Path) -> str:
        if not self.runtime.ready or self._whisper is None:
            raise RuntimeError(self.runtime.message)

        result = self._whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=self.settings.whisper_model,
        )
        return str(result.get("text", "")).strip()

    def record_and_transcribe(self, on_status: callable, on_done: callable, on_error: callable) -> None:
        def worker() -> None:
            try:
                on_status("Mikrofon dinleniyor...")
                wav_path = self._record_wav(self.settings.record_seconds)
                on_status("MLX Whisper transkribe ediyor...")
                text = self.transcribe_file(wav_path)
                wav_path.unlink(missing_ok=True)
                on_done(text)
            except Exception as exc:
                on_error(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _record_wav(seconds: int, sample_rate: int = 16000) -> Path:
        import numpy as np
        import sounddevice as sd

        seconds = max(1, min(30, seconds))
        audio = sd.rec(
            int(seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        pcm = np.clip(audio[:, 0], -1.0, 1.0)
        pcm16 = (pcm * 32767).astype("int16")

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm16.tobytes())

        return tmp_path


# ── splash ───────────────────────────────────────────────────────────────────


class WarningSplash(ctk.CTk):
    def __init__(self, duration_seconds: int = 10, on_complete: callable | None = None):
        super().__init__()
        self.duration_seconds = max(1, duration_seconds)
        self.on_complete = on_complete
        self._seconds_left = self.duration_seconds
        self._skip_requested = False
        self._dont_show_again = False
        self._timer_job: str | None = None

        self.title("MARKYELLS MLX FINAL — Warning")
        self.geometry("840x620")
        self.minsize(740, 560)
        self.configure(fg_color="#050505")
        self._build_ui()
        self._tick()
        self.protocol("WM_DELETE_WINDOW", self._skip)

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=18)
        container.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            container,
            text="⚠  WARNING — JOKE SCREEN  ·  MLX FINAL",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ff4d4d",
            fg_color="#1a0000",
            corner_radius=10,
            padx=16,
            pady=6,
        ).pack(anchor="w", padx=20, pady=(20, 10))

        tabview = ctk.CTkTabview(
            container,
            fg_color="#0f0f0f",
            segmented_button_fg_color="#1a1a1a",
            segmented_button_selected_color="#2a1515",
            segmented_button_selected_hover_color="#3a1a1a",
            segmented_button_unselected_color="#141414",
            segmented_button_unselected_hover_color="#222222",
            text_color="#e0e0e0",
        )
        tabview.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        joke = ctk.CTkFrame(tabview.add("The Joke"), fg_color="#0a0a0a", corner_radius=12)
        joke.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(
            joke,
            text=JOKE_HEADLINE,
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#ff4d4d",
            justify="center",
            wraplength=700,
        ).pack(expand=True, pady=(40, 12))
        ctk.CTkLabel(
            joke,
            text="(this is a joke screen. mostly.)",
            font=ctk.CTkFont(size=13),
            text_color="#666666",
        ).pack(pady=(0, 40))

        story_scroll = ctk.CTkScrollableFrame(
            tabview.add("Backstory for Curious"),
            fg_color="#0a0a0a",
            corner_radius=12,
        )
        story_scroll.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(
            story_scroll,
            text="Backstory for Curious",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ff6b6b",
        ).pack(anchor="w", padx=20, pady=(20, 12))
        ctk.CTkLabel(
            story_scroll,
            text=BACKSTORY_TEXT,
            font=ctk.CTkFont(size=14),
            text_color="#c8c8c8",
            justify="left",
            wraplength=680,
        ).pack(anchor="w", padx=20, pady=(0, 24))

        core_scroll = ctk.CTkScrollableFrame(
            tabview.add("Corelogic for Curious"),
            fg_color="#0a0a0a",
            corner_radius=12,
        )
        core_scroll.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(
            core_scroll,
            text="Corelogic for Curious",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ff6b6b",
        ).pack(anchor="w", padx=20, pady=(20, 12))
        ctk.CTkLabel(
            core_scroll,
            text=CORELOGIC_FOR_CURIOUS,
            font=ctk.CTkFont(size=14),
            text_color="#c8c8c8",
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=20, pady=(0, 24))

        tabview.set("The Joke")

        self.timer_label = ctk.CTkLabel(
            container,
            text=f"MLX app opens in {self._seconds_left}s...",
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
            font=ctk.CTkFont(size=13),
            text_color="#d0d0d0",
            fg_color="#ff4d4d",
            hover_color="#cc3d3d",
            command=lambda: setattr(self, "_dont_show_again", bool(self.dont_show_var.get())),
        ).pack(side="left")

        ctk.CTkButton(
            bottom,
            text="Skip →",
            width=140,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f1f1f",
            hover_color="#333333",
            text_color="#f0f0f0",
            border_width=1,
            border_color="#444444",
            command=self._skip,
        ).pack(side="right")

    def _tick(self) -> None:
        if self._skip_requested:
            return
        elapsed = self.duration_seconds - self._seconds_left
        self.progress.set(elapsed / self.duration_seconds)
        self.timer_label.configure(text=f"MLX app opens in {self._seconds_left}s...")
        if self._seconds_left <= 0:
            self._finish()
            return
        self._seconds_left -= 1
        self._timer_job = self.after(1000, self._tick)

    def _skip(self) -> None:
        if self._skip_requested:
            return
        self._skip_requested = True
        if self._timer_job:
            self.after_cancel(self._timer_job)
        self._finish()

    def _finish(self) -> None:
        if self.on_complete:
            self.on_complete(self._dont_show_again)
        self.destroy()


# ── main app ─────────────────────────────────────────────────────────────────


class MarkyellsMLXFinal(ctk.CTk):
    def __init__(self, settings: MLXSettings):
        super().__init__()
        self.settings = settings
        self.engine = MLXEngine(settings)

        self.title("MARKYELLS — MLX FINAL")
        self.geometry("980x700")
        self.minsize(860, 600)
        self.configure(fg_color="#0d0d0d")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)
        ctk.CTkLabel(
            top,
            text="MARKYELLS — MLX FINAL  ·  Built for Mark",
            font=ctk.CTkFont(size=18, weight="bold"),
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

        self._build_yell_tab(tabview.add("Yell"))
        self._build_home_tab(tabview.add("MLX Status"))
        self._build_settings_tab(tabview.add("Ayarlar"))
        tabview.set("Yell")

    def _build_yell_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card,
            text="Yell at MARKYELLS 🎙",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#f5f5f5",
        ).pack(anchor="w", padx=24, pady=(24, 6))

        ctk.CTkLabel(
            card,
            text="Konuş. MLX Whisper seni dinlesin. Sonsuz dinleyici — Mark için.",
            font=ctk.CTkFont(size=14),
            text_color="#9a9a9a",
        ).pack(anchor="w", padx=24, pady=(0, 16))

        self.status_label = ctk.CTkLabel(
            card,
            text="Hazır." if self.engine.runtime.ready else self.engine.runtime.message,
            font=ctk.CTkFont(size=13),
            text_color="#fbbf24" if not self.engine.runtime.ready else "#7dd3fc",
        )
        self.status_label.pack(anchor="w", padx=24, pady=(0, 12))

        self.yell_btn = ctk.CTkButton(
            card,
            text=f"🎤  YELL ({self.settings.record_seconds}s)",
            width=220,
            height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#ff4d4d",
            hover_color="#cc3d3d",
            state="normal" if self.engine.runtime.ready else "disabled",
            command=self._on_yell,
        )
        self.yell_btn.pack(anchor="w", padx=24, pady=(0, 16))

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
        self.transcript.insert("1.0", "Transkript burada görünecek...\n")
        self.transcript.configure(state="disabled")

    def _build_home_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        rt = self.engine.runtime
        color = "#4ade80" if rt.ready else "#fbbf24"
        icon = "●" if rt.ready else "○"

        ctk.CTkLabel(
            card,
            text=f"{icon} MLX Runtime",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=color,
        ).pack(anchor="w", padx=24, pady=(24, 8))

        for line in (
            rt.message,
            f"Platform: {rt.platform}",
            f"MLX version: {rt.mlx_version or '—'}",
            f"Device: {rt.device or '—'}",
            f"Benchmark: {rt.benchmark or '—'}",
            f"Whisper model: {self.settings.whisper_model}",
        ):
            ctk.CTkLabel(
                card,
                text=line,
                font=ctk.CTkFont(size=13),
                text_color="#c8c8c8",
                wraplength=820,
                justify="left",
            ).pack(anchor="w", padx=24, pady=(0, 6))

    def _build_settings_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card,
            text="Ayarlar",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f0f0f0",
        ).pack(anchor="w", padx=24, pady=(24, 16))

        self.warning_var = ctk.BooleanVar(value=self.settings.show_warning_on_startup)
        ctk.CTkCheckBox(
            card,
            text="Başlangıçta uyarı ekranını göster",
            variable=self.warning_var,
            fg_color="#ff4d4d",
            hover_color="#cc3d3d",
            command=self._save_settings,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        ctk.CTkLabel(card, text="Kayıt süresi (sn)", text_color="#aaaaaa").pack(
            anchor="w", padx=24, pady=(8, 4)
        )
        self.record_slider = ctk.CTkSlider(
            card, from_=3, to=15, number_of_steps=12, command=self._on_record_change
        )
        self.record_slider.set(self.settings.record_seconds)
        self.record_slider.pack(fill="x", padx=24, pady=(0, 4))
        self.record_label = ctk.CTkLabel(
            card, text=f"{self.settings.record_seconds} saniye", text_color="#888888"
        )
        self.record_label.pack(anchor="w", padx=24, pady=(0, 16))

        ctk.CTkButton(
            card,
            text="Uyarı Ekranını Şimdi Göster",
            width=220,
            fg_color="#1f1f1f",
            hover_color="#333333",
            border_width=1,
            border_color="#444444",
            command=self._preview_warning,
        ).pack(anchor="w", padx=24, pady=(0, 12))

    def _on_record_change(self, value: float) -> None:
        self.settings.record_seconds = int(value)
        self.record_label.configure(text=f"{self.settings.record_seconds} saniye")
        self.yell_btn.configure(text=f"🎤  YELL ({self.settings.record_seconds}s)")
        self._save_settings()

    def _save_settings(self) -> None:
        self.settings.show_warning_on_startup = bool(self.warning_var.get())
        self.settings.save()

    def _preview_warning(self) -> None:
        splash = WarningSplash(
            duration_seconds=self.settings.warning_duration_seconds,
            on_complete=self._on_preview_closed,
        )
        splash.grab_set()
        self.wait_window(splash)

    def _on_preview_closed(self, dont_show_again: bool) -> None:
        if dont_show_again:
            self.settings.show_warning_on_startup = False
            self.settings.save()
            self.warning_var.set(False)

    def _on_yell(self) -> None:
        self.yell_btn.configure(state="disabled")

        def status(msg: str) -> None:
            self.after(0, lambda: self.status_label.configure(text=msg))

        def done(text: str) -> None:
            def ui() -> None:
                self.transcript.configure(state="normal")
                self.transcript.delete("1.0", "end")
                self.transcript.insert("1.0", text or "(sessizlik...)")
                self.transcript.configure(state="disabled")
                self.status_label.configure(text="Tamam. Biri seni duydu.")
                self.yell_btn.configure(state="normal")

            self.after(0, ui)

        def error(msg: str) -> None:
            def ui() -> None:
                self.status_label.configure(text=f"Hata: {msg}")
                self.yell_btn.configure(state="normal")

            self.after(0, ui)

        self.engine.record_and_transcribe(status, done, error)


# ── entry ────────────────────────────────────────────────────────────────────


def run() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    settings = MLXSettings.load()
    root = ctk.CTk()
    root.withdraw()

    def open_main(dont_show_again: bool = False) -> None:
        if dont_show_again:
            settings.show_warning_on_startup = False
            settings.save()
        root.destroy()
        MarkyellsMLXFinal(settings).mainloop()

    if settings.show_warning_on_startup:
        WarningSplash(
            duration_seconds=settings.warning_duration_seconds,
            on_complete=open_main,
        ).mainloop()
    else:
        root.destroy()
        MarkyellsMLXFinal(settings).mainloop()


if __name__ == "__main__":
    run()