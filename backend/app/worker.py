import time
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from app.logic import compute_next_generation, compute_next_generation_batch
from app import benchmark_logger

class SimulationWorker(QObject):
    step_done = pyqtSignal(np.ndarray, float, str)
    benchmark_done = pyqtSignal(np.ndarray, float, float, int, str)
    benchmark_all_done = pyqtSignal(dict, int, int, int, np.ndarray)

    @pyqtSlot(np.ndarray, str)
    def do_step(self, grid, mode):
        t0 = time.perf_counter()
        next_grid, mode_used = compute_next_generation(grid, mode)
        t1 = time.perf_counter()
        self.step_done.emit(next_grid, (t1 - t0) * 1000, mode_used)

    @pyqtSlot(np.ndarray, str, int, str)
    def do_benchmark(self, grid, mode, steps, pattern_name):
        rows, cols = grid.shape
        cells = grid.size

        if mode in ("all_report_engines", "all_engines"):
            # Run all 4 report engines on the exact same starting grid state
            engines = [
                ("gpu_opt", "CUDA Optimised"),
                ("gpu", "CUDA Original"),
                ("numba_opt", "CPU (OpenMP)"),
                ("loop", "Serial CPU"),
            ]
            all_results = {}
            final_display_grid = grid

            for engine_key, engine_label in engines:
                grid_input = np.copy(grid)
                t0 = time.perf_counter()
                res_grid, mode_used = compute_next_generation_batch(grid_input, engine_key, steps)
                t1 = time.perf_counter()
                total_ms = (t1 - t0) * 1000
                avg_ms = total_ms / steps
                throughput = (cells * steps) / (total_ms / 1000.0) / 1e6 if total_ms > 0 else 0
                
                benchmark_logger.log_result(mode_used, rows, cols, steps, total_ms, avg_ms, pattern_name)
                
                all_results[engine_key] = {
                    "mode_used": mode_used,
                    "label": engine_label,
                    "total_ms": total_ms,
                    "avg_ms": avg_ms,
                    "throughput": throughput
                }
                if engine_key == "gpu_opt":
                    final_display_grid = res_grid

            self.benchmark_all_done.emit(all_results, rows, cols, steps, final_display_grid)
            return

        t0 = time.perf_counter()
        next_grid, mode_used = compute_next_generation_batch(grid, mode, steps)
        t1 = time.perf_counter()
        total_ms = (t1 - t0) * 1000
        avg_ms = total_ms / steps
        
        benchmark_logger.log_result(mode_used, rows, cols, steps, total_ms, avg_ms, pattern_name)
        
        self.benchmark_done.emit(next_grid, total_ms, avg_ms, steps, mode_used)

