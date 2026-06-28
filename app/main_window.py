from __future__ import annotations

import customtkinter as ctk

from app.mlx_probe import MLXStatus, probe_mlx
from app.settings_store import AppSettings
from app.splash import WarningSplash


class MarkyellsApp(ctk.CTk):
    """Ana MARKYELLS arayüzü — şimdilik iskelet, ileride genişletilecek."""

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.mlx_status = probe_mlx()

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
            text="MARKYELLS",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f2f2f2",
        ).pack(side="left", padx=20)

        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#111111",
            segmented_button_fg_color="#1a1a1a",
            segmented_button_selected_color="#2a2a2a",
            segmented_button_selected_hover_color="#333333",
            segmented_button_unselected_color="#141414",
            segmented_button_unselected_hover_color="#222222",
            text_color="#e8e8e8",
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        home_tab = self.tabview.add("Ana Sayfa")
        settings_tab = self.tabview.add("Ayarlar")

        self._build_home_tab(home_tab)
        self._build_settings_tab(settings_tab)

        self.tabview.set("Ana Sayfa")

    def _build_home_tab(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=16)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card,
            text="Hoş geldin, Markyells 👋",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#f5f5f5",
        ).pack(anchor="w", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            card,
            text="Ana GUI iskeleti hazır. Tam arayüz bağlantısı eklendiğinde buraya yerleştirilecek.",
            font=ctk.CTkFont(size=14),
            text_color="#9a9a9a",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 20))

        mlx_card = ctk.CTkFrame(card, fg_color="#0f0f0f", corner_radius=12)
        mlx_card.pack(fill="x", padx=24, pady=(0, 24))

        status_color = "#4ade80" if self.mlx_status.available else "#fbbf24"
        status_icon = "●" if self.mlx_status.available else "○"

        ctk.CTkLabel(
            mlx_card,
            text=f"{status_icon} MLX Durumu",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=status_color,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            mlx_card,
            text=self.mlx_status.message,
            font=ctk.CTkFont(size=13),
            text_color="#c8c8c8",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 4))

        ctk.CTkLabel(
            mlx_card,
            text=f"Platform: {self.mlx_status.platform}",
            font=ctk.CTkFont(size=12),
            text_color="#777777",
        ).pack(anchor="w", padx=18, pady=(0, 4))

        if self.mlx_status.sample_value:
            ctk.CTkLabel(
                mlx_card,
                text=self.mlx_status.sample_value,
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
            text='"Bir daha gösterme" seçeneği bu ayarı kapatır.\n'
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


def launch_app(settings: AppSettings) -> None:
    app = MarkyellsApp(settings)
    app.mainloop()