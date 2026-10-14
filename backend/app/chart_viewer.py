import csv
import os
from collections import defaultdict
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QCheckBox, QScrollArea, QMessageBox, QFileDialog
)

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from app import benchmark_logger

METHOD_COLORS = {
    'numba_opt': '#10b981',
    'gpu_opt': '#ec4899',
    'gpu': '#06b6d4',
    'loop': '#ef4444',
    'numpy': '#3b82f6',
    'scipy': '#8b5cf6',
    'numba': '#f59e0b',
    'numba_fast': '#f97316',
}

METHOD_LABELS = {
    'numba_opt': 'CPU (OpenMP)',
    'gpu_opt': 'CUDA Optimised',
    'gpu': 'CUDA Original',
    'loop': 'Serial CPU',
    'numpy': 'CPU (NumPy)',
    'scipy': 'CPU (SciPy)',
    'numba': 'CPU (Numba)',
    'numba_fast': 'CPU (Numba Fast)',
}

class ChartViewer(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benchmark Results Viewer")
        self.resize(1000, 700)
        self.apply_dark_theme()
        
        plt.style.use('dark_background')
        
        self.figure, self.ax = plt.subplots()
        self.figure.patch.set_facecolor('#111827')
        self.ax.set_facecolor('#1f2937')
        self.canvas = FigureCanvas(self.figure)
        
        self.method_checkboxes = {}
        self.setup_ui()
        self.refresh()
        
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { 
                background-color: #0b0f19; 
                color: #e2e8f0; 
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QPushButton { 
                background-color: #1e293b; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                padding: 7px 12px; 
                color: #f1f5f9;
                font-weight: 600;
            }
            QPushButton:hover { 
                background-color: #334155; 
                border-color: #00f0ff;
                color: #ffffff;
            }
            QComboBox { 
                background-color: #0f172a; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                padding: 6px; 
                color: #f1f5f9;
            }
            QComboBox:focus, QComboBox:hover {
                border-color: #00f0ff;
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
                background: #00f0ff;
                border-color: #00f0ff;
            }
        """)

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Sidebar Controls
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        side_layout = QVBoxLayout()
        
        side_layout.addWidget(QLabel("<b>Methods</b>"))
        methods = list(METHOD_COLORS.keys())
        for m in methods:
            cb = QCheckBox(METHOD_LABELS.get(m, m))
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {METHOD_COLORS[m]}; font-weight: bold;")
            cb.stateChanged.connect(self.draw_chart)
            self.method_checkboxes[m] = cb
            side_layout.addWidget(cb)
            
        side_layout.addSpacing(20)
        side_layout.addWidget(QLabel("<b>Chart Type</b>"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Bar Chart", "Line Chart", "Scatter Plot"])
        self.combo_type.currentIndexChanged.connect(self.draw_chart)
        side_layout.addWidget(self.combo_type)
        
        side_layout.addSpacing(10)
        side_layout.addWidget(QLabel("<b>X-Axis</b>"))
        self.combo_x = QComboBox()
        self.combo_x.addItems(["Grid Size (rows×cols)", "Steps", "Timestamp"])
        self.combo_x.currentIndexChanged.connect(self.draw_chart)
        side_layout.addWidget(self.combo_x)
        
        side_layout.addSpacing(10)
        side_layout.addWidget(QLabel("<b>Y-Axis</b>"))
        self.combo_y = QComboBox()
        self.combo_y.addItems(["Total Time (ms)", "Avg ms/step", "Throughput (M cells/s)"])
        self.combo_y.currentIndexChanged.connect(self.draw_chart)
        side_layout.addWidget(self.combo_y)
        
        side_layout.addStretch()
        
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.refresh)
        side_layout.addWidget(btn_refresh)
        
        btn_export = QPushButton("💾 Export PNG")
        btn_export.clicked.connect(self.export_png)
        side_layout.addWidget(btn_export)
        
        btn_clear = QPushButton("🗑 Clear Data")
        btn_clear.clicked.connect(self.clear_data)
        btn_clear.setStyleSheet("background-color: #991b1b; color: white;")
        side_layout.addWidget(btn_clear)
        
        self.label_status = QLabel("")
        side_layout.addWidget(self.label_status)
        
        sidebar.setLayout(side_layout)
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.canvas, stretch=1)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh(self):
        self.data = []
        if os.path.exists(benchmark_logger.LOG_FILE):
            with open(benchmark_logger.LOG_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.data.append(row)
        
        self.label_status.setText(f"Status: {len(self.data)} entries loaded")
        self.draw_chart()
        
    def draw_chart(self):
        self.ax.clear()
        
        if not self.data:
            self.ax.text(0.5, 0.5, "No data available", ha='center', va='center', color='white', transform=self.ax.transAxes)
            self.canvas.draw()
            return
            
        chart_type = self.combo_type.currentText()
        x_axis_mode = self.combo_x.currentText()
        y_axis_mode = self.combo_y.currentText()
        
        # Group data by method
        grouped = defaultdict(list)
        for row in self.data:
            m = row['method']
            if self.method_checkboxes.get(m) and self.method_checkboxes[m].isChecked():
                grouped[m].append(row)
                
        for method, rows in grouped.items():
            # Extract X and Y
            x_vals = []
            y_vals = []
            
            for row in rows:
                if x_axis_mode == "Grid Size (rows×cols)":
                    val = f"{row['grid_rows']}x{row['grid_cols']}"
                elif x_axis_mode == "Steps":
                    val = int(row['steps'])
                else: # Timestamp
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
            
            # Sort chronologically or numerically if possible
            if x_axis_mode != "Timestamp":
                # For categorical X like Grid Size, plotting as line might be weird without sorting
                pass
                
            if chart_type == "Scatter Plot":
                self.ax.scatter(x_vals, y_vals, label=display_label, color=color, alpha=0.7, s=50)
            elif chart_type == "Line Chart":
                # Only makes sense if X is sortable, but let's just plot
                self.ax.plot(x_vals, y_vals, label=display_label, color=color, marker='o', linewidth=2)
            else: # Bar Chart
                # Grouped bar chart requires calculating offsets, but for simplicity
                # we can just use scatter/line or unaligned bars.
                # Actually, simple bars can overlap. For robustness:
                self.ax.bar(x_vals, y_vals, label=display_label, color=color, alpha=0.5)

        if grouped:
            self.ax.legend()
            
        self.ax.set_ylabel(y_axis_mode)
        self.ax.set_xlabel(x_axis_mode)
        self.ax.grid(True, linestyle='--', alpha=0.2, color='#4b5563')
        
        # Rotate x labels if they are strings (like timestamp or grid size)
        if x_axis_mode != "Steps":
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "PNG Images (*.png)")
        if path:
            self.figure.savefig(path, facecolor=self.figure.get_facecolor(), dpi=300)
            QMessageBox.information(self, "Export", "Chart exported successfully!")
            
    def clear_data(self):
        reply = QMessageBox.question(self, 'Clear Data', 'Are you sure you want to delete all benchmark data?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            benchmark_logger.clear_log()
            self.refresh()
