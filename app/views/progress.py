"""Progreso: evolucion de peso (grafica) y registro de agua."""
from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDate, QDateTime, QTime, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDoubleSpinBox, QHBoxLayout, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from .. import config, db
from ..theme import COLORS
from ..widgets import Card, label


class ProgressView(QWidget):
    data_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Root")
        self._today = db.today()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        root = QVBoxLayout(host)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)

        root.addWidget(label("Progreso", "H1"))

        # --- Peso ---
        weight_card = Card()
        weight_card.add(label("Peso corporal", "H2"))
        input_row = QHBoxLayout()
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(30, 250)
        self.weight_input.setDecimals(1)
        self.weight_input.setSuffix(" kg")
        save_w = QPushButton("Registrar peso de hoy")
        save_w.setObjectName("Primary")
        save_w.clicked.connect(self._save_weight)
        input_row.addWidget(self.weight_input)
        input_row.addWidget(save_w)
        weight_card.v.addLayout(input_row)

        self.weight_caption = label("", "Muted")
        weight_card.add(self.weight_caption)

        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(240)
        self.chart_view.setStyleSheet("background: transparent; border: none;")
        weight_card.add(self.chart_view)
        root.addWidget(weight_card)

        # --- Agua ---
        water_card = Card()
        water_card.add(label("Hidratación", "H2"))
        self.water_lbl = label("", "Muted")
        self.water_bar = QProgressBar()
        self.water_bar.setTextVisible(False)
        self.water_bar.setFixedHeight(12)
        self.water_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {COLORS['water']}; border-radius:6px; }}"
        )
        water_card.add(self.water_lbl)
        water_card.add(self.water_bar)

        btns = QHBoxLayout()
        for text, ml in [("+250 ml", 250), ("+500 ml", 500), ("-250 ml", -250)]:
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, x=ml: self._water(x))
            btns.addWidget(b)
        reset = QPushButton("Reiniciar")
        reset.setObjectName("Danger")
        reset.clicked.connect(self._reset_water)
        btns.addWidget(reset)
        water_card.v.addLayout(btns)
        root.addWidget(water_card)

        root.addStretch()

    # ---- Peso ----
    def _save_weight(self):
        profile = db.get_profile()
        if not profile:
            return
        profile["weight_kg"] = self.weight_input.value()
        db.save_profile(profile)
        self._build_chart()
        self._refresh_caption(profile)
        self.data_changed.emit()

    def _refresh_caption(self, profile: dict):
        history = db.weight_history()
        if len(history) >= 2:
            diff = history[-1]["weight_kg"] - history[0]["weight_kg"]
            sign = "+" if diff >= 0 else ""
            self.weight_caption.setText(
                f"Peso actual: {profile['weight_kg']:.1f} kg   ·   "
                f"{sign}{diff:.1f} kg desde el inicio del registro"
            )
        else:
            self.weight_caption.setText(f"Peso actual: {profile['weight_kg']:.1f} kg")

    def _build_chart(self):
        history = db.weight_history()
        chart = QChart()
        chart.legend().hide()
        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)

        if not history:
            self.chart_view.setChart(chart)
            return

        series = QLineSeries()
        pen = QPen(QColor(COLORS["accent"]))
        pen.setWidth(3)
        series.setPen(pen)
        series.setPointsVisible(True)

        weights = []
        for entry in history:
            qd = QDate.fromString(entry["day"], "yyyy-MM-dd")
            dt = QDateTime(qd, QTime(12, 0))
            series.append(float(dt.toMSecsSinceEpoch()), entry["weight_kg"])
            weights.append(entry["weight_kg"])

        chart.addSeries(series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd MMM")
        axis_x.setLabelsColor(QColor(COLORS["muted"]))
        axis_x.setGridLineColor(QColor(COLORS["border"]))
        axis_x.setLinePenColor(QColor(COLORS["border"]))
        axis_x.setTickCount(min(6, max(2, len(history))))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        lo, hi = min(weights), max(weights)
        pad = max(1.0, (hi - lo) * 0.2)
        axis_y.setRange(lo - pad, hi + pad)
        axis_y.setLabelFormat("%.1f")
        axis_y.setLabelsColor(QColor(COLORS["muted"]))
        axis_y.setGridLineColor(QColor(COLORS["border"]))
        axis_y.setLinePenColor(QColor(COLORS["border"]))
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self.chart_view.setChart(chart)

    # ---- Agua ----
    def _water(self, ml: int):
        db.add_water(self._today, ml)
        self._refresh_water()
        self.data_changed.emit()

    def _reset_water(self):
        current = db.get_water(self._today)
        db.add_water(self._today, -current)
        self._refresh_water()
        self.data_changed.emit()

    def _refresh_water(self):
        goal = config.get("water_goal_ml", 2500)
        water = db.get_water(self._today)
        self.water_bar.setMaximum(int(goal))
        self.water_bar.setValue(int(min(water, goal)))
        self.water_lbl.setText(f"{water:.0f} / {goal:.0f} ml")

    def refresh(self):
        self._today = db.today()
        profile = db.get_profile()
        if profile:
            self.weight_input.setValue(profile["weight_kg"])
            self._refresh_caption(profile)
        self._build_chart()
        self._refresh_water()
