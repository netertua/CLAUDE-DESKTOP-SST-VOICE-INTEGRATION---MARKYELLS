from __future__ import annotations

import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class MLXStatus:
    available: bool
    platform: str
    message: str
    sample_value: str | None = None


def probe_mlx() -> MLXStatus:
    system = platform.system()
    machine = platform.machine().lower()

    if system != "Darwin":
        return MLXStatus(
            available=False,
            platform=f"{system} ({machine})",
            message="MLX yalnızca macOS + Apple Silicon üzerinde çalışır.",
        )

    if machine not in {"arm64", "aarch64"}:
        return MLXStatus(
            available=False,
            platform=f"{system} ({machine})",
            message="MLX için Apple Silicon (M serisi) gerekir.",
        )

    try:
        import mlx.core as mx

        tensor = mx.array([1.0, 2.0, 3.0])
        result = float(mx.sum(tensor).item())
        return MLXStatus(
            available=True,
            platform=f"{system} ({machine})",
            message="MLX hazır ve çalışıyor.",
            sample_value=f"mx.sum([1,2,3]) = {result}",
        )
    except ImportError:
        return MLXStatus(
            available=False,
            platform=f"{system} ({machine})",
            message="MLX kurulu değil. Kurulum: pip install mlx",
        )
    except Exception as exc:
        return MLXStatus(
            available=False,
            platform=f"{system} ({machine})",
            message=f"MLX testi başarısız: {exc}",
        )