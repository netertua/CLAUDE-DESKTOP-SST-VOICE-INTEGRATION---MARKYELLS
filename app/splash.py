from __future__ import annotations

import customtkinter as ctk

JOKE_HEADLINE = (
    "EVEN MARK CAN YELL\n"
    "AT CLAUDE DESKTOP.\n"
    "POOR ANTHROPIC."
)

BACKSTORY_TEXT = """Developed by Capt Can Yapıcı.

So I built this speech recognizer as a gift for him — so my brilliant, lonely-but-quality friend would always have an infinite listener. Someone who never gets tired. Someone who actually hears him.

And yes: Claude Desktop still had no speech recognition. Everyone was complaining. Poor Anthropic. A whole company, all that money, all those engineers — and still no speech rec on desktop. Meanwhile Mark can yell at Claude Desktop all day long and nothing happens. Compare that to Anthropic's big promises.

So I thought: fine. If they won't build it, I will. Even from Thailand. Even on my own. Even I can build a speech recognizer — and I did.

This is MARKYELLS. Built for Mark. Built because he deserved better than silence.

Yell all you want. Someone's finally listening."""


class WarningSplash(ctk.CTk):
    """Ana GUI açılmadan önce gösterilen şaka + backstory ekranı."""

    def __init__(
        self,
        duration_seconds: int = 10,
        on_complete: callable | None = None,
    ):
        super().__init__()
        self.on_complete = on_complete
        self._skip_requested = False
        self._dont_show_again = False

        self.title("MARKYELLS — Warning / Şaka Ekranı")
        self.geometry("820x580")
        self.minsize(720, 520)
        self.configure(fg_color="#050505")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._skip)

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=18)
        container.pack(fill="both", expand=True, padx=24, pady=24)

        badge = ctk.CTkLabel(
            container,
            text="⚠  WARNING — JOKE SCREEN",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ff4d4d",
            fg_color="#1a0000",
            corner_radius=10,
            padx=16,
            pady=6,
        )
        badge.pack(anchor="w", padx=20, pady=(20, 10))

        self.tabview = ctk.CTkTabview(
            container,
            fg_color="#0f0f0f",
            segmented_button_fg_color="#1a1a1a",
            segmented_button_selected_color="#2a1515",
            segmented_button_selected_hover_color="#3a1a1a",
            segmented_button_unselected_color="#141414",
            segmented_button_unselected_hover_color="#222222",
            text_color="#e0e0e0",
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        joke_tab = self.tabview.add("The Joke")
        story_tab = self.tabview.add("Backstory for Curious")

        self._build_joke_tab(joke_tab)
        self._build_story_tab(story_tab)

        self.tabview.set("The Joke")

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
            command=self._on_dont_show_toggle,
        ).pack(side="left")

        ctk.CTkButton(
            bottom,
            text="Continue →",
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

    def _on_dont_show_toggle(self) -> None:
        self._dont_show_again = bool(self.dont_show_var.get())

    def _skip(self) -> None:
        if self._skip_requested:
            return
        self._skip_requested = True
        self._finish()

    def _finish(self) -> None:
        if self.on_complete:
            self.on_complete(self._dont_show_again)
        self.destroy()

    @property
    def dont_show_again(self) -> bool:
        return self._dont_show_again