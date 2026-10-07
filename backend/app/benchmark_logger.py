import csv
import os
import threading
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmark_results.csv")
_lock = threading.Lock()

def log_result(method: str, grid_rows: int, grid_cols: int, steps: int, total_ms: float, avg_ms_per_step: float, pattern: str):
    file_exists = os.path.isfile(LOG_FILE)
    
    with _lock:
        with open(LOG_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "method", "grid_rows", "grid_cols", "steps", "total_ms", "avg_ms_per_step", "pattern"])
            
            timestamp = datetime.now().isoformat(timespec='seconds')
            writer.writerow([timestamp, method, grid_rows, grid_cols, steps, total_ms, f"{avg_ms_per_step:.4f}", pattern])

def clear_log():
    with _lock:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
