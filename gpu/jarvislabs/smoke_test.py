#!/usr/bin/env python3
"""Small, deterministic CUDA check suitable for an explicit JarvisLabs run."""

from __future__ import annotations

import json
import platform


def main() -> int:
    try:
        import torch
    except ImportError:
        print("PyTorch is missing. Install requirements/hoe-gpu.txt.")
        return 2

    if not torch.cuda.is_available():
        print("CUDA is not available; run this check on the intended GPU host.")
        return 1

    torch.manual_seed(7)
    device = torch.device("cuda")
    left = torch.arange(16, dtype=torch.float32, device=device).reshape(4, 4)
    right = torch.eye(4, dtype=torch.float32, device=device)
    result = left @ right
    expected = torch.arange(16, dtype=torch.float32, device=device).reshape(4, 4)
    passed = bool(torch.equal(result, expected))
    report = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "device_count": torch.cuda.device_count(),
        "matrix_check": passed,
        "checksum": float(result.sum().item()),
    }
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
