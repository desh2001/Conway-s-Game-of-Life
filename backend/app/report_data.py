"""HPC Assignment Benchmark Report Data and Results.

Course: CSE3102 / CCS3102 - High-Performance Computing
Faculty of Computing, University of Sri Jayewardenepura
Project: Conway's Game of Life
"""

REPORT_ENVIRONMENT = {
    "cpu": "12th Gen Intel(R) Core(TM) i5-12500H (2.50 GHz base, up to 4.50 GHz, 12 cores: 4 P-cores + 8 E-cores, 16 threads)",
    "ram": "16 GB RAM",
    "cpu_compiler": "GNU C++ compiler (MinGW-w64) GCC version 6.3.0 (-std=c++14 -O3 -Wall -fopenmp)",
    "gpu": "NVIDIA GeForce RTX 3050 Laptop GPU (4 GB GDDR6 VRAM, Compute Capability 8.6, sm_86)",
    "cuda_toolkit": "NVIDIA CUDA 12.9 (Cuda compilation tools release 12.9, V12.9.86)",
    "os": "Microsoft Windows 11 Pro 64-bit (Build 26300), Performance Power Mode",
    "steps": 100,
    "workload": "Random starting pattern (~20% living cells), 100 generations, 3 runs each"
}

REPORT_BENCHMARK_ROWS = [
    {
        "grid": "256 × 256",
        "rows": 256,
        "cols": 256,
        "cells": 65536,
        "serial_cpu_ms": 16.84,
        "openmp_cpu_ms": 16.54,
        "openmp_throughput": 396,
        "cuda_original_ms": 6.21,
        "cuda_optimised_ms": 4.75,
        "cuda_optimised_throughput": 1379,
        "speedup_openmp_vs_serial": 1.02,
        "speedup_cuda_opt_vs_serial": 3.55,
        "speedup_cuda_opt_vs_openmp": 3.48,
    },
    {
        "grid": "512 × 512",
        "rows": 512,
        "cols": 512,
        "cells": 262144,
        "serial_cpu_ms": 65.84,
        "openmp_cpu_ms": 27.23,
        "openmp_throughput": 963,
        "cuda_original_ms": 9.15,
        "cuda_optimised_ms": 5.79,
        "cuda_optimised_throughput": 4531,
        "speedup_openmp_vs_serial": 2.42,
        "speedup_cuda_opt_vs_serial": 11.37,
        "speedup_cuda_opt_vs_openmp": 4.70,
    },
    {
        "grid": "1024 × 1024",
        "rows": 1024,
        "cols": 1024,
        "cells": 1048576,
        "serial_cpu_ms": 243.45,
        "openmp_cpu_ms": 62.20,
        "openmp_throughput": 1686,
        "cuda_original_ms": 35.29,
        "cuda_optimised_ms": 21.51,
        "cuda_optimised_throughput": 4876,
        "speedup_openmp_vs_serial": 3.91,
        "speedup_cuda_opt_vs_serial": 11.32,
        "speedup_cuda_opt_vs_openmp": 2.89,
    },
    {
        "grid": "1920 × 1080",
        "rows": 1920,
        "cols": 1080,
        "cells": 2073600,
        "serial_cpu_ms": 468.62,
        "openmp_cpu_ms": 98.03,
        "openmp_throughput": 2115,
        "cuda_original_ms": 61.59,
        "cuda_optimised_ms": 20.54,
        "cuda_optimised_throughput": 10096,
        "speedup_openmp_vs_serial": 4.78,
        "speedup_cuda_opt_vs_serial": 22.82,
        "speedup_cuda_opt_vs_openmp": 4.77,
    },
    {
        "grid": "2048 × 2048",
        "rows": 2048,
        "cols": 2048,
        "cells": 4194304,
        "serial_cpu_ms": 941.40,
        "openmp_cpu_ms": 201.28,
        "openmp_throughput": 2084,
        "cuda_original_ms": 125.50,
        "cuda_optimised_ms": 77.51,
        "cuda_optimised_throughput": 5411,
        "speedup_openmp_vs_serial": 4.68,
        "speedup_cuda_opt_vs_serial": 12.15,
        "speedup_cuda_opt_vs_openmp": 2.60,
    },
    {
        "grid": "4096 × 4096",
        "rows": 4096,
        "cols": 4096,
        "cells": 16777216,
        "serial_cpu_ms": 3726.70,
        "openmp_cpu_ms": 578.76,
        "openmp_throughput": 2899,
        "cuda_original_ms": 587.62,
        "cuda_optimised_ms": 310.22,
        "cuda_optimised_throughput": 5408,
        "speedup_openmp_vs_serial": 6.44,
        "speedup_cuda_opt_vs_serial": 12.01,
        "speedup_cuda_opt_vs_openmp": 1.87,
    },
]

