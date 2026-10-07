import numpy as np
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMainWindow, QLabel, QMessageBox, QFrame

from app.worker import SimulationWorker
from app.renderer import GridRenderer
from app.controls import ControlsDock
from app.patterns import parse_rle, tile_pattern, place_pattern_centered, random_fill, PATTERN_LIBRARY
from app.chart_viewer import ChartViewer

class MainWindow(QMainWindow):
    do_step_signal = pyqtSignal(np.ndarray, str)
    do_benchmark_signal = pyqtSignal(np.ndarray, str, int, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conway's Game of Life — Cyber Edition")
        self.resize(1280, 840)
        self.apply_modern_theme()

        self.running = False
        self.generation = 0
        self.step_in_progress = False
        
        self.chart_viewer = None

        self.renderer = GridRenderer()
        self.setCentralWidget(self.renderer)

        self.setup_worker()
        self.setup_dock()
        self.setup_status_bar()

        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.request_step)

        self.renderer.cell_toggled.connect(lambda r, c, v: self.update_alive_count())
        
        # Initial grid
        self.apply_grid(50, 80)

    def apply_modern_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(9, 13, 22))
        palette.setColor(QPalette.WindowText, QColor(241, 245, 249))
        palette.setColor(QPalette.Base, QColor(15, 23, 42))
        palette.setColor(QPalette.AlternateBase, QColor(17, 24, 39))
        palette.setColor(QPalette.ToolTipBase, QColor(15, 23, 42))
        palette.setColor(QPalette.ToolTipText, QColor(241, 245, 249))
        palette.setColor(QPalette.Text, QColor(241, 245, 249))
        palette.setColor(QPalette.Button, QColor(30, 41, 59))
        palette.setColor(QPalette.ButtonText, QColor(241, 245, 249))
        palette.setColor(QPalette.BrightText, QColor(0, 240, 255))
        palette.setColor(QPalette.Highlight, QColor(14, 165, 233))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #070a13;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                font-size: 12px;
            }
            
            /* DOCK WIDGET */
            QDockWidget {
                color: #f8fafc;
                font-weight: 700;
                font-size: 13px;
                titlebar-close-icon: url();
                titlebar-normal-icon: url();
            }
            QDockWidget::title {
                background: #0f172a;
                padding: 8px 12px;
                border-bottom: 1px solid #1e293b;
                letter-spacing: 0.5px;
            }
            
            /* SCROLL AREA & CONTAINER */
            QScrollArea {
                background: #0b0f19;
                border: none;
            }
            QWidget#controlsContainer {
                background: #0b0f19;
            }
            
            /* CARD FRAMES */
            QFrame#cardFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            QLabel#cardHeader {
                color: #f1f5f9;
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 0.3px;
                padding-bottom: 2px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
            
            /* STATUS BADGES */
            QLabel#statusBadgePaused {
                background-color: rgba(239, 68, 68, 0.12);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
                padding: 4px;
                letter-spacing: 1px;
            }
            QLabel#statusBadgeRunning {
                background-color: rgba(16, 185, 129, 0.14);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
                padding: 4px;
                letter-spacing: 1px;
            }

            /* PRIMARY BUTTONS */
            QPushButton#btnPlay {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                color: #ffffff;
                font-weight: 700;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton#btnPlay:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
            }
            QPushButton#btnPause {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #ef4444);
                color: #ffffff;
                font-weight: 700;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton#btnPause:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b91c1c, stop:1 #dc2626);
            }
            QPushButton#btnStep {
                background-color: #1e293b;
                color: #f1f5f9;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 10px;
            }
            QPushButton#btnStep:hover {
                background-color: #334155;
                border-color: #00f0ff;
            }
            QPushButton#btnClear {
                background-color: #1a2234;
                color: #94a3b8;
                font-weight: 500;
                border: 1px solid #283548;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton#btnClear:hover {
                background-color: #273549;
                color: #ef4444;
                border-color: #ef4444;
            }

            /* PRESET & SECONDARY BUTTONS */
            QPushButton#presetBtn {
                background-color: #1a2333;
                color: #94a3b8;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid #273549;
                border-radius: 4px;
                padding: 4px 6px;
            }
            QPushButton#presetBtn:hover {
                background-color: #28374d;
                color: #00f0ff;
                border-color: #00f0ff;
            }
            QPushButton#btnSecondary {
                background-color: #1e293b;
                color: #e2e8f0;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px;
            }
            QPushButton#btnSecondary:hover {
                background-color: #2e3e57;
                border-color: #38bdf8;
                color: #ffffff;
            }
            QPushButton#btnAccent {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #06b6d4);
                color: #ffffff;
                font-weight: 700;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton#btnAccent:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0891b2);
            }

            /* INPUTS & COMBOS */
            QComboBox, QSpinBox, QPlainTextEdit {
                background-color: #0b1120;
                border: 1px solid #243044;
                border-radius: 6px;
                padding: 5px 8px;
                color: #f1f5f9;
                selection-background-color: #0284c7;
            }
            QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover {
                border-color: #3b82f6;
            }
            QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {
                border-color: #00f0ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #0b1120;
                border: 1px solid #334155;
                color: #f1f5f9;
                selection-background-color: #1e293b;
                selection-color: #00f0ff;
                padding: 4px;
            }

            /* SLIDERS */
            QSlider::groove:horizontal {
                height: 6px;
                background: #1e293b;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #00f0ff);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: #ffffff;
                border: 2px solid #0284c7;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #00f0ff;
                border-color: #ffffff;
            }

            /* SCROLLBARS */
            QScrollBar:vertical {
                background: #0b0f19;
                width: 7px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #273549;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3b4e6b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            /* STATUS BAR */
            QStatusBar {
                background: #090d16;
                border-top: 1px solid #1a2234;
                color: #94a3b8;
                padding: 4px;
            }
            QStatusBar QLabel {
                padding: 2px 6px;
                font-size: 11px;
            }
        """)

    def setup_worker(self):
        self.worker_thread = QThread()
        self.worker = SimulationWorker()
        self.worker.moveToThread(self.worker_thread)
        
        self.do_step_signal.connect(self.worker.do_step)
        self.do_benchmark_signal.connect(self.worker.do_benchmark)
        
        self.worker.step_done.connect(self.on_step_done)
        self.worker.benchmark_done.connect(self.on_benchmark_done)
        
        self.worker_thread.start()

    def closeEvent(self, event):
        self.worker_thread.quit()
        self.worker_thread.wait()
        super().closeEvent(event)

    def setup_dock(self):
        self.controls = ControlsDock(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.controls)
        
        # Connect signals
        self.controls.apply_size_requested.connect(self.apply_grid)
        self.controls.clear_grid_requested.connect(self.clear_grid)
        self.controls.speed_changed.connect(self.update_timer)
        self.controls.step_requested.connect(self.single_step)
        self.controls.toggle_run_requested.connect(self.toggle_run)
        self.controls.benchmark_requested.connect(self.run_benchmark)
        self.controls.view_results_requested.connect(self.open_chart_viewer)
        self.controls.pattern_load_requested.connect(self.load_pattern)
        self.controls.theme_changed.connect(self.renderer.set_theme)

    def setup_status_bar(self):
        self.status = self.statusBar()
        
        self.label_status_mode = QLabel("🚀 Engine: Ready")
        self.label_status_mode.setStyleSheet("color: #38bdf8; font-weight: 600;")
        
        self.label_status_gen = QLabel("Gen: 0")
        self.label_status_gen.setStyleSheet("color: #f1f5f9; font-weight: 600;")

        self.label_status_alive = QLabel("Alive: 0")
        self.label_status_alive.setStyleSheet("color: #34d399; font-weight: 600;")

        self.label_status_dim = QLabel("50 × 80")
        self.label_status_dim.setStyleSheet("color: #cbd5e1;")

        self.label_status_vram = QLabel("VRAM: 0.00 GB")
        self.label_status_vram.setStyleSheet("color: #94a3b8;")

        def make_sep():
            sep = QLabel("│")
            sep.setStyleSheet("color: #273549; margin: 0 4px;")
            return sep
        
        self.status.addWidget(self.label_status_mode)
        self.status.addWidget(make_sep())
        self.status.addWidget(self.label_status_gen)
        self.status.addWidget(make_sep())
        self.status.addWidget(self.label_status_alive)
        self.status.addWidget(make_sep())
        self.status.addWidget(self.label_status_dim)
        self.status.addWidget(make_sep())
        self.status.addWidget(self.label_status_vram)

    def update_alive_count(self):
        if self.renderer.grid.size <= 2_000_000:
            alive = int(np.count_nonzero(self.renderer.grid))
            self.label_status_alive.setText(f"Alive: {alive:,}")
        else:
            self.label_status_alive.setText("Alive: [Large Grid]")

    def check_vram(self, rows, cols):
        bytes_needed = rows * cols * 3
        gb = bytes_needed / (1024**3)
        self.label_status_dim.setText(f"{rows:,} × {cols:,}")
        if gb > 10.0:
            self.label_status_vram.setText(f"VRAM Est: {gb:.1f} GB ⚠️")
            self.label_status_vram.setStyleSheet("color: #ef4444; font-weight: bold;")
        else:
            self.label_status_vram.setText(f"VRAM Est: {gb:.2f} GB")
            self.label_status_vram.setStyleSheet("color: #94a3b8;")

    @pyqtSlot(int, int)
    def apply_grid(self, rows, cols):
        self.generation = 0
        self.label_status_gen.setText("Gen: 0")
        self.check_vram(rows, cols)
        
        grid = np.zeros((rows, cols), dtype=np.uint8)
        self.renderer.set_grid(grid)
        self.update_alive_count()
        self.stop_run()

    @pyqtSlot()
    def clear_grid(self):
        self.renderer.grid.fill(0)
        self.renderer.needs_texture_upload = True
        self.renderer.update()
        self.generation = 0
        self.label_status_gen.setText("Gen: 0")
        self.update_alive_count()
        self.stop_run()

    @pyqtSlot(int)
    def update_timer(self, speed_ms):
        if self.running:
            self.sim_timer.setInterval(speed_ms)

    @pyqtSlot()
    def request_step(self):
        if self.step_in_progress:
            return  # Frame drop to prevent flooding
        self.step_in_progress = True
        self.do_step_signal.emit(self.renderer.grid, self.controls.get_current_mode())

    @pyqtSlot()
    def single_step(self):
        self.stop_run()
        self.request_step()

    @pyqtSlot()
    def toggle_run(self):
        if self.running:
            self.stop_run()
        else:
            self.running = True
            self.controls.set_running_state(True)
            self.sim_timer.start(self.controls.get_speed())

    def stop_run(self):
        self.running = False
        self.controls.set_running_state(False)
        self.sim_timer.stop()

    @pyqtSlot(int)
    def run_benchmark(self, steps):
        self.stop_run()
        self.controls.set_benchmark_result("⚡ Running Benchmark...")
        self.step_in_progress = True
        pattern_name = self.controls.get_current_pattern_name()
        self.do_benchmark_signal.emit(self.renderer.grid, self.controls.get_current_mode(), steps, pattern_name)

    @pyqtSlot(np.ndarray, float, str)
    def on_step_done(self, next_grid, duration_ms, mode_used):
        self.renderer.set_grid(next_grid)
        self.generation += 1
        self.label_status_gen.setText(f"Gen: {self.generation:,}")
        self.label_status_mode.setText(f"⚡ {mode_used.upper()}: {duration_ms:.2f} ms")
        self.update_alive_count()
        self.step_in_progress = False

    @pyqtSlot(np.ndarray, float, float, int, str)
    def on_benchmark_done(self, next_grid, total_ms, avg_ms, steps, mode_used):
        if self.controls.check_render_bench.isChecked():
            self.renderer.set_grid(next_grid)
        self.generation += steps
        self.label_status_gen.setText(f"Gen: {self.generation:,}")
        self.update_alive_count()
        res = f"Results: {mode_used.upper()} ({steps} steps) — Total: {total_ms:.1f}ms | Avg: {avg_ms:.3f}ms/step"
        self.controls.set_benchmark_result(res)
        self.label_status_mode.setText(f"Benchmark finished ({mode_used.upper()})")
        self.step_in_progress = False
        
        if self.chart_viewer and self.chart_viewer.isVisible():
            self.chart_viewer.refresh()

    @pyqtSlot()
    def open_chart_viewer(self):
        if not self.chart_viewer:
            self.chart_viewer = ChartViewer(self)
        self.chart_viewer.show()
        self.chart_viewer.raise_()
        self.chart_viewer.activateWindow()

    @pyqtSlot(str, str, float, str)
    def load_pattern(self, val, mode, density, custom_rle):
        if not val:
            return
            
        self.stop_run()
        self.generation = 0
        self.label_status_gen.setText("Gen: 0")
        
        rows = self.controls.spin_rows.value()
        cols = self.controls.spin_cols.value()
        grid = np.zeros((rows, cols), dtype=np.uint8)
        
        if val == "__random__":
            grid = random_fill(grid, density)
        else:
            rle_str = ""
            if val == "__custom__":
                rle_str = custom_rle
            else:
                pat = next((p for p in PATTERN_LIBRARY if p["name"] == val), None)
                if pat:
                    rle_str = pat["rle"]
            
            if not rle_str.strip():
                return
                
            try:
                w, h, cells = parse_rle(rle_str)
                if mode == "tile":
                    grid = tile_pattern(grid, cells, 2, 2)
                else:
                    grid = place_pattern_centered(grid, cells)
            except Exception as e:
                QMessageBox.critical(self, "Parse Error", f"Failed to parse RLE:\n{str(e)}")
                return
                
        if self.controls.check_render_bench.isChecked():
            self.renderer.set_grid(grid)
        else:
            self.renderer.grid = grid
        self.update_alive_count()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle_run()
        elif event.key() == Qt.Key_S:
            self.single_step()
        elif event.key() == Qt.Key_C:
            self.clear_grid()
        elif event.key() == Qt.Key_R:
            # Random fill hotkey
            idx = self.controls.combo_pat.findData("__random__")
            self.controls.combo_pat.setCurrentIndex(idx)
            self.load_pattern("__random__", "center", self.controls.slider_density.value() / 100.0, "")
        else:
            super().keyPressEvent(event)
