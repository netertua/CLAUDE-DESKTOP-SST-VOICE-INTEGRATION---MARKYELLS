#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKYELLS — Microphone discovery & analyzer (Windows AMD · Apple Silicon · Intel Mac)."""

from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class MicDevice:
    index: int
    name: str
    channels: int
    sample_rate: float
    is_default: bool
    host_api: str
    score: int
    tags: tuple[str, ...]

    @property
    def label(self) -> str:
        tag = f" [{', '.join(self.tags)}]" if self.tags else ""
        default = " ★" if self.is_default else ""
        return f"{self.index}: {self.name}{default}{tag}"


@dataclass(frozen=True)
class MicAnalysis:
    platform_label: str
    devices: tuple[MicDevice, ...]
    recommended_index: int | None
    recommended_name: str
    message: str
    is_desktop_hint: bool


_DESKTOP_KEYWORDS = (
    "usb", "external", "blue", "yeti", "snowball", "rode", "shure",
    "audio interface", "focusrite", "scarlett", "elgato", "wave",
    "desktop", "condenser", "podcast", "studio",
)
_LAPTOP_KEYWORDS = ("built-in", "internal", "macbook", "array", "embedded")
_APPLE_KEYWORDS = ("airpods", "beats", "iphone", "ipad", "continuity")


def _platform_label() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macOS Apple Silicon"
    if system == "Darwin":
        return "macOS Intel"
    if system == "Windows":
        vendor = "AMD" if "amd" in platform.processor().lower() else "Intel/Other"
        return f"Windows ({vendor})"
    return system


def _score_mic(name: str, is_default: bool, system: str) -> tuple[int, list[str]]:
    lower = name.lower()
    score = 0
    tags: list[str] = []

    if is_default:
        score += 30
        tags.append("default")

    for kw in _DESKTOP_KEYWORDS:
        if kw in lower:
            score += 25
            tags.append("desktop/external")
            break

    for kw in _LAPTOP_KEYWORDS:
        if kw in lower:
            score -= 10
            tags.append("built-in")
            break

    if system == "Darwin":
        for kw in _APPLE_KEYWORDS:
            if kw in lower:
                score += 5
                tags.append("apple-device")
                break
        if "macbook" not in lower and "built-in" not in lower:
            score += 10

    if "microphone" in lower or "mic" in lower:
        score += 5

    if re.search(r"disabled|null|dummy|mapper", lower):
        score -= 100
        tags.append("skip")

    return score, tags


def _mac_desktop_hint() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.model"], text=True, timeout=4).strip().lower()
        # MacBook = laptop, Mac mini/iMac/Mac Pro/Mac Studio = desktop
        return "macbook" not in out
    except Exception:
        return False


def discover_microphones() -> MicAnalysis:
    system = platform.system()
    plat = _platform_label()
    is_desktop = _mac_desktop_hint()

    try:
        import sounddevice as sd
    except ImportError:
        return MicAnalysis(
            platform_label=plat,
            devices=(),
            recommended_index=None,
            recommended_name="",
            message="sounddevice not installed. pip install sounddevice",
            is_desktop_hint=is_desktop,
        )

    try:
        default_in = sd.default.device[0]
        raw_devices = sd.query_devices()
        hostapis = sd.query_hostapis()
    except Exception as exc:
        return MicAnalysis(
            platform_label=plat,
            devices=(),
            recommended_index=None,
            recommended_name="",
            message=f"Mic scan failed: {exc}",
            is_desktop_hint=is_desktop,
        )

    found: list[MicDevice] = []

    for idx, dev in enumerate(raw_devices):
        if dev.get("max_input_channels", 0) < 1:
            continue

        name = str(dev.get("name", f"Device {idx}"))
        score, tags = _score_mic(name, idx == default_in, system)

        if "skip" in tags:
            continue

        api_idx = dev.get("hostapi", 0)
        api_name = hostapis[api_idx]["name"] if api_idx < len(hostapis) else "unknown"

        found.append(
            MicDevice(
                index=idx,
                name=name,
                channels=int(dev.get("max_input_channels", 1)),
                sample_rate=float(dev.get("default_samplerate", 44100)),
                is_default=(idx == default_in),
                host_api=str(api_name),
                score=score,
                tags=tuple(tags),
            )
        )

    found.sort(key=lambda d: d.score, reverse=True)

    if not found:
        msg = "No microphone found."
        if system == "Darwin":
            msg += " Check System Settings → Privacy → Microphone, then retry."
        return MicAnalysis(
            platform_label=plat,
            devices=(),
            recommended_index=None,
            recommended_name="",
            message=msg,
            is_desktop_hint=is_desktop,
        )

    best = found[0]
    if is_desktop and system == "Darwin":
        hint = "Desktop Mac detected — preferring external/USB mic if available."
    elif system == "Darwin":
        hint = "Mac detected — auto-selected best available input."
    elif "AMD" in plat:
        hint = "Windows AMD — using Python sounddevice host driver."
    else:
        hint = "Microphone ready."

    return MicAnalysis(
        platform_label=plat,
        devices=tuple(found),
        recommended_index=best.index,
        recommended_name=best.name,
        message=f"{hint} Selected: {best.name}",
        is_desktop_hint=is_desktop,
    )


def get_mic_by_index(index: int | None) -> int | None:
    """Validate mic index; fall back to auto-detect."""
    analysis = discover_microphones()
    if not analysis.devices:
        return None

    if index is None:
        return analysis.recommended_index

    valid = {d.index for d in analysis.devices}
    if index in valid:
        return index

    return analysis.recommended_index