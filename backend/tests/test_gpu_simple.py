import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import app.cuda_setup  # noqa: F401

import numpy as np
from numba import cuda

@cuda.jit
def simple_kernel(output, rows, cols):
    row, col = cuda.grid(2)
    if row < rows and col < cols:
        output[row, col] = 1

rows, cols = 3, 3
device_output = cuda.device_array((rows, cols), dtype=np.uint8)
simple_kernel[(1, 1), (16, 16)](device_output, rows, cols)
cuda.synchronize()
print("Success")