REPORT_TRANSFER_BENCHMARK = {
    "1024 × 1024": {
        "cells": 1048576,
        "transfer_overhead_ms": 214.70,
        "compute_time_ms": 21.51,
        "ratio_transfer_to_compute": "9.98×"
    },
    "4096 × 4096": {
        "cells": 16777216,
        "transfer_overhead_ms": 766.23,
        "compute_time_ms": 310.22,
        "ratio_transfer_to_compute": "2.47×"
    }
}

def generate_markdown_report() -> str:
    """Returns markdown text of all four benchmark tables from the report."""
    md = []
    md.append("# Conway's Game of Life — HPC Benchmark Results (100 Generations)\n")
    md.append(f"**Hardware Environment:** {REPORT_ENVIRONMENT['cpu']} | {REPORT_ENVIRONMENT['gpu']}\n")
    
    md.append("## Table 1: Serial CPU and OpenMP Execution Times")
    md.append("| Grid Size | Cells | Serial CPU (ms) | OpenMP CPU (ms) | OpenMP Throughput (M cells/s) |")
    md.append("|:---|---:|---:|---:|---:|")
    for r in REPORT_BENCHMARK_ROWS:
        md.append(f"| {r['grid']} | {r['cells']:,} | {r['serial_cpu_ms']:.2f} | {r['openmp_cpu_ms']:.2f} | {r['openmp_throughput']:,} |")
    md.append("")

    md.append("## Table 2: CUDA Execution Times")
    md.append("| Grid Size | Cells | CUDA Original (ms) | CUDA Optimised (ms) | Optimised Throughput (M cells/s) |")
    md.append("|:---|---:|---:|---:|---:|")
    for r in REPORT_BENCHMARK_ROWS:
        md.append(f"| {r['grid']} | {r['cells']:,} | {r['cuda_original_ms']:.2f} | {r['cuda_optimised_ms']:.2f} | {r['cuda_optimised_throughput']:,} |")
    md.append("")

    md.append("## Table 3: Comparison of All Implementations")
    md.append("| Grid Size | Serial CPU (ms) | OpenMP CPU (ms) | CUDA Original (ms) | CUDA Optimised (ms) |")
    md.append("|:---|---:|---:|---:|---:|")
    for r in REPORT_BENCHMARK_ROWS:
        md.append(f"| {r['grid']} | {r['serial_cpu_ms']:.2f} | {r['openmp_cpu_ms']:.2f} | {r['cuda_original_ms']:.2f} | {r['cuda_optimised_ms']:.2f} |")
    md.append("")

    md.append("## Table 4: Speed-up Ratios")
    md.append("| Grid Size | OpenMP vs Serial | Optimised CUDA vs Serial | Optimised CUDA vs OpenMP |")
    md.append("|:---|---:|---:|---:|")
    for r in REPORT_BENCHMARK_ROWS:
        md.append(f"| {r['grid']} | {r['speedup_openmp_vs_serial']:.2f}× | {r['speedup_cuda_opt_vs_serial']:.2f}× | {r['speedup_cuda_opt_vs_openmp']:.2f}× |")
    md.append("")

    md.append("## Memory Transfer vs Compute Overhead (Section 7.2)")
    md.append("| Grid Size | Transfer Overhead (ms) | Compute Time (ms) | Transfer vs Compute Ratio |")
    md.append("|:---|---:|---:|---:|")
    for k, v in REPORT_TRANSFER_BENCHMARK.items():
        md.append(f"| {k} | {v['transfer_overhead_ms']:.2f} | {v['compute_time_ms']:.2f} | {v['ratio_transfer_to_compute']} |")
    md.append("")
    return "\n".join(md)
