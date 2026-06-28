#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKYELLS — Runtime Auto-Detect
Apple Silicon MLX · Intel Mac CPU · Windows AMD/Intel · NVIDIA CUDA
"""

from __future__ import annotations

import platform
import subprocess
import sys
import tempfile
import threading
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from apple_native_speech import probe_apple_speech


@dataclass(frozen=True)
class HardwareInfo:
    os_name: str
    arch: str
    cpu_vendor: str
    mac_era: str | None
    processor_raw: str
    python_version: str

    @property
    def label(self) -> str:
        if self.mac_era == "apple_silicon":
            return "Apple Silicon Mac (M serisi)"
        if self.mac_era == "intel_mac":
            return "Intel Mac (2011–2020)"
        if self.os_name == "Windows" and self.cpu_vendor == "AMD":
            return "Windows · AMD CPU"
        if self.os_name == "Windows" and self.cpu_vendor == "Intel":
            return "Windows · Intel CPU"
        return f"{self.os_name} · {self.cpu_vendor}"


@dataclass(frozen=True)
class RuntimeProfile:
    hardware: HardwareInfo
    backend: str
    backend_label: str
    speech_engine: str
    speech_model: str
    ready: bool
    message: str
    is_local: bool = True
    details: tuple[str, ...] = field(default_factory=tuple)

    @property
    def local_badge(self) -> str:
        if self.is_local:
            return "🔒 100% Local · Offline · Free"
        return "☁️ Online API (fallback only)"


@dataclass(frozen=True)
class EngineOption:
    engine_id: str
    name: str
    platform_hint: str
    available: bool
    is_local: bool
    is_recommended: bool
    status_icon: str
    summary: str
    details: tuple[str, ...] = field(default_factory=tuple)


def _read_processor() -> str:
    raw = platform.processor() or ""
    if raw:
        return raw

    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor).Name -join ', '"],
                text=True,
                timeout=8,
                stderr=subprocess.DEVNULL,
            )
            return out.strip()
        except Exception:
            pass

    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True,
                timeout=5,
                stderr=subprocess.DEVNULL,
            )
            return out.strip()
        except Exception:
            pass

    return "unknown"


def _cpu_vendor(processor: str, system: str, machine: str) -> str:
    p = processor.lower()
    if "authenticamd" in p or "amd" in p:
        return "AMD"
    if "intel" in p or "genuineintel" in p:
        return "Intel"
    if system == "Darwin":
        if machine in {"arm64", "aarch64"}:
            return "Apple"
        return "Intel"
    return "Unknown"


def _mac_era(system: str, machine: str) -> str | None:
    if system != "Darwin":
        return None
    if machine in {"arm64", "aarch64"}:
        return "apple_silicon"
    if machine in {"x86_64", "amd64", "i386"}:
        return "intel_mac"
    return None


def detect_hardware() -> HardwareInfo:
    system = platform.system()
    machine = platform.machine().lower()
    processor = _read_processor()
    return HardwareInfo(
        os_name=system,
        arch=machine,
        cpu_vendor=_cpu_vendor(processor, system, machine),
        mac_era=_mac_era(system, machine),
        processor_raw=processor,
        python_version=platform.python_version(),
    )


def _probe_cuda() -> tuple[bool, str]:
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return True, name
    except Exception:
        pass
    return False, ""


def _probe_mlx() -> tuple[bool, str]:
    if platform.system() != "Darwin":
        return False, ""
    if platform.machine().lower() not in {"arm64", "aarch64"}:
        return False, ""
    try:
        import mlx
        import mlx.core as mx

        a = mx.array([1.0, 2.0, 3.0])
        mx.eval(mx.sum(a))
        return True, getattr(mlx, "__version__", "unknown")
    except Exception:
        return False, ""


def _probe_faster_whisper() -> bool:
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def _probe_speech_recognition() -> bool:
    try:
        import speech_recognition  # noqa: F401

        return True
    except ImportError:
        return False


def detect_runtime() -> RuntimeProfile:
    hw = detect_hardware()
    details: list[str] = [
        f"Hardware: {hw.label}",
        f"Arch: {hw.arch}",
        f"CPU: {hw.processor_raw}",
        f"Python: {hw.python_version}",
    ]

    mlx_ok, mlx_ver = _probe_mlx()
    cuda_ok, cuda_name = _probe_cuda()
    fw_ok = _probe_faster_whisper()
    sr_ok = _probe_speech_recognition()

    local_tag = "Mode: 100% local · offline · no API cost"

    # ── Apple Silicon → MLX local whisper ────────────────────────────────
    if hw.mac_era == "apple_silicon":
        if mlx_ok:
            return RuntimeProfile(
                hardware=hw,
                backend="mlx",
                backend_label="MLX + Metal (Apple Silicon)",
                speech_engine="mlx_whisper",
                speech_model="mlx-community/whisper-tiny",
                ready=True,
                message="Apple Silicon MLX aktif. mlx-whisper — tamamen local, ücretsiz.",
                is_local=True,
                details=tuple(
                    details
                    + [
                        f"MLX: {mlx_ver}",
                        "Speech: mlx-whisper (on-device Metal GPU)",
                        "Cost: $0 — model bir kez iner, sonra offline",
                        local_tag,
                    ]
                ),
            )
        if fw_ok:
            return RuntimeProfile(
                hardware=hw,
                backend="cpu_apple",
                backend_label="Apple Silicon CPU fallback",
                speech_engine="faster_whisper",
                speech_model="tiny",
                ready=True,
                message="MLX yok — faster-whisper CPU (local, free).",
                is_local=True,
                details=tuple(
                    details
                    + [
                        "MLX: not installed",
                        "Speech: faster-whisper CPU (local)",
                        local_tag,
                    ]
                ),
            )

    # ── Intel Mac (son 15 yıl) → local CPU ───────────────────────────────
    if hw.mac_era == "intel_mac":
        if fw_ok:
            return RuntimeProfile(
                hardware=hw,
                backend="cpu_intel_mac",
                backend_label="Intel Mac CPU mode",
                speech_engine="faster_whisper",
                speech_model="tiny",
                ready=True,
                message="Intel Mac algılandı. Local CPU whisper — free, offline.",
                is_local=True,
                details=tuple(
                    details
                    + [
                        "Speech: faster-whisper CPU (local)",
                        "Era: Intel Mac 2011–2020",
                        local_tag,
                    ]
                ),
            )

    # ── Windows NVIDIA → CUDA ──────────────────────────────────────────
    if hw.os_name == "Windows" and cuda_ok:
        if fw_ok:
            return RuntimeProfile(
                hardware=hw,
                backend="cuda",
                backend_label=f"NVIDIA CUDA · {cuda_name}",
                speech_engine="faster_whisper",
                speech_model="tiny",
                ready=True,
                message="NVIDIA GPU algılandı. Local CUDA whisper modu aktif.",
                is_local=True,
                details=tuple(
                    details + [f"GPU: {cuda_name}", "Speech: faster-whisper CUDA (local)", local_tag]
                ),
            )

    # ── Windows AMD → CPU optimized ────────────────────────────────────
    if hw.os_name == "Windows" and hw.cpu_vendor == "AMD":
        if fw_ok:
            return RuntimeProfile(
                hardware=hw,
                backend="cpu_amd",
                backend_label="AMD CPU mode (Windows)",
                speech_engine="faster_whisper",
                speech_model="tiny",
                ready=True,
                message="AMD CPU algılandı. Local faster-whisper CPU modu aktif.",
                is_local=True,
                details=tuple(
                    details
                    + [
                        "Vendor: AMD",
                        "Speech: faster-whisper CPU int8 (local)",
                        local_tag,
                    ]
                ),
            )

    # ── Windows Intel → CPU ────────────────────────────────────────────
    if hw.os_name == "Windows" and hw.cpu_vendor == "Intel":
        if fw_ok:
            return RuntimeProfile(
                hardware=hw,
                backend="cpu_intel",
                backend_label="Intel CPU mode (Windows)",
                speech_engine="faster_whisper",
                speech_model="tiny",
                ready=True,
                message="Intel CPU algılandı. Local faster-whisper CPU modu aktif.",
                is_local=True,
                details=tuple(
                    details + ["Vendor: Intel", "Speech: faster-whisper CPU (local)", local_tag]
                ),
            )

    # ── Generic Windows CPU ──────────────────────────────────────────────
    if hw.os_name == "Windows" and fw_ok:
        return RuntimeProfile(
            hardware=hw,
            backend="cpu_windows",
            backend_label="Windows CPU fallback",
            speech_engine="faster_whisper",
            speech_model="tiny",
            ready=True,
            message="Windows CPU modu aktif (local).",
            is_local=True,
            details=tuple(details + ["Speech: faster-whisper CPU (local)", local_tag]),
        )

    # Apple'da cloud API kullanma — her şey pahalı, local şart
    if hw.os_name == "Darwin":
        return RuntimeProfile(
            hardware=hw,
            backend="none",
            backend_label="Local engine required",
            speech_engine="none",
            speech_model="",
            ready=False,
            message="Apple için local engine gerekli: pip install mlx-whisper faster-whisper",
            is_local=True,
            details=tuple(
                details
                + [
                    "Apple policy: no paid cloud speech APIs",
                    "Install: mlx-whisper (M-series) or faster-whisper (Intel Mac)",
                ]
            ),
        )

    # ── speech_recognition son çare (Windows only, online) ─────────────
    if sr_ok:
        return RuntimeProfile(
            hardware=hw,
            backend="speech_recognition",
            backend_label="Google Speech API fallback",
            speech_engine="speech_recognition",
            speech_model="google",
            ready=True,
            message="faster-whisper yok — Google Speech API yedek (online, not local).",
            is_local=False,
            details=tuple(details + ["Speech: speech_recognition (online only)", "⚠ Not local"]),
        )

    return RuntimeProfile(
        hardware=hw,
        backend="none",
        backend_label="No backend",
        speech_engine="none",
        speech_model="",
        ready=False,
        message="Speech engine bulunamadı. pip install faster-whisper sounddevice",
        is_local=True,
        details=tuple(details),
    )


def discover_all_engines(profile: RuntimeProfile | None = None) -> tuple[EngineOption, ...]:
    """Debug matrix: every speech option for this machine (MLX, whisper, Apple OS, cloud)."""
    if profile is None:
        profile = detect_runtime()

    hw = profile.hardware
    mlx_ok, mlx_ver = _probe_mlx()
    cuda_ok, cuda_name = _probe_cuda()
    fw_ok = _probe_faster_whisper()
    sr_ok = _probe_speech_recognition()
    apple = probe_apple_speech()

    options: list[EngineOption] = []

    # ── Apple Silicon MLX ────────────────────────────────────────────────
    if hw.mac_era == "apple_silicon":
        options.append(
            EngineOption(
                engine_id="mlx_whisper",
                name="mlx-whisper (MLX + Metal GPU)",
                platform_hint="Apple Silicon Mac · desktop & laptop",
                available=mlx_ok,
                is_local=True,
                is_recommended=profile.speech_engine == "mlx_whisper",
                status_icon="●" if mlx_ok else "○",
                summary=(
                    f"Primary on M-series. MLX {mlx_ver}."
                    if mlx_ok
                    else "Not installed — pip install mlx mlx-whisper"
                ),
                details=(
                    "100% local · offline · Thai + English",
                    "NOT the same as faster-whisper — native Apple Silicon path",
                    f"Model: mlx-community/whisper-tiny",
                ),
            )
        )

    # ── faster-whisper (universal local) ───────────────────────────────
    fw_details: list[str] = ["100% local · offline · Thai + English via Whisper"]
    if cuda_ok:
        fw_details.insert(0, f"CUDA GPU: {cuda_name}")
    elif hw.os_name == "Windows" and hw.cpu_vendor == "AMD":
        fw_details.insert(0, "Windows AMD CPU int8 mode")
    elif hw.mac_era in {"apple_silicon", "intel_mac"}:
        fw_details.insert(0, "macOS CPU fallback when MLX unavailable")

    options.append(
        EngineOption(
            engine_id="faster_whisper",
            name="faster-whisper (CTranslate2)",
            platform_hint="Windows · Intel Mac · Apple Silicon fallback",
            available=fw_ok,
            is_local=True,
            is_recommended=profile.speech_engine == "faster_whisper",
            status_icon="●" if fw_ok else "○",
            summary="Installed and ready." if fw_ok else "Not installed — pip install faster-whisper",
            details=tuple(fw_details),
        )
    )

    # ── Apple Speech Framework (macOS built-in) ──────────────────────────
    if hw.os_name == "Darwin":
        apple_details = list(apple.details)
        if apple.locales:
            apple_details.append(f"Thai/English locales: {', '.join(apple.locales)}")
        options.append(
            EngineOption(
                engine_id="apple_speech",
                name="Apple Speech Framework (SFSpeechRecognizer)",
                platform_hint="macOS built-in · iMac · MacBook · Mac mini · Mac Studio",
                available=apple.available,
                is_local=True,
                is_recommended=profile.speech_engine == "apple_speech",
                status_icon="●" if apple.available else ("◐" if apple.framework_present else "○"),
                summary=apple.message,
                details=tuple(apple_details),
            )
        )

    # ── Windows note: no separate OS speech hook yet ─────────────────────
    if hw.os_name == "Windows":
        options.append(
            EngineOption(
                engine_id="windows_local_note",
                name="Windows built-in speech (info)",
                platform_hint="Windows desktop & laptop",
                available=False,
                is_local=True,
                is_recommended=False,
                status_icon="ℹ",
                summary="MARKYELLS uses faster-whisper as the Windows local engine.",
                details=(
                    "Windows has Speech Recognition in Settings, but no stable Python hook like macOS Speech.framework.",
                    "faster-whisper is the local path on Windows (same as your AMD machine now).",
                ),
            )
        )

    # ── Cloud fallback (Windows policy) ──────────────────────────────────
    if sr_ok and hw.os_name != "Darwin":
        options.append(
            EngineOption(
                engine_id="speech_recognition",
                name="Google Speech API (speech_recognition)",
                platform_hint="Windows online fallback only",
                available=True,
                is_local=False,
                is_recommended=profile.speech_engine == "speech_recognition",
                status_icon="☁",
                summary="Online only — used when faster-whisper is missing.",
                details=("Not local.", "Apple Macs skip this — local engines only."),
            )
        )

    return tuple(options)


def apply_engine_override(profile: RuntimeProfile, override: str) -> RuntimeProfile:
    """Apply manual engine pick from debug/settings. 'auto' keeps autodetect result."""
    if override in {"", "auto"}:
        return profile

    hw = profile.hardware
    mlx_ok, _ = _probe_mlx()
    fw_ok = _probe_faster_whisper()
    apple = probe_apple_speech()
    sr_ok = _probe_speech_recognition()

    if override == "mlx_whisper" and mlx_ok and hw.mac_era == "apple_silicon":
        return RuntimeProfile(
            hardware=hw,
            backend="mlx",
            backend_label="MLX + Metal (manual)",
            speech_engine="mlx_whisper",
            speech_model="mlx-community/whisper-tiny",
            ready=True,
            message="Manual: mlx-whisper (Apple Silicon local).",
            is_local=True,
            details=profile.details + ("Override: mlx-whisper selected in Settings.",),
        )

    if override == "faster_whisper" and fw_ok:
        backend = profile.backend if profile.speech_engine == "faster_whisper" else "cpu_manual"
        label = profile.backend_label if profile.speech_engine == "faster_whisper" else "faster-whisper (manual)"
        return RuntimeProfile(
            hardware=hw,
            backend=backend,
            backend_label=label,
            speech_engine="faster_whisper",
            speech_model="tiny",
            ready=True,
            message="Manual: faster-whisper (local CPU/CUDA).",
            is_local=True,
            details=profile.details + ("Override: faster-whisper selected in Settings.",),
        )

    if override == "apple_speech" and apple.available:
        return RuntimeProfile(
            hardware=hw,
            backend="apple_speech",
            backend_label="Apple Speech Framework (manual)",
            speech_engine="apple_speech",
            speech_model="SFSpeechRecognizer",
            ready=True,
            message="Manual: Apple Speech Framework (macOS built-in, local).",
            is_local=True,
            details=profile.details + ("Override: Apple Speech Framework selected.",),
        )

    if override == "speech_recognition" and sr_ok and hw.os_name != "Darwin":
        return RuntimeProfile(
            hardware=hw,
            backend="speech_recognition",
            backend_label="Google Speech API (manual)",
            speech_engine="speech_recognition",
            speech_model="google",
            ready=True,
            message="Manual: Google Speech API (online, not local).",
            is_local=False,
            details=profile.details + ("Override: online Google fallback.",),
        )

    return profile


class AutoSpeechEngine:
    """Algılanan backend'e göre otomatik speech recognition."""

    def __init__(
        self,
        profile: RuntimeProfile,
        record_seconds: int = 5,
        mic_device_index: int | None = None,
        language: str = "auto",
    ):
        self.profile = profile
        self.record_seconds = record_seconds
        self.mic_device_index = mic_device_index
        self.language = language if language in {"auto", "en", "th"} else "auto"
        self._fw_model = None
        self._recognizer = None

    def _whisper_language(self) -> str | None:
        if self.language == "en":
            return "en"
        if self.language == "th":
            return "th"
        return None

    def record_and_transcribe(
        self,
        on_status: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        def worker() -> None:
            try:
                if not self.profile.ready:
                    raise RuntimeError(self.profile.message)

                on_status("Listening to microphone...")
                wav_path = self._record_wav(self.record_seconds, self.mic_device_index)
                on_status(f"Transcribing ({self.profile.backend_label})...")
                text = self.transcribe_file(wav_path)
                wav_path.unlink(missing_ok=True)
                on_done(text)
            except Exception as exc:
                on_error(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def transcribe_file(self, audio_path: Path) -> str:
        engine = self.profile.speech_engine

        if engine == "mlx_whisper":
            import mlx_whisper

            lang = self._whisper_language()
            kwargs = {"path_or_hf_repo": self.profile.speech_model}
            if lang:
                kwargs["language"] = lang
            result = mlx_whisper.transcribe(str(audio_path), **kwargs)
            return str(result.get("text", "")).strip()

        if engine == "faster_whisper":
            from faster_whisper import WhisperModel

            if self._fw_model is None:
                device = "cuda" if self.profile.backend == "cuda" else "cpu"
                compute = "float16" if device == "cuda" else "int8"
                self._fw_model = WhisperModel(
                    self.profile.speech_model,
                    device=device,
                    compute_type=compute,
                )

            lang = self._whisper_language()
            kwargs = {}
            if lang:
                kwargs["language"] = lang
            segments, _ = self._fw_model.transcribe(str(audio_path), **kwargs)
            return " ".join(seg.text.strip() for seg in segments).strip()

        if engine == "apple_speech":
            from apple_native_speech import transcribe_file as apple_transcribe

            return apple_transcribe(audio_path, self.language)

        if engine == "speech_recognition":
            import speech_recognition as sr

            if self._recognizer is None:
                self._recognizer = sr.Recognizer()

            with sr.AudioFile(str(audio_path)) as source:
                audio = self._recognizer.record(source)
            lang = "th-TH" if self.language == "th" else "en-US"
            return self._recognizer.recognize_google(audio, language=lang).strip()

        raise RuntimeError(f"Desteklenmeyen engine: {engine}")

    @staticmethod
    def _record_wav(
        seconds: int,
        device_index: int | None = None,
        sample_rate: int = 16000,
    ) -> Path:
        import numpy as np
        import sounddevice as sd

        seconds = max(1, min(30, seconds))
        kwargs = {
            "frames": int(seconds * sample_rate),
            "samplerate": sample_rate,
            "channels": 1,
            "dtype": "float32",
        }
        if device_index is not None:
            kwargs["device"] = device_index

        audio = sd.rec(**kwargs)
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