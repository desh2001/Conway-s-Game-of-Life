"""CUDA environment setup for Numba.

Automatically discovers bundled or pip-installed NVIDIA CUDA components
(e.g., nvidia-cuda-nvcc-cu12, nvidia-cuda-runtime-cu12) and configures
CUDA_HOME, system PATH, and DLL directories before Numba compiles CUDA kernels.
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
import warnings

# Avoid cuCtxSynchronize_v2 context-destroyed error on CUDA 13.0+ drivers
os.environ.setdefault("NUMBA_CUDA_USE_NVIDIA_BINDING", "1")

# Suppress deprecation warnings from cuda.cuda bindings
warnings.filterwarnings("ignore", message=".*The cuda.cuda module is deprecated.*")


def setup_cuda_environment() -> bool:
    """Configures environment variables and DLL search paths for CUDA.

    Returns True if a CUDA toolkit / NVVM was found and configured, False otherwise.
    """
    candidate_nvidia_dirs: list[str] = []

    # 1. Search in Python's sys.path (site-packages in active environment)
    for p in sys.path:
        nv_dir = os.path.join(p, "nvidia")
        if os.path.isdir(nv_dir):
            candidate_nvidia_dirs.append(nv_dir)

    # 2. Search in sys.prefix (e.g., venv/Lib/site-packages/nvidia)
    venv_site = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
    if os.path.isdir(venv_site) and venv_site not in candidate_nvidia_dirs:
        candidate_nvidia_dirs.append(venv_site)

    configured = False

    for nv_dir in candidate_nvidia_dirs:
        nvcc_dir = os.path.join(nv_dir, "cuda_nvcc")
        runtime_dir = os.path.join(nv_dir, "cuda_runtime")

        if os.path.isdir(nvcc_dir):
            if "CUDA_HOME" not in os.environ:
                os.environ["CUDA_HOME"] = nvcc_dir

            nvcc_bin = os.path.join(nvcc_dir, "bin")
            nvvm_bin = os.path.join(nvcc_dir, "nvvm", "bin")
            dirs_to_add = [nvcc_bin, nvvm_bin]

            if os.path.isdir(runtime_dir):
                rt_bin = os.path.join(runtime_dir, "bin")
                dirs_to_add.append(rt_bin)
                # Ensure cudart DLL is present in nvcc_bin so Numba can find it
                for dll in glob.glob(os.path.join(rt_bin, "cudart64_*.dll")):
                    target = os.path.join(nvcc_bin, os.path.basename(dll))
                    if not os.path.exists(target):
                        try:
                            shutil.copy2(dll, target)
                        except Exception:
                            pass

            for d in dirs_to_add:
                if os.path.isdir(d):
                    if hasattr(os, "add_dll_directory"):
                        try:
                            os.add_dll_directory(d)
                        except Exception:
                            pass
                    cur_path = os.environ.get("PATH", "")
                    if d not in cur_path:
                        os.environ["PATH"] = d + os.pathsep + cur_path

            configured = True
            break

    return configured


# Automatically run on module import
setup_cuda_environment()
