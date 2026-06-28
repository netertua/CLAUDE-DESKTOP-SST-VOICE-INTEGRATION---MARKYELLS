#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — CODELOGIC BASE (single-file core)
Developed by Capt Can Yapıcı

Windows'ta çalıştır:
    python markyells_corelog.py

Gereksinim:
    pip install customtkinter pillow
"""

from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

import customtkinter as ctk

# ── paths ──────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# ── content ──────────────────────────────────────────────────────────────────

JOKE_HEADLINE = (
    "EVEN MARK CAN YELL\n"
    "AT CLAUDE DESKTOP.\n"
    "POOR ANTHROPIC."
)

BACKSTORY_TEXT = """Developed by Capt Can Yapıcı.

Short story:

When I went to Thailand, I met — purely by chance — a bestie a lot like me: razor-sharp, living with EDS, and proudly ADHD. His name is Mark. One day he stayed on the phone with me for ages, listening with impossible patience while I talked his ear off.

So I built this speech recognizer as a gift for him — so my brilliant, lonely-but-quality friend would always have an infinite listener. Someone who never gets tired. Someone who actually hears him.

And yes: Claude Desktop still had no speech recognition. Everyone was complaining. Poor Anthropic. A whole company, all that money, all those engineers — and still no speech rec on desktop. Meanwhile Mark can yell at Claude Desktop all day long and nothing happens. Compare that to Anthropic's big promises.

So I thought: fine. If they won't build it, I will. Even from Thailand. Even on my own. Even I can build a speech recognizer — and I did.

This is MARKYELLS. Built for Mark. Built because he deserved better than silence.

Yell all you want. Someone's finally listening."""

# ── settings ─────────────────────────────────────────────────────────────────


