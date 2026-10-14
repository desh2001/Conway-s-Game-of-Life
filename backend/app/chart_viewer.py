import csv
import os
import time
from collections import defaultdict
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QCheckBox, QScrollArea, QMessageBox, QFileDialog, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QDialog, QApplication
)

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np

from app import benchmark_logger
from app import report_data
from app.logic import compute_next_generation_batch
from app.patterns import random_fill

METHOD_COLORS = {
    'loop': '#3b82f6',       # Serial CPU (Blue)
    'numba_opt': '#f97316',  # OpenMP CPU (Orange)
    'gpu': '#06b6d4',        # CUDA Original (Cyan)
    'gpu_opt': '#eab308',    # CUDA Optimised (Gold/Yellow)
    'numpy': '#a855f7',      # NumPy
    'scipy': '#ec4899',      # SciPy
    'numba': '#10b981',      # Numba Multi
    'numba_fast': '#14b8a6', # Numba Fast
}

METHOD_LABELS = {
    'loop': 'Serial CPU',
    'numba_opt': 'CPU (OpenMP)',
    'gpu': 'CUDA Original',
    'gpu_opt': 'CUDA Optimised',
    'numpy': 'CPU (NumPy)',
    'scipy': 'CPU (SciPy)',
    'numba': 'CPU (Numba)',
    'numba_fast': 'CPU (Numba Fast)',
}

class LiveSuiteWorker(QThread):
    progress = pyqtSignal(int, str)
    suite_done = pyqtSignal(list)

    def run(self):
        grids = [
            (256, 256, "256 × 256"),
            (512, 512, "512 × 512"),
            (1024, 1024, "1024 × 1024"),
            (1920, 1080, "1920 × 1080"),
            (2048, 2048, "2048 × 2048"),
            (4096, 4096, "4096 × 4096"),
        ]
        results = []
        total_steps = len(grids) * 4
        step_idx = 0

        for r, c, label in grids:
            cells = r * c
            # Warm-up / base grid with 20% living cells
            base_grid = random_fill(np.zeros((r, c), dtype=np.uint8), 0.20)
            
            row_res = {
                "grid": label,
                "rows": r,
                "cols": c,
                "cells": cells,
            }

            # 1. Serial CPU
            step_idx += 1
            self.progress.emit(int((step_idx / total_steps) * 100), f"Running Serial CPU on {label}...")
            # For 4096 on serial CPU, 100 steps can take ~3.7s, run 100 steps:
            t0 = time.perf_counter()
            compute_next_generation_batch(base_grid.copy(), "loop", 100)
            t1 = time.perf_counter()
            row_res["serial_cpu_ms"] = (t1 - t0) * 1000

            # 2. OpenMP CPU
            step_idx += 1
            self.progress.emit(int((step_idx / total_steps) * 100), f"Running CPU (OpenMP) on {label}...")
            t0 = time.perf_counter()
            compute_next_generation_batch(base_grid.copy(), "numba_opt", 100)
            t1 = time.perf_counter()
            row_res["openmp_cpu_ms"] = (t1 - t0) * 1000
            row_res["openmp_throughput"] = int((cells * 100) / ((t1 - t0) * 1e6)) if (t1 - t0) > 0 else 0

            # 3. CUDA Original
            step_idx += 1
            self.progress.emit(int((step_idx / total_steps) * 100), f"Running CUDA Original on {label}...")
            t0 = time.perf_counter()
            compute_next_generation_batch(base_grid.copy(), "gpu", 100)
            t1 = time.perf_counter()
            row_res["cuda_original_ms"] = (t1 - t0) * 1000

            # 4. CUDA Optimised
            step_idx += 1
            self.progress.emit(int((step_idx / total_steps) * 100), f"Running CUDA Optimised on {label}...")
            t0 = time.perf_counter()
            compute_next_generation_batch(base_grid.copy(), "gpu_opt", 100)
            t1 = time.perf_counter()
            row_res["cuda_optimised_ms"] = (t1 - t0) * 1000
            row_res["cuda_optimised_throughput"] = int((cells * 100) / ((t1 - t0) * 1e6)) if (t1 - t0) > 0 else 0

            # Calculate speedups
            s_ms = row_res["serial_cpu_ms"]
            o_ms = row_res["openmp_cpu_ms"]
            co_ms = row_res["cuda_optimised_ms"]
            row_res["speedup_openmp_vs_serial"] = s_ms / o_ms if o_ms > 0 else 1.0
            row_res["speedup_cuda_opt_vs_serial"] = s_ms / co_ms if co_ms > 0 else 1.0
            row_res["speedup_cuda_opt_vs_openmp"] = o_ms / co_ms if co_ms > 0 else 1.0

            results.append(row_res)

        self.suite_done.emit(results)


