# Conway's Game of Life — High-Performance Computing (HPC) Edition

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CUDA 12.x](https://img.shields.io/badge/CUDA-12.x-green.svg)](https://developer.nvidia.com/cuda-zone)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-informational.svg)](https://pypi.org/project/PyQt5/)
[![PyOpenGL](https://img.shields.io/badge/Render-PyOpenGL-red.svg)](https://pypi.org/project/PyOpenGL/)

A high-performance cellular automaton simulation and benchmarking suite developed for **CSE3102 / CCS3102 — High-Performance Computing**, Faculty of Computing, University of Sri Jayewardenepura.

This project implements Conway's Game of Life across multiple parallel computing architectures (multicore CPU via OpenMP and massively parallel GPU via NVIDIA CUDA), accompanied by an interactive **PyQt5 + PyOpenGL** desktop visualization application, live multi-engine benchmarking tools, and an integrated report analytics dashboard.

---

## Table of Contents

- [Architectures & Compute Engines](#architectures--compute-engines)
- [Key Features](#key-features)
- [Hardware & Software Environment](#hardware--software-environment)
- [Benchmark Results (100 Generations)](#benchmark-results-100-generations)
  - [Table 1: Serial CPU and OpenMP Results](#table-1-serial-cpu-and-openmp-results)
  - [Table 2: CUDA Results](#table-2-cuda-results)
  - [Table 3: Comparison of All Implementations](#table-3-comparison-of-all-implementations)
  - [Table 4: Speed-Up Ratios](#table-4-speed-up-ratios)
  - [Memory Transfer vs. Compute Overhead](#memory-transfer-vs-compute-overhead-section-72)
- [Installation & Setup](#installation--setup)
- [Usage & Controls](#usage--controls)
  - [Launching the GUI](#launching-the-gui)
  - [Interactive Controls & Shortcuts](#interactive-controls--shortcuts)
- [Running Automated Tests](#running-automated-tests)
- [Project Structure](#project-structure)

---

## Architectures & Compute Engines

The simulation models an infinite toroidal (wrap-around) 2D grid using double-buffering. Four primary computing engines are compared:

1. **⚡ CUDA Optimised (`gpu_opt`)**:
   - 2D thread block mapping ($16 \times 16 = 256$ threads per block).
   - Coalesced global memory access across consecutive columns.
   - Eliminates expensive runtime modulo (`%`) integer divisions for toroidal boundary wrapping using conditional coordinate checks.
   - Zero host-to-device memory copy overhead during generation loops by keeping buffers device-resident.
2. **🟢 CUDA Original (`gpu`)**:
   - Baseline CUDA kernel utilizing standard modulo arithmetic for boundary wrapping.
3. **💻 CPU OpenMP (`numba_opt`)**:
   - Multithreaded row-level parallelism (`#pragma omp parallel for schedule(static)`).
   - Contiguous row-major memory layout with row pointers (`p_above`, `p_curr`, `p_below`).
   - Inner loop vectorization with independent iteration hints (`ivdep`).
   - Reduction operations for population tracking.
4. **🔄 Serial CPU (`loop`)**:
   - Single-threaded baseline implementation using row pointers and double buffering.
5. **Additional Engines**:
   - **NumPy Vectorized (`numpy`)**: NumPy 2D array roll/slice vectorization.
   - **SciPy Convolution (`scipy`)**: 2D kernel convolution (`scipy.signal.convolve2d`).
   - **CPU Multicore (`numba`)**: Multi-threaded Numba JIT compiler with `parallel=True`.
   - **Numba Fast Branching (`numba_fast`)**: Branch-reduced neighbor counting.

---

## Key Features

- **Massive Grid Scale**: Handles configurations from $256 \times 256$ up to $4096 \times 4096$ (16.7+ million cells) at interactive framerates.
- **Hardware-Accelerated OpenGL Rendering**: Zero-copy texture streaming with viewport pan & zoom (centered on cursor) and visual theme customization (Monochrome Minimal, Cyberpunk Neon, Classic Emerald, Solarized Glow, High Contrast).
- **1-Click Multi-Engine Benchmark**: Benchmark all 4 core engines (**Serial CPU**, **OpenMP**, **CUDA Original**, **CUDA Optimised**) simultaneously on the current grid in a single click with real-time throughput ($M\text{ cells/s}$) and speed-up calculation.
- **HPC Report Results & Charts Viewer**:
  - Interactive tables replicating Tables 1–4 from the official assignment report.
  - Figure 1 execution time comparison plot with linear/logarithmic scale toggles.
  - Live benchmark suite runner that executes all 6 grid resolutions on the local machine with a progress bar.
  - Export capabilities for CSV and formatted Markdown.
- **Pattern Library & RLE Import**: Includes 22 classic configurations (Gosper Glider Gun, Pulsar, Simkin Glider Gun, etc.) with centering and auto-tiling options, plus direct Run Length Encoded (RLE) string parser.

---

## Hardware & Software Environment

The empirical benchmarks were measured under the following environment:

| Component | Specification |
|:---|:---|
| **CPU** | 12th Gen Intel(R) Core(TM) i5-12500H (2.50 GHz base, up to 4.50 GHz, 12 cores: 4 P-cores + 8 E-cores, 16 threads) |
| **System Memory** | 16 GB DDR4 RAM |
| **CPU Compiler Flags** | `-std=c++14 -O3 -Wall -fopenmp` |
| **GPU** | NVIDIA GeForce RTX 3050 Laptop GPU (4 GB GDDR6 VRAM, Compute Capability 8.6 / Ampere `sm_86`) |
| **CUDA Toolkit** | NVIDIA CUDA 12.9 (`nvcc` release 12.9, V12.9.86) |
| **CUDA Compiler Flags** | `-O3 -std=c++14 -arch=sm_86` |
| **Operating System** | Microsoft Windows 11 Pro 64-bit (Performance Power Mode) |

---

## Benchmark Results (100 Generations)

Workload evaluated across 100 generations with a randomized initial density of ~20% living cells.

### Table 1: Serial CPU and OpenMP Results

| Grid Size | Total Cells | Serial CPU (ms) | OpenMP CPU (ms) | OpenMP Throughput ($M\text{ cells/s}$) |
|:---|---:|---:|---:|---:|
| $256 \times 256$ | 65,536 | 16.84 | 16.54 | 396 |
| $512 \times 512$ | 262,144 | 65.84 | 27.23 | 963 |
| $1024 \times 1024$ | 1,048,576 | 243.45 | 62.20 | 1,686 |
| $1920 \times 1080$ | 2,073,600 | 468.62 | 98.03 | 2,115 |
| $2048 \times 2048$ | 4,194,304 | 941.40 | 201.28 | 2,084 |
| $4096 \times 4096$ | 16,777,216 | 3726.70 | 578.76 | 2,899 |

### Table 2: CUDA Results

| Grid Size | Total Cells | CUDA Original (ms) | CUDA Optimised (ms) | Optimised Throughput ($M\text{ cells/s}$) |
|:---|---:|---:|---:|---:|
| $256 \times 256$ | 65,536 | 6.21 | 4.75 | 1,379 |
| $512 \times 512$ | 262,144 | 9.15 | 5.79 | 4,531 |
| $1024 \times 1024$ | 1,048,576 | 35.29 | 21.51 | 4,876 |
| $1920 \times 1080$ | 2,073,600 | 61.59 | 20.54 | 10,096 |
| $2048 \times 2048$ | 4,194,304 | 125.50 | 77.51 | 5,411 |
| $4096 \times 4096$ | 16,777,216 | 587.62 | 310.22 | 5,408 |

### Table 3: Comparison of All Implementations

| Grid Size | Serial CPU (ms) | OpenMP CPU (ms) | CUDA Original (ms) | CUDA Optimised (ms) |
|:---|---:|---:|---:|---:|
| $256 \times 256$ | 16.84 | 16.54 | 6.21 | **4.75** |
| $512 \times 512$ | 65.84 | 27.23 | 9.15 | **5.79** |
| $1024 \times 1024$ | 243.45 | 62.20 | 35.29 | **21.51** |
| $1920 \times 1080$ | 468.62 | 98.03 | 61.59 | **20.54** |
| $2048 \times 2048$ | 941.40 | 201.28 | 125.50 | **77.51** |
| $4096 \times 4096$ | 3726.70 | 578.76 | 587.62 | **310.22** |

### Table 4: Speed-Up Ratios

| Grid Size | OpenMP vs. Serial | Optimised CUDA vs. Serial | Optimised CUDA vs. OpenMP |
|:---|:---:|:---:|:---:|
| $256 \times 256$ | $1.02\times$ | $3.55\times$ | $3.48\times$ |
| $512 \times 512$ | $2.42\times$ | $11.37\times$ | $4.70\times$ |
| $1024 \times 1024$ | $3.91\times$ | $11.32\times$ | $2.89\times$ |
| $1920 \times 1080$ | $4.78\times$ | $22.82\times$ | $4.77\times$ |
| $2048 \times 2048$ | $4.68\times$ | $12.15\times$ | $2.60\times$ |
| $4096 \times 4096$ | $6.44\times$ | **$12.01\times$** | **$1.87\times$** |

### Memory Transfer vs. Compute Overhead (Section 7.2)

Host-to-Device (H2D) and Device-to-Host (D2H) PCIe transfers over 100 generations were measured to quantify the benefit of GPU buffer residence:

| Grid Size | PCIe Transfer Overhead (ms) | GPU Compute Time (ms) | Transfer vs. Compute Ratio |
|:---|:---:|:---:|:---:|
| $1024 \times 1024$ | 214.70 ms | 21.51 ms | **$9.98\times$** |
| $4096 \times 4096$ | 766.23 ms | 310.22 ms | **$2.47\times$** |

Keeping buffers GPU-resident between steps avoids memory transfer penalties that would otherwise exceed raw computation by up to nearly $10\times$.

---

## Installation & Setup

### Prerequisites

- **Python**: 3.10 or 3.11
- **NVIDIA GPU**: Maxwell architecture or newer (Compute Capability $\ge 5.0$, recommended Ampere/Ada Lovelace)
- **NVIDIA Drivers**: R535+ with CUDA support

### Environment Configuration

1. Clone repository and navigate to `backend/`:
   ```powershell
   git clone https://github.com/desh2001/Conway-s-Game-of-Life.git
   cd Conway-s-Game-of-Life\backend
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install project dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
   *(Note: The environment includes automatic CUDA toolkit and NVVM DLL locator hooks via `app.cuda_setup`, ensuring Numba CUDA functions out-of-the-box without manual environment variable overrides).*

---

## Usage & Controls

### Launching the GUI

With your virtual environment active, run:

```powershell
python run_gui.py
```

### Interactive Controls & Shortcuts

| Action | Control |
|:---|:---|
| **Draw / Toggle Cell** | `Left Click` on grid |
| **Pan Grid** | `Middle Click` or `Right Click` + Drag |
| **Zoom Viewport** | `Mouse Wheel` (pivots around cursor location) |
| **Play / Pause** | `Spacebar` or **▶ RUN / ⏸ PAUSE** |
| **Single Step** | `S` key or **⏭ STEP** |
| **Clear Grid** | `C` key or **🗑 Clear Grid** |
| **Random Fill** | `R` key (populates with density specified in Pattern Library) |
| **Compare All 4 Engines in Once** | Click **🏆 Compare All 4 in Once** in the control dock |
| **View Full Report Tables & Charts** | Click **📊 HPC Report Results & Charts** |

---

## Running Automated Tests

Run the full pytest suite to verify logic correctness, RLE parsers, and GPU kernel functionality:

```powershell
pytest -v
```

---

## Project Structure

```
Conway-s-Game-of-Life/
├── backend/
│   ├── app/
│   │   ├── __init__.py           # Package init with CUDA configuration
│   │   ├── cuda_setup.py         # Automatic Windows CUDA/NVVM DLL path resolver
│   │   ├── logic.py              # CUDA kernels, Numba JIT, & CPU evolution logic
│   │   ├── controls.py           # PyQt5 sidebar dock with multi-engine controls
│   │   ├── renderer.py           # PyOpenGL texture shader & viewport manager
│   │   ├── chart_viewer.py       # Tabbed benchmark results & Figure 1 viewer
│   │   ├── report_data.py        # Official HPC assignment empirical data & tables
│   │   ├── benchmark_logger.py   # Thread-safe benchmark CSV logger
│   │   ├── patterns.py           # 22 built-in RLE patterns & parsing routines
│   │   ├── worker.py             # QThread simulation & benchmark worker
│   │   └── main_window.py        # Main application window & event orchestrator
│   ├── tests/                    # Pytest verification suite
│   ├── requirements.txt          # Production dependencies
│   └── run_gui.py                # Desktop application entry point
├── README.md                     # Project documentation
└── .gitignore
```

---

## Authors

- **T W V Deshan** (FC212048)
- **B P U Mendis** (FC2210)

*Faculty of Computing, University of Sri Jayewardenepura*  
*High-Performance Computing (HPC) — 2026*
