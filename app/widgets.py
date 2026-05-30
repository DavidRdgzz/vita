"""Widgets reutilizables: tarjeta, anillo de progreso y barra de macro."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

from .theme import COLORS


class Card(QFrame):
    """Tarjeta con borde redondeado y layout vertical."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(18, 18, 18, 18)
        self.v.setSpacing(12)

    def add(self, w: QWidget):
        self.v.addWidget(w)
        return w


def label(text: str, kind: str = "") -> QLabel:
    lbl = QLabel(text)
    if kind:
        lbl.setObjectName(kind)
    return lbl


class CircularProgress(QWidget):
    """Anillo de progreso con valor central (usado para las calorias)."""

    def __init__(self, color: str = COLORS["kcal"], parent: QWidget | None = None):
        super().__init__(parent)
        self._value = 0.0
        self._max = 1.0
        self._color = color
        self._caption = "kcal"
        self.setMinimumSize(190, 190)

    def set_values(self, value: float, maximum: float, caption: str = "kcal"):
        self._value = max(0.0, value)
        self._max = max(1.0, maximum)
        self._caption = caption
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        thickness = 16
        side = min(self.width(), self.height())
        margin = thickness / 2 + 4
        rect = QRectF(
            (self.width() - side) / 2 + margin,
            (self.height() - side) / 2 + margin,
            side - 2 * margin,
            side - 2 * margin,
        )

        # Arco de fondo
        pen = QPen(QColor(COLORS["bg2"]))
        pen.setWidth(thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)

        # Arco de progreso
        ratio = min(self._value / self._max, 1.0)
        over = self._value > self._max
        pen.setColor(QColor(COLORS["danger"] if over else self._color))
        p.setPen(pen)
        p.drawArc(rect, 90 * 16, -int(ratio * 360 * 16))

        # Texto central
        p.setPen(QColor(COLORS["danger"] if over else COLORS["text"]))
        f = QFont("Segoe UI", 26, QFont.Weight.Bold)
        p.setFont(f)
        top = QRectF(rect.x(), rect.y() + rect.height() * 0.30,
                     rect.width(), rect.height() * 0.30)
        p.drawText(top, Qt.AlignmentFlag.AlignCenter, f"{self._value:.0f}")

        p.setPen(QColor(COLORS["muted"]))
        p.setFont(QFont("Segoe UI", 10))
        bot = QRectF(rect.x(), rect.y() + rect.height() * 0.52,
                     rect.width(), rect.height() * 0.22)
        p.drawText(bot, Qt.AlignmentFlag.AlignCenter,
                   f"de {self._max:.0f} {self._caption}")


class MacroBar(QWidget):
    """Barra horizontal de un macro con etiqueta y valores."""

    def __init__(self, name: str, color: str, unit: str = "g",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._color = color
        self._unit = unit
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        top = QHBoxLayout()
        self.name = QLabel(name)
        self.name.setStyleSheet("font-weight:600;")
        self.value = QLabel("0 / 0 g")
        self.value.setObjectName("Muted")
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(self.name)
        top.addWidget(self.value)
        lay.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {color}; border-radius:5px; }}"
        )
        lay.addWidget(self.bar)

    def set_values(self, value: float, maximum: float):
        maximum = max(1.0, maximum)
        self.bar.setMaximum(int(maximum))
        self.bar.setValue(int(min(value, maximum)))
        over = value > maximum * 1.05
        color = COLORS["danger"] if over else COLORS["muted"]
        self.value.setStyleSheet(f"color:{color};")
        self.value.setText(f"{value:.0f} / {maximum:.0f} {self._unit}")
