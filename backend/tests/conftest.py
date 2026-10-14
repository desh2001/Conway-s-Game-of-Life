"""Root conftest – sets up environment before any test imports."""

import os
import sys

# Ensure Numba uses the NVIDIA cuda-python binding (avoids the
# cuCtxSynchronize_v2 context-destroyed error on CUDA 13.0 drivers).
os.environ.setdefault("NUMBA_CUDA_USE_NVIDIA_BINDING", "1")

# Allow ``from app.logic import …`` without installing as a package.
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure CUDA paths and bindings are configured before Numba compiles kernels
import app.cuda_setup  # noqa: F401