@dataclass
class AppSettings:
    show_warning_on_startup: bool = True
    warning_duration_seconds: int = 10

    @classmethod
    def load(cls) -> "AppSettings":
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not SETTINGS_FILE.exists():
            return cls()
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return cls(
                show_warning_on_startup=bool(data.get("show_warning_on_startup", True)),
                warning_duration_seconds=int(data.get("warning_duration_seconds", 10)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ── platform probe ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RuntimeStatus:
    label: str
    available: bool
    platform: str
    message: str
    detail: str | None = None


def probe_runtime() -> RuntimeStatus:
    system = platform.system()
    machine = platform.machine().lower()
    plat = f"{system} ({machine})"

    if system == "Windows":
        return RuntimeStatus(
            label="Windows Code Model",
            available=True,
            platform=plat,
            message="Windows runtime aktif. Bu build şimdilik Windows üzerinde çalışıyor.",
            detail=f"Python {platform.python_version()}",
        )

    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        try:
            import mlx.core as mx

            tensor = mx.array([1.0, 2.0, 3.0])
            result = float(mx.sum(tensor).item())
            return RuntimeStatus(
                label="MLX",
                available=True,
                platform=plat,
                message="MLX hazır ve çalışıyor.",
                detail=f"mx.sum([1,2,3]) = {result}",
            )
        except ImportError:
            return RuntimeStatus(
                label="MLX",
                available=False,
                platform=plat,
                message="MLX kurulu değil. Kurulum: pip install mlx",
            )
        except Exception as exc:
            return RuntimeStatus(
                label="MLX",
                available=False,
                platform=plat,
                message=f"MLX testi başarısız: {exc}",
            )

    return RuntimeStatus(
        label="Runtime",
        available=False,
        platform=plat,
        message="Bu corelog build'i Windows veya macOS Apple Silicon için optimize edildi.",
    )


# ── splash / warning ─────────────────────────────────────────────────────────


class WarningSplash(ctk.CTk):
    """Ana GUI açılmadan önce gösterilen şaka + backstory ekranı."""

    def __init__(
        self,
        duration_seconds: int = 10,
        on_complete: callable | None = None,
    ):
        super().__init__()
        self.duration_seconds = max(1, duration_seconds)
        self.on_complete = on_complete
        self._seconds_left = self.duration_seconds
        self._skip_requested = False
        self._dont_show_again = False
        self._timer_job: str | None = None

        self.title("MARKYELLS — Warning / Joke Screen")
        self.geometry("820x580")
        self.minsize(720, 520)
        self.configure(fg_color="#050505")

        self._build_ui()
        self._start_timer()
        self.protocol("WM_DELETE_WINDOW", self._skip)

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=18)
        container.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            container,
            text="⚠  WARNING — JOKE SCREEN",
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

        self._build_joke_tab(tabview.add("The Joke"))
        self._build_story_tab(tabview.add("Backstory for Curious"))
        tabview.set("The Joke")

        self.timer_label = ctk.CTkLabel(
            container,
            text=f"Main app opens in {self._seconds_left}s...",
            font=ctk.CTkFont(size=13),
            text_color="#7a7a7a",
        )
        self.timer_label.pack(anchor="w", padx=20, pady=(0, 10))

        self.progress = ctk.CTkProgressBar(
            container,
            width=740,
            height=8,
            fg_color="#1f1f1f",
            progress_color="#ff4d4d",
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
            border_color="#444444",
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

    def _build_joke_tab(self, parent: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(parent, fg_color="#0a0a0a", corner_radius=12)
        inner.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(
            inner,
            text=JOKE_HEADLINE,
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#ff4d4d",
            justify="center",
            wraplength=700,
        ).pack(expand=True, pady=(40, 12))

        ctk.CTkLabel(
            inner,
            text="(this is a joke screen. mostly.)",
            font=ctk.CTkFont(size=13),
            text_color="#666666",
        ).pack(pady=(0, 40))

    def _build_story_tab(self, parent: ctk.CTkFrame) -> None:
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
            text="Backstory for Curious",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ff6b6b",
        ).pack(anchor="w", padx=20, pady=(20, 12))

        ctk.CTkLabel(
            scroll,
            text=BACKSTORY_TEXT,
            font=ctk.CTkFont(size=14),
            text_color="#c8c8c8",
            justify="left",
            wraplength=680,
        ).pack(anchor="w", padx=20, pady=(0, 24))

    def _start_timer(self) -> None:
        self._tick()

    def _tick(self) -> None:
        if self._skip_requested:
            return

        elapsed = self.duration_seconds - self._seconds_left
        self.progress.set(elapsed / self.duration_seconds)
        self.timer_label.configure(text=f"Main app opens in {self._seconds_left}s...")

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


# ── main window ──────────────────────────────────────────────────────────────


class MarkyellsApp(ctk.CTk):
    """Ana MARKYELLS arayüzü — CODELOGIC BASE iskelet."""

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.runtime = probe_runtime()

        self.title("MARKYELLS")
        self.geometry("960x640")
        self.minsize(820, 560)
        self.configure(fg_color="#0d0d0d")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self._build_ui()

    def _build_ui(self) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=52)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        ctk.CTkLabel(
            top_bar,
            text="MARKYELLS — CODELOGIC BASE",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f2f2f2",
        ).pack(side="left", padx=20)

        tabview = ctk.CTkTabview(
            self,
            fg_color="#111111",
            segmented_button_fg_color="#1a1a1a",
            segmented_button_selected_color="#2a2a2a",
            segmented_button_selected_hover_color="#333333",
            segmented_button_unselected_color="#141414",
            segmented_button_unselected_hover_color="#222222",
            text_color="#e8e8e8",
        )
        tabview.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        self._build_home_tab(tabview.add("Ana Sayfa"))
        self._build_settings_tab(tabview.add("Ayarlar"))
        tabview.set("Ana Sayfa")

    def _build_home_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card,
            text="Hoş geldin, Mark 👋",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#f5f5f5",
        ).pack(anchor="w", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            card,
            text="CODELOGIC BASE hazır. Tam GUI bağlantısı eklendiğinde buraya yerleştirilecek.",
            font=ctk.CTkFont(size=14),
            text_color="#9a9a9a",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 20))

        runtime_card = ctk.CTkFrame(card, fg_color="#0f0f0f", corner_radius=12)
        runtime_card.pack(fill="x", padx=24, pady=(0, 24))

        color = "#4ade80" if self.runtime.available else "#fbbf24"
        icon = "●" if self.runtime.available else "○"

        ctk.CTkLabel(
            runtime_card,
            text=f"{icon} {self.runtime.label}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            runtime_card,
            text=self.runtime.message,
            font=ctk.CTkFont(size=13),
            text_color="#c8c8c8",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 4))

        ctk.CTkLabel(
            runtime_card,
            text=f"Platform: {self.runtime.platform}",
            font=ctk.CTkFont(size=12),
            text_color="#777777",
        ).pack(anchor="w", padx=18, pady=(0, 4))

        if self.runtime.detail:
            ctk.CTkLabel(
                runtime_card,
                text=self.runtime.detail,
                font=ctk.CTkFont(size=12),
                text_color="#5eead4",
            ).pack(anchor="w", padx=18, pady=(0, 16))

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
            font=ctk.CTkFont(size=14),
            text_color="#d8d8d8",
            fg_color="#ff4d4d",
            hover_color="#cc3d3d",
            command=self._save_warning_pref,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            card,
            text=f"Uyarı süresi: {self.settings.warning_duration_seconds} saniye",
            font=ctk.CTkFont(size=13),
            text_color="#888888",
        ).pack(anchor="w", padx=24, pady=(0, 20))

        ctk.CTkButton(
            card,
            text="Uyarı Ekranını Şimdi Göster",
            width=220,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f1f1f",
            hover_color="#333333",
            border_width=1,
            border_color="#444444",
            command=self._preview_warning,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            card,
            text='"Don\'t show this again" bu ayarı kapatır.\n'
            "İstediğin zaman Ayarlar sekmesinden tekrar açabilirsin.",
            font=ctk.CTkFont(size=12),
            text_color="#666666",
            justify="left",
        ).pack(anchor="w", padx=24, pady=(8, 0))

    def _save_warning_pref(self) -> None:
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


# ── entry ────────────────────────────────────────────────────────────────────


def run() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    settings = AppSettings.load()
    root = ctk.CTk()
    root.withdraw()

    def open_main(dont_show_again: bool = False) -> None:
        if dont_show_again:
            settings.show_warning_on_startup = False
            settings.save()
        root.destroy()
        MarkyellsApp(settings).mainloop()

    if settings.show_warning_on_startup:
        splash = WarningSplash(
            duration_seconds=settings.warning_duration_seconds,
            on_complete=open_main,
        )
        splash.mainloop()
    else:
        root.destroy()
        MarkyellsApp(settings).mainloop()


if __name__ == "__main__":
    run()