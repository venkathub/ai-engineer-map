#!/usr/bin/env python3
"""Report a JarvisLabs GPU runtime without printing environment values."""

from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--require-env",
        action="append",
        default=[],
        metavar="NAME",
        help="require an environment variable by name; values are never printed",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    required_env = {name: bool(os.environ.get(name, "").strip()) for name in args.require_env}
    try:
        import torch
    except ImportError:
        print(json.dumps({"ok": False, "error": "PyTorch is missing", "required_env": required_env}, indent=2))
        return 2

    cuda_available = torch.cuda.is_available()
    report: dict[str, object] = {
        "ok": False,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cuda_available": cuda_available,
        "required_env": required_env,
        "filesystem": {
            "working_directory_writable": os.access(Path.cwd(), os.W_OK),
            "shared_storage_present": Path("/home/jl_fs").is_dir(),
            "shared_storage_writable": os.access("/home/jl_fs", os.W_OK),
            "working_disk_free_gb": round(shutil.disk_usage(Path.cwd()).free / 1024**3, 2),
        },
    }
    if shutil.which("nvidia-smi"):
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=driver_version,name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        report["nvidia_smi"] = result.stdout.strip().splitlines() if result.returncode == 0 else "query failed"
    if not cuda_available:
        report["error"] = "CUDA is not available"
        print(json.dumps(report, indent=2))
        return 1

    torch.manual_seed(7)
    left = torch.arange(16, dtype=torch.float32, device="cuda").reshape(4, 4)
    result = left @ torch.eye(4, dtype=torch.float32, device="cuda")
    matrix_check = bool(torch.equal(result, left))
    report.update({
        "device_count": torch.cuda.device_count(),
        "devices": [
            {
                "name": torch.cuda.get_device_name(index),
                "capability": ".".join(map(str, torch.cuda.get_device_capability(index))),
                "memory_gb": round(torch.cuda.get_device_properties(index).total_memory / 1024**3, 2),
            }
            for index in range(torch.cuda.device_count())
        ],
        "matrix_check": matrix_check,
        "checksum": float(result.sum().item()),
    })
    report["ok"] = matrix_check and all(required_env.values())
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
