from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QSpinBox, QSlider, QComboBox, QPlainTextEdit, QDockWidget, QCheckBox,
    QScrollArea, QFrame, QButtonGroup
)

from app.patterns import PATTERN_LIBRARY, PATTERN_CATEGORIES
from app.renderer import COLOR_THEMES

class ControlsDock(QDockWidget):
    # Signals to communicate with MainWindow
    apply_size_requested = pyqtSignal(int, int)  # rows, cols
    clear_grid_requested = pyqtSignal()
    speed_changed = pyqtSignal(int)
    step_requested = pyqtSignal()
    toggle_run_requested = pyqtSignal()
    benchmark_requested = pyqtSignal(int)  # steps
    view_results_requested = pyqtSignal()
    pattern_load_requested = pyqtSignal(str, str, float, str)  # val, mode (tile/center), density, custom_rle
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Control Center", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.setup_ui()

    def _create_card(self, title_text: str, icon: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        header = QLabel(f"{icon} {title_text}" if icon else title_text)
        header.setObjectName("cardHeader")
        card_layout.addWidget(header)
        return card, card_layout

    def setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("controlsContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. SIMULATION CONTROLS CARD
        # -------------------------------------------------------------
        sim_card, sim_layout = self._create_card("Simulation Control", "🕹️")
        
        # State badge
        self.status_badge = QLabel("● PAUSED")
        self.status_badge.setObjectName("statusBadgePaused")
        self.status_badge.setAlignment(Qt.AlignCenter)
        sim_layout.addWidget(self.status_badge)

        # Big Play / Step Row
        btn_action_layout = QHBoxLayout()
        self.btn_run = QPushButton("▶  RUN")
        self.btn_run.setObjectName("btnPlay")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.toggle_run_requested.emit)

        self.btn_step = QPushButton("⏭  STEP")
        self.btn_step.setObjectName("btnStep")
        self.btn_step.setCursor(Qt.PointingHandCursor)
        self.btn_step.clicked.connect(self.step_requested.emit)

        btn_action_layout.addWidget(self.btn_run, stretch=3)
        btn_action_layout.addWidget(self.btn_step, stretch=2)
        sim_layout.addLayout(btn_action_layout)

        # Clear button
        self.btn_clear = QPushButton("🗑  Clear Grid")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_grid_requested.emit)
        sim_layout.addWidget(self.btn_clear)

        # Speed slider & indicator
        speed_header_lay = QHBoxLayout()
        speed_title = QLabel("Speed / Interval:")
        speed_title.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.label_speed = QLabel("100 ms (10 FPS)")
        self.label_speed.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
        speed_header_lay.addWidget(speed_title)
        speed_header_lay.addStretch()
        speed_header_lay.addWidget(self.label_speed)
        sim_layout.addLayout(speed_header_lay)

        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(10, 1000)
        self.slider_speed.setValue(100)
        self.slider_speed.setInvertedAppearance(True)
        self.slider_speed.valueChanged.connect(self._on_speed_changed)
        sim_layout.addWidget(self.slider_speed)

        # Speed presets
        presets_layout = QHBoxLayout()
        presets = [("Slow", 400), ("Normal", 100), ("Fast", 35), ("Turbo", 10)]
        for name, val in presets:
            p_btn = QPushButton(name)
            p_btn.setObjectName("presetBtn")
            p_btn.setCursor(Qt.PointingHandCursor)
            p_btn.clicked.connect(lambda checked, v=val: self.slider_speed.setValue(v))
            presets_layout.addWidget(p_btn)
        sim_layout.addLayout(presets_layout)

        layout.addWidget(sim_card)

        # -------------------------------------------------------------
        # 2. VISUAL THEME CARD
        # -------------------------------------------------------------
        theme_card, theme_layout = self._create_card("Visual Theme", "🎨")
        
        self.combo_theme = QComboBox()
        # Put Monochrome Minimal first (default from Figure 1)
        theme_order = ["classic", "neon_green", "cyberpunk", "matrix", "solar_amber", "synthwave"]
        for key in theme_order:
            if key in COLOR_THEMES:
                self.combo_theme.addItem(COLOR_THEMES[key]["name"], key)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.combo_theme)

        layout.addWidget(theme_card)

        # -------------------------------------------------------------
        # 3. GRID CONFIGURATION CARD
        # -------------------------------------------------------------
        grid_card, grid_layout = self._create_card("Grid Configuration", "📐")

        # Quick size presets
        grid_presets_layout = QGridLayout()
        grid_presets_layout.setSpacing(6)
        grid_presets = [
            ("256×256", 256, 256),
            ("512×512", 512, 512),
            ("1024×1024", 1024, 1024),
            ("1920×1080", 1080, 1920),
            ("2048×2048", 2048, 2048),
            ("4096×4096", 4096, 4096),
        ]
        for idx, (label, r, c) in enumerate(grid_presets):
            g_btn = QPushButton(label)
            g_btn.setObjectName("presetBtn")
            g_btn.setCursor(Qt.PointingHandCursor)
            g_btn.clicked.connect(lambda checked, rows=r, cols=c: self._set_and_apply_size(rows, cols))
            grid_presets_layout.addWidget(g_btn, idx // 2, idx % 2)
        grid_layout.addLayout(grid_presets_layout)

        # Custom inputs
        row_col_lay = QHBoxLayout()
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 100000)
        self.spin_rows.setValue(50)
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 100000)
        self.spin_cols.setValue(80)

        lbl_r = QLabel("Rows:")
        lbl_r.setStyleSheet("color: #94a3b8;")
        lbl_c = QLabel("Cols:")
        lbl_c.setStyleSheet("color: #94a3b8;")

        row_col_lay.addWidget(lbl_r)
        row_col_lay.addWidget(self.spin_rows)
        row_col_lay.addWidget(lbl_c)
        row_col_lay.addWidget(self.spin_cols)
        grid_layout.addLayout(row_col_lay)

        btn_apply = QPushButton("Apply Dimensions")
        btn_apply.setObjectName("btnSecondary")
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.clicked.connect(lambda: self.apply_size_requested.emit(self.spin_rows.value(), self.spin_cols.value()))
        grid_layout.addWidget(btn_apply)

        layout.addWidget(grid_card)

        # -------------------------------------------------------------
        # 4. PATTERN LIBRARY CARD
        # -------------------------------------------------------------
        pat_card, pat_layout = self._create_card("Pattern Library", "🧬")

        self.combo_pat = QComboBox()
        self.combo_pat.addItem("— Select a Pattern —", "")
        self.combo_pat.addItem("🎲 Random Fill", "__random__")
        self.combo_pat.addItem("📝 Custom RLE Code…", "__custom__")
        for cat in PATTERN_CATEGORIES:
            self.combo_pat.insertSeparator(self.combo_pat.count())
            for pat in PATTERN_LIBRARY:
                if pat["category"] == cat:
                    self.combo_pat.addItem(f"{cat}: {pat['name']}", pat["name"])
        pat_layout.addWidget(self.combo_pat)
        self.combo_pat.currentIndexChanged.connect(self.on_pattern_select)

        self.combo_pat_mode = QComboBox()
        self.combo_pat_mode.addItems(["Tile (Fill Entire Grid)", "Center (Single Copy)"])
        pat_layout.addWidget(self.combo_pat_mode)

        # Random Density Widget
        self.slider_density = QSlider(Qt.Horizontal)
        self.slider_density.setRange(5, 80)
        self.slider_density.setValue(20)
        self.label_density = QLabel("20%")
        self.label_density.setStyleSheet("color: #00f0ff; font-weight: bold;")
        self.slider_density.valueChanged.connect(lambda v: self.label_density.setText(f"{v}%"))

        dens_lay = QHBoxLayout()
        dens_title = QLabel("Fill Density:")
        dens_title.setStyleSheet("color: #94a3b8;")
        dens_lay.addWidget(dens_title)
        dens_lay.addWidget(self.slider_density)
        dens_lay.addWidget(self.label_density)
        self.widget_density = QWidget()
        self.widget_density.setLayout(dens_lay)
        pat_layout.addWidget(self.widget_density)
        self.widget_density.hide()

        # Custom RLE Widget
        self.text_rle = QPlainTextEdit()
        self.text_rle.setPlaceholderText("#C My pattern\nx = 3, y = 3, rule = B3/S23\nbob$2bo$3o!")
        self.text_rle.setMaximumHeight(85)
        pat_layout.addWidget(self.text_rle)
        self.text_rle.hide()

        self.label_pat_desc = QLabel("")
        self.label_pat_desc.setWordWrap(True)
        self.label_pat_desc.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        pat_layout.addWidget(self.label_pat_desc)

        btn_load = QPushButton("✨  Load Pattern")
        btn_load.setObjectName("btnAccent")
        btn_load.setCursor(Qt.PointingHandCursor)
        btn_load.clicked.connect(self._on_load_pattern)
        pat_layout.addWidget(btn_load)

        layout.addWidget(pat_card)

        # -------------------------------------------------------------
        # 5. ENGINE & BENCHMARK CARD
        # -------------------------------------------------------------
        bench_card, bench_layout = self._create_card("Compute Engine & Benchmark", "⚡")

        mode_lay = QVBoxLayout()
        lbl_engine = QLabel("Simulation Engine:")
        lbl_engine.setStyleSheet("color: #94a3b8; font-size: 11px;")
        mode_lay.addWidget(lbl_engine)

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("💻 CPU (OpenMP)", "numba_opt")
        self.combo_mode.addItem("⚡ CUDA Optimised", "gpu_opt")
        self.combo_mode.addItem("🟢 CUDA Original", "gpu")
        self.combo_mode.addItem("🔄 Serial CPU", "loop")
        self.combo_mode.addItem("🚀 CPU (NumPy Vectorized)", "numpy")
        self.combo_mode.addItem("🔬 CPU (SciPy Convolution)", "scipy")
        self.combo_mode.addItem("⚙️ CPU (Numba Multicore)", "numba")
        self.combo_mode.addItem("⚡ CPU (Numba Fast Branching)", "numba_fast")
        mode_lay.addWidget(self.combo_mode)
        bench_layout.addLayout(mode_lay)

        b_lay = QHBoxLayout()
        self.spin_bench = QSpinBox()
        self.spin_bench.setRange(1, 10000)
        self.spin_bench.setValue(100)

        lbl_steps = QLabel("Steps:")
        lbl_steps.setStyleSheet("color: #94a3b8;")
        b_lay.addWidget(lbl_steps)
        b_lay.addWidget(self.spin_bench)

        btn_bench = QPushButton("⚡ Test")
        btn_bench.setObjectName("btnSecondary")
        btn_bench.setCursor(Qt.PointingHandCursor)
        btn_bench.clicked.connect(lambda: self.benchmark_requested.emit(self.spin_bench.value()))
        b_lay.addWidget(btn_bench)
        bench_layout.addLayout(b_lay)

        btn_view_results = QPushButton("📊  View Benchmark Charts")
        btn_view_results.setObjectName("btnSecondary")
        btn_view_results.setCursor(Qt.PointingHandCursor)
        btn_view_results.clicked.connect(self.view_results_requested.emit)
        bench_layout.addWidget(btn_view_results)

        self.check_render_bench = QCheckBox("Render result on screen")
        self.check_render_bench.setChecked(True)
        self.check_render_bench.setStyleSheet("color: #cbd5e1; font-size: 12px; padding: 2px 0;")
        bench_layout.addWidget(self.check_render_bench)

        self.label_bench_res = QLabel("")
        self.label_bench_res.setWordWrap(True)
        self.label_bench_res.setTextFormat(Qt.RichText)
        self.label_bench_res.setStyleSheet("""
            QLabel {
                color: #f1f5f9;
                font-size: 13px;
                padding: 10px 12px;
                background-color: rgba(14, 165, 233, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
            }
        """)
        self.label_bench_res.hide()
        bench_layout.addWidget(self.label_bench_res)

        layout.addWidget(bench_card)
        layout.addStretch()

        scroll.setWidget(container)
        self.setWidget(scroll)

    def _set_and_apply_size(self, rows, cols):
        self.spin_rows.setValue(rows)
        self.spin_cols.setValue(cols)
        self.apply_size_requested.emit(rows, cols)

    def _on_speed_changed(self, v):
        fps = int(1000 / v) if v > 0 else 0
        self.label_speed.setText(f"{v} ms ({fps} FPS)")
        self.speed_changed.emit(v)

    def _on_theme_changed(self):
        theme_key = self.combo_theme.currentData()
        self.theme_changed.emit(theme_key)

    def on_pattern_select(self):
        val = self.combo_pat.currentData()
        self.widget_density.setVisible(val == "__random__")
        self.text_rle.setVisible(val == "__custom__")

        self.label_pat_desc.setText("")
        if val and val not in ("__random__", "__custom__"):
            pat = next((p for p in PATTERN_LIBRARY if p["name"] == val), None)
            if pat:
                self.label_pat_desc.setText(pat.get("description", ""))

    def _on_load_pattern(self):
        val = self.combo_pat.currentData()
        mode = "tile" if self.combo_pat_mode.currentIndex() == 0 else "center"
        density = self.slider_density.value() / 100.0
        custom_rle = self.text_rle.toPlainText()
        self.pattern_load_requested.emit(val or "", mode, density, custom_rle)

    def get_current_mode(self):
        return self.combo_mode.currentData()

    def get_current_pattern_name(self):
        val = self.combo_pat.currentData()
        if not val:
            return "empty"
        elif val == "__random__":
            return f"random_{self.slider_density.value()}%"
        elif val == "__custom__":
            return "custom"
        return val

    def get_speed(self):
        return self.slider_speed.value()

    def set_running_state(self, is_running):
        if is_running:
            self.btn_run.setText("⏸  PAUSE")
            self.btn_run.setObjectName("btnPause")
            self.status_badge.setText("● RUNNING")
            self.status_badge.setObjectName("statusBadgeRunning")
            self.btn_step.setEnabled(False)
        else:
            self.btn_run.setText("▶  RUN")
            self.btn_run.setObjectName("btnPlay")
            self.status_badge.setText("● PAUSED")
            self.status_badge.setObjectName("statusBadgePaused")
            self.btn_step.setEnabled(True)
        # Force re-polish stylesheet
        self.btn_run.style().unpolish(self.btn_run)
        self.btn_run.style().polish(self.btn_run)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def set_benchmark_result(self, res):
        if res:
            self.label_bench_res.setText(res)
            self.label_bench_res.show()
        else:
            self.label_bench_res.hide()