class ChartViewer(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HPC Benchmark Suite & Report Results")
        self.resize(1150, 780)
        self.apply_dark_theme()
        
        plt.style.use('dark_background')
        
        self.report_rows = list(report_data.REPORT_BENCHMARK_ROWS)
        self.data = []
        self.method_checkboxes = {}
        
        self.setup_ui()
        self.populate_report_tables()
        self.draw_report_chart()
        self.refresh_custom_log()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { 
                background-color: #0b0f19; 
                color: #e2e8f0; 
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background-color: #0b0f19;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #111827;
                color: #94a3b8;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid #1e293b;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #1e293b;
                color: #38bdf8;
                border-color: #38bdf8;
            }
            QTabBar::tab:hover {
                background: #1e293b;
                color: #ffffff;
            }
            QPushButton { 
                background-color: #1e293b; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                padding: 7px 14px; 
                color: #f1f5f9;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: #334155; 
                border-color: #38bdf8;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                gridline-color: #1e293b;
                color: #f8fafc;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #38bdf8;
                font-weight: 700;
                font-size: 12px;
                padding: 6px;
                border: 1px solid #0f172a;
            }
            QComboBox { 
                background-color: #0f172a; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                padding: 6px; 
                color: #f1f5f9;
            }
            QComboBox:focus, QComboBox:hover {
                border-color: #38bdf8;
            }
            QCheckBox { 
                spacing: 8px; 
            }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border-radius: 4px;
                border: 1px solid #475569;
                background: #0f172a;
            }
            QCheckBox::indicator:checked {
                background: #38bdf8;
                border-color: #38bdf8;
            }
        """)

    def setup_ui(self):
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        # ---------------- TAB 1: REPORT TABLES ----------------
        self.tab_tables = QWidget()
        tab_tables_layout = QVBoxLayout(self.tab_tables)
        tab_tables_layout.setContentsMargins(14, 14, 14, 14)
        tab_tables_layout.setSpacing(10)

        # Header bar with Actions
        hdr_lay = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("HPC Assignment Benchmark Evaluation (100 Generations)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        env_text = f"CPU: {report_data.REPORT_ENVIRONMENT['cpu'].split('(')[0]} &bull; GPU: {report_data.REPORT_ENVIRONMENT['gpu'].split('(')[0]}"
        lbl_env = QLabel(env_text)
        lbl_env.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_env)
        hdr_lay.addLayout(title_box)
        hdr_lay.addStretch()

        btn_copy_md = QPushButton("📋 Copy Tables (Markdown)")
        btn_copy_md.clicked.connect(self.copy_markdown_tables)
        hdr_lay.addWidget(btn_copy_md)

        btn_export_csv = QPushButton("💾 Export CSV")
        btn_export_csv.clicked.connect(self.export_report_csv)
        hdr_lay.addWidget(btn_export_csv)

        btn_run_suite = QPushButton("🚀 Run Live Suite on This Machine")
        btn_run_suite.setStyleSheet("background: #0284c7; color: white; border: 1px solid #38bdf8;")
        btn_run_suite.clicked.connect(self.start_live_suite)
        hdr_lay.addWidget(btn_run_suite)

        tab_tables_layout.addLayout(hdr_lay)

        # Scrollable container for tables
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        tables_container = QWidget()
        tables_vbox = QVBoxLayout(tables_container)
        tables_vbox.setSpacing(14)

        # Table 3: Summary Comparison of All 4 Implementations
        tables_vbox.addWidget(QLabel("<b style='color: #f1f5f9; font-size: 14px;'>Table 3. Execution Time for 100 Generations Across All Four Implementations</b>"))
        self.table_all = QTableWidget(6, 5)
        self.table_all.setHorizontalHeaderLabels(["Grid Size", "Serial CPU (ms)", "OpenMP CPU (ms)", "CUDA Original (ms)", "CUDA Optimised (ms)"])
        self.table_all.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_all.setFixedHeight(220)
        tables_vbox.addWidget(self.table_all)

        # Table 4: Speed-up Ratios
        tables_vbox.addWidget(QLabel("<b style='color: #f1f5f9; font-size: 14px;'>Table 4. Speed-up Ratios Across Implementations</b>"))
        self.table_speedup = QTableWidget(6, 4)
        self.table_speedup.setHorizontalHeaderLabels(["Grid Size", "OpenMP vs Serial", "Optimised CUDA vs Serial", "Optimised CUDA vs OpenMP"])
        self.table_speedup.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_speedup.setFixedHeight(220)
        tables_vbox.addWidget(self.table_speedup)

        # Sub-tables in horizontal row (Table 1 & Table 2)
        h_split = QHBoxLayout()
        
        # Table 1: CPU Results
        t1_box = QVBoxLayout()
        t1_box.addWidget(QLabel("<b style='color: #cbd5e1; font-size: 13px;'>Table 1. Serial CPU & OpenMP Results</b>"))
        self.table_cpu = QTableWidget(6, 4)
        self.table_cpu.setHorizontalHeaderLabels(["Grid Size", "Serial (ms)", "OpenMP (ms)", "Throughput (M/s)"])
        self.table_cpu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_cpu.setFixedHeight(220)
        t1_box.addWidget(self.table_cpu)
        h_split.addLayout(t1_box)

        # Table 2: CUDA Results
        t2_box = QVBoxLayout()
        t2_box.addWidget(QLabel("<b style='color: #cbd5e1; font-size: 13px;'>Table 2. CUDA Original & Optimised Results</b>"))
        self.table_cuda = QTableWidget(6, 4)
        self.table_cuda.setHorizontalHeaderLabels(["Grid Size", "CUDA Orig (ms)", "CUDA Opt (ms)", "Throughput (M/s)"])
        self.table_cuda.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_cuda.setFixedHeight(220)
        t2_box.addWidget(self.table_cuda)
        h_split.addLayout(t2_box)

        tables_vbox.addLayout(h_split)

        # Section 7.2 PCIe Memory Transfer Overhead Table
        tables_vbox.addWidget(QLabel("<b style='color: #cbd5e1; font-size: 13px;'>Section 7.2 Memory Transfer Overhead vs Compute Time (100 Generations)</b>"))
        self.table_transfer = QTableWidget(2, 4)
        self.table_transfer.setHorizontalHeaderLabels(["Grid Size", "Transfer Overhead (ms)", "Optimised Compute Time (ms)", "Transfer vs Compute Ratio"])
        self.table_transfer.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_transfer.setFixedHeight(105)
        tables_vbox.addWidget(self.table_transfer)

        scroll.setWidget(tables_container)
        tab_tables_layout.addWidget(scroll)
        self.tabs.addTab(self.tab_tables, "📑 All Benchmark Results (Tables)")

        # ---------------- TAB 2: REPORT CHART (Figure 1) ----------------
        self.tab_report_chart = QWidget()
        tab_chart_layout = QVBoxLayout(self.tab_report_chart)
        tab_chart_layout.setContentsMargins(14, 14, 14, 14)

        chart_ctrl_lay = QHBoxLayout()
        lbl_chart_title = QLabel("<b>Figure 1. Execution Time Comparison Across Different Grid Sizes</b>")
        lbl_chart_title.setStyleSheet("font-size: 14px; color: #38bdf8;")
        chart_ctrl_lay.addWidget(lbl_chart_title)
        chart_ctrl_lay.addStretch()

        self.check_log_scale = QCheckBox("Logarithmic Y-Axis Scale")
        self.check_log_scale.stateChanged.connect(self.draw_report_chart)
        chart_ctrl_lay.addWidget(self.check_log_scale)

        btn_export_rep_png = QPushButton("💾 Export Chart PNG")
        btn_export_rep_png.clicked.connect(self.export_report_chart_png)
        chart_ctrl_lay.addWidget(btn_export_rep_png)
        tab_chart_layout.addLayout(chart_ctrl_lay)

        self.figure_rep, self.ax_rep = plt.subplots(figsize=(10, 6))
        self.figure_rep.patch.set_facecolor('#0f172a')
        self.ax_rep.set_facecolor('#1e293b')
        self.canvas_rep = FigureCanvas(self.figure_rep)
        tab_chart_layout.addWidget(self.canvas_rep)
        self.tabs.addTab(self.tab_report_chart, "📈 Report Comparison Chart (Figure 1)")

        # ---------------- TAB 3: CUSTOM BENCHMARK LOG EXPLORER ----------------
        self.tab_custom = QWidget()
        custom_layout = QHBoxLayout(self.tab_custom)
        custom_layout.setContentsMargins(14, 14, 14, 14)

        # Custom Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(sidebar)
        side_layout.addWidget(QLabel("<b>Engines to Plot</b>"))
        for m, label in METHOD_LABELS.items():
            cb = QCheckBox(label)
            cb.setChecked(m in ['loop', 'numba_opt', 'gpu', 'gpu_opt'])
            cb.setStyleSheet(f"color: {METHOD_COLORS.get(m, '#ffffff')}; font-weight: bold;")
            cb.stateChanged.connect(self.draw_custom_chart)
            self.method_checkboxes[m] = cb
            side_layout.addWidget(cb)

        side_layout.addSpacing(15)
        side_layout.addWidget(QLabel("<b>Chart Type</b>"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Line Chart", "Bar Chart", "Scatter Plot"])
        self.combo_type.currentIndexChanged.connect(self.draw_custom_chart)
        side_layout.addWidget(self.combo_type)

        side_layout.addSpacing(10)
        side_layout.addWidget(QLabel("<b>X-Axis</b>"))
        self.combo_x = QComboBox()
        self.combo_x.addItems(["Grid Size (rows×cols)", "Steps", "Timestamp"])
        self.combo_x.currentIndexChanged.connect(self.draw_custom_chart)
        side_layout.addWidget(self.combo_x)

        side_layout.addSpacing(10)
        side_layout.addWidget(QLabel("<b>Y-Axis</b>"))
        self.combo_y = QComboBox()
        self.combo_y.addItems(["Total Time (ms)", "Throughput (M cells/s)", "Avg ms/step"])
        self.combo_y.currentIndexChanged.connect(self.draw_custom_chart)
        side_layout.addWidget(self.combo_y)

        side_layout.addStretch()
        btn_refresh = QPushButton("🔄 Refresh Log")
        btn_refresh.clicked.connect(self.refresh_custom_log)
        side_layout.addWidget(btn_refresh)

        btn_export_custom = QPushButton("💾 Export PNG")
        btn_export_custom.clicked.connect(self.export_custom_png)
        side_layout.addWidget(btn_export_custom)

        btn_clear = QPushButton("🗑 Clear Log Data")
        btn_clear.clicked.connect(self.clear_data)
        btn_clear.setStyleSheet("background-color: #991b1b; color: white;")
        side_layout.addWidget(btn_clear)

        self.label_status = QLabel("")
        side_layout.addWidget(self.label_status)

        custom_layout.addWidget(sidebar)

        self.figure_custom, self.ax_custom = plt.subplots(figsize=(8, 6))
        self.figure_custom.patch.set_facecolor('#0f172a')
        self.ax_custom.set_facecolor('#1e293b')
        self.canvas_custom = FigureCanvas(self.figure_custom)
        custom_layout.addWidget(self.canvas_custom, stretch=1)

        self.tabs.addTab(self.tab_custom, "📊 Custom Benchmark Explorer")

    def populate_report_tables(self):
        # 1. Summary Table 3
        for i, r in enumerate(self.report_rows):
            self._set_item(self.table_all, i, 0, r["grid"], bold=True)
            self._set_item(self.table_all, i, 1, f"{r['serial_cpu_ms']:.2f}", color="#cbd5e1")
            self._set_item(self.table_all, i, 2, f"{r['openmp_cpu_ms']:.2f}", color="#60a5fa")
            self._set_item(self.table_all, i, 3, f"{r['cuda_original_ms']:.2f}", color="#4ade80")
            self._set_item(self.table_all, i, 4, f"{r['cuda_optimised_ms']:.2f}", color="#38bdf8", bold=True)

        # 2. Speedup Table 4
        for i, r in enumerate(self.report_rows):
            self._set_item(self.table_speedup, i, 0, r["grid"], bold=True)
            self._set_item(self.table_speedup, i, 1, f"{r['speedup_openmp_vs_serial']:.2f}×", color="#60a5fa")
            self._set_item(self.table_speedup, i, 2, f"{r['speedup_cuda_opt_vs_serial']:.2f}×", color="#fbbf24", bold=True)
            self._set_item(self.table_speedup, i, 3, f"{r['speedup_cuda_opt_vs_openmp']:.2f}×", color="#38bdf8", bold=True)

        # 3. Table 1: CPU Results
        for i, r in enumerate(self.report_rows):
            self._set_item(self.table_cpu, i, 0, r["grid"], bold=True)
            self._set_item(self.table_cpu, i, 1, f"{r['serial_cpu_ms']:.2f}")
            self._set_item(self.table_cpu, i, 2, f"{r['openmp_cpu_ms']:.2f}", color="#60a5fa")
            self._set_item(self.table_cpu, i, 3, f"{r['openmp_throughput']:,}", color="#34d399", bold=True)

        # 4. Table 2: CUDA Results
        for i, r in enumerate(self.report_rows):
            self._set_item(self.table_cuda, i, 0, r["grid"], bold=True)
            self._set_item(self.table_cuda, i, 1, f"{r['cuda_original_ms']:.2f}", color="#4ade80")
            self._set_item(self.table_cuda, i, 2, f"{r['cuda_optimised_ms']:.2f}", color="#38bdf8", bold=True)
            self._set_item(self.table_cuda, i, 3, f"{r['cuda_optimised_throughput']:,}", color="#34d399", bold=True)

        # 5. Section 7.2 PCIe Transfer Overhead Table
        t_rows = list(report_data.REPORT_TRANSFER_BENCHMARK.items())
        for i, (k, v) in enumerate(t_rows):
            self._set_item(self.table_transfer, i, 0, k, bold=True)
            self._set_item(self.table_transfer, i, 1, f"{v['transfer_overhead_ms']:.2f} ms", color="#f87171")
            self._set_item(self.table_transfer, i, 2, f"{v['compute_time_ms']:.2f} ms", color="#38bdf8", bold=True)
            self._set_item(self.table_transfer, i, 3, v['ratio_transfer_to_compute'], color="#fbbf24", bold=True)

    def _set_item(self, table: QTableWidget, row: int, col: int, text: str, color: str = None, bold: bool = False):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter if col == 0 else Qt.AlignRight | Qt.AlignVCenter)
        if color:
            item.setForeground(QColor(color))
        font = item.font()
        font.setBold(bold)
        item.setFont(font)
        table.setItem(row, col, item)

    def draw_report_chart(self):
        self.ax_rep.clear()
        grids = [r["grid"] for r in self.report_rows]
        ser_times = [r["serial_cpu_ms"] for r in self.report_rows]
        omp_times = [r["openmp_cpu_ms"] for r in self.report_rows]
        cuda_orig = [r["cuda_original_ms"] for r in self.report_rows]
        cuda_opt = [r["cuda_optimised_ms"] for r in self.report_rows]

        self.ax_rep.plot(grids, ser_times, label="Serial CPU (ms)", color='#3b82f6', marker='o', linewidth=2.5)
        self.ax_rep.plot(grids, omp_times, label="OpenMP CPU (ms)", color='#f97316', marker='s', linewidth=2.5)
        self.ax_rep.plot(grids, cuda_orig, label="CUDA Original (ms)", color='#94a3b8', marker='^', linewidth=2.0)
        self.ax_rep.plot(grids, cuda_opt, label="CUDA Optimised (ms)", color='#eab308', marker='D', linewidth=2.5)

        self.ax_rep.set_title("Execution time for 100 generations across the four implementations", color="#f8fafc", fontsize=13, pad=12)
        self.ax_rep.set_xlabel("Grid Size", color="#cbd5e1", fontsize=11)
        self.ax_rep.set_ylabel("Execution Time (ms)", color="#cbd5e1", fontsize=11)
        
        if self.check_log_scale.isChecked():
            self.ax_rep.set_yscale('log')
            self.ax_rep.set_ylabel("Execution Time (ms, Log Scale)", color="#cbd5e1", fontsize=11)

        self.ax_rep.grid(True, linestyle='--', alpha=0.25, color='#475569')
        self.ax_rep.legend(loc='upper left', framealpha=0.8, facecolor='#111827', edgecolor='#334155')
        plt.setp(self.ax_rep.get_xticklabels(), color='#cbd5e1')
        plt.setp(self.ax_rep.get_yticklabels(), color='#cbd5e1')

        self.figure_rep.tight_layout()
        self.canvas_rep.draw()

    def copy_markdown_tables(self):
        md = report_data.generate_markdown_report()
        clipboard = QApplication.clipboard()
        clipboard.setText(md)
        QMessageBox.information(self, "Copied", "All report benchmark tables copied to clipboard as Markdown!")

    def export_report_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Report Tables", "hpc_benchmark_report_tables.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["=== TABLE 3: ALL IMPLEMENTATIONS COMPARISON ==="])
            writer.writerow(["Grid Size", "Cells", "Serial CPU (ms)", "OpenMP CPU (ms)", "CUDA Original (ms)", "CUDA Optimised (ms)"])
            for r in self.report_rows:
                writer.writerow([r["grid"], r["cells"], r["serial_cpu_ms"], r["openmp_cpu_ms"], r["cuda_original_ms"], r["cuda_optimised_ms"]])
            
            writer.writerow([])
            writer.writerow(["=== TABLE 4: SPEED-UP RATIOS ==="])
            writer.writerow(["Grid Size", "OpenMP vs Serial", "CUDA Optimised vs Serial", "CUDA Optimised vs OpenMP"])
            for r in self.report_rows:
                writer.writerow([r["grid"], f"{r['speedup_openmp_vs_serial']:.2f}", f"{r['speedup_cuda_opt_vs_serial']:.2f}", f"{r['speedup_cuda_opt_vs_openmp']:.2f}"])
            
            writer.writerow([])
            writer.writerow(["=== SECTION 7.2 TRANSFER OVERHEAD ==="])
            writer.writerow(["Grid Size", "Transfer Overhead (ms)", "Compute Time (ms)", "Transfer vs Compute Ratio"])
            for k, v in report_data.REPORT_TRANSFER_BENCHMARK.items():
                writer.writerow([k, v["transfer_overhead_ms"], v["compute_time_ms"], v["ratio_transfer_to_compute"]])

        QMessageBox.information(self, "Export Successful", f"Report tables exported to:\n{path}")

    def start_live_suite(self):
        reply = QMessageBox.question(
            self,
            "Run Live Benchmark Suite",
            "This will execute all 4 engines across all 6 grid resolutions (256² to 4096²) for 100 generations each on your hardware.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        self.suite_dialog = QDialog(self)
        self.suite_dialog.setWindowTitle("Executing HPC Benchmark Suite...")
        self.suite_dialog.resize(450, 150)
        self.suite_dialog.setStyleSheet("background-color: #0b0f19; color: #f1f5f9;")
        d_layout = QVBoxLayout(self.suite_dialog)

        self.lbl_suite_status = QLabel("Initializing benchmark suite...")
        self.lbl_suite_status.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 13px;")
        d_layout.addWidget(self.lbl_suite_status)

        self.suite_prog = QProgressBar()
        self.suite_prog.setRange(0, 100)
        self.suite_prog.setValue(0)
        self.suite_prog.setStyleSheet("""
            QProgressBar {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
                border-radius: 5px;
            }
        """)
        d_layout.addWidget(self.suite_prog)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.suite_dialog.reject)
        d_layout.addWidget(btn_cancel)

        self.suite_worker = LiveSuiteWorker()
        self.suite_worker.progress.connect(self._on_suite_progress)
        self.suite_worker.suite_done.connect(self._on_suite_done)
        self.suite_dialog.finished.connect(self._on_suite_dialog_closed)
        self.suite_worker.start()
        self.suite_dialog.exec_()

    def _on_suite_progress(self, val, msg):
        if hasattr(self, 'suite_prog'):
            self.suite_prog.setValue(val)
        if hasattr(self, 'lbl_suite_status'):
            self.lbl_suite_status.setText(msg)

    def _on_suite_done(self, new_rows):
        self.report_rows = new_rows
        self.populate_report_tables()
        self.draw_report_chart()
        if hasattr(self, 'suite_dialog') and self.suite_dialog.isVisible():
            self.suite_dialog.accept()
        QMessageBox.information(self, "Benchmark Finished", "Live benchmark suite completed! Tables and chart updated with newly measured hardware results.")

    def _on_suite_dialog_closed(self, result):
        if hasattr(self, 'suite_worker') and self.suite_worker.isRunning():
            self.suite_worker.terminate()
            self.suite_worker.wait()

    def export_report_chart_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "figure_1_comparison.png", "PNG Images (*.png)")
        if path:
            self.figure_rep.savefig(path, facecolor=self.figure_rep.get_facecolor(), dpi=300)
            QMessageBox.information(self, "Export", "Report chart saved successfully!")

    def refresh(self):
        self.refresh_custom_log()

    def refresh_custom_log(self):
        self.data = []
        if os.path.exists(benchmark_logger.LOG_FILE):
            with open(benchmark_logger.LOG_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.data.append(row)
        
        self.label_status.setText(f"Status: {len(self.data)} entries loaded")
        self.draw_custom_chart()

    def draw_custom_chart(self):
        self.ax_custom.clear()
        if not self.data:
            self.ax_custom.text(0.5, 0.5, "No logged benchmark data available", ha='center', va='center', color='white', transform=self.ax_custom.transAxes)
            self.canvas_custom.draw()
            return
            
        chart_type = self.combo_type.currentText()
        x_axis_mode = self.combo_x.currentText()
        y_axis_mode = self.combo_y.currentText()
        
        grouped = defaultdict(list)
        for row in self.data:
            m = row['method']
            if self.method_checkboxes.get(m) and self.method_checkboxes[m].isChecked():
                grouped[m].append(row)
                
        for method, rows in grouped.items():
            x_vals = []
            y_vals = []
            for row in rows:
                if x_axis_mode == "Grid Size (rows×cols)":
                    val = f"{row['grid_rows']}×{row['grid_cols']}"
                elif x_axis_mode == "Steps":
                    val = int(row['steps'])
                else:
                    val = row['timestamp']
                x_vals.append(val)
                
                if y_axis_mode == "Total Time (ms)":
                    y_vals.append(float(row['total_ms']))
                elif y_axis_mode == "Throughput (M cells/s)":
                    try:
                        cells = int(row.get('grid_rows', 1)) * int(row.get('grid_cols', 1))
                        steps = int(row.get('steps', 1))
                        t_ms = float(row.get('total_ms', 1))
                        th = (cells * steps) / (t_ms / 1000.0) / 1e6 if t_ms > 0 else 0
                        y_vals.append(th)
                    except Exception:
                        y_vals.append(0.0)
                else:
                    y_vals.append(float(row['avg_ms_per_step']))
                    
            color = METHOD_COLORS.get(method, '#ffffff')
            display_label = METHOD_LABELS.get(method, method)
            
            if chart_type == "Scatter Plot":
                self.ax_custom.scatter(x_vals, y_vals, label=display_label, color=color, alpha=0.7, s=50)
            elif chart_type == "Line Chart":
                self.ax_custom.plot(x_vals, y_vals, label=display_label, color=color, marker='o', linewidth=2)
            else:
                self.ax_custom.bar(x_vals, y_vals, label=display_label, color=color, alpha=0.5)

        if grouped:
            self.ax_custom.legend(loc='upper left', framealpha=0.8, facecolor='#111827', edgecolor='#334155')
            
        self.ax_custom.set_ylabel(y_axis_mode, color='#cbd5e1')
        self.ax_custom.set_xlabel(x_axis_mode, color='#cbd5e1')
        self.ax_custom.grid(True, linestyle='--', alpha=0.2, color='#4b5563')
        if x_axis_mode != "Steps":
            plt.setp(self.ax_custom.get_xticklabels(), rotation=45, ha='right', color='#cbd5e1')
        plt.setp(self.ax_custom.get_yticklabels(), color='#cbd5e1')
            
        self.figure_custom.tight_layout()
        self.canvas_custom.draw()

    def export_custom_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "PNG Images (*.png)")
        if path:
            self.figure_custom.savefig(path, facecolor=self.figure_custom.get_facecolor(), dpi=300)
            QMessageBox.information(self, "Export", "Chart exported successfully!")
            
    def clear_data(self):
        reply = QMessageBox.question(self, 'Clear Data', 'Are you sure you want to delete all benchmark data?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            benchmark_logger.clear_log()
            self.refresh_custom_log()
