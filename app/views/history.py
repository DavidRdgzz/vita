"""Historial: dias registrados y medias recientes."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from .. import db, nutrition
from ..util import format_date_es, relative_label
from ..widgets import Card, label


def _clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()


class HistoryView(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Root")

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

        root.addWidget(label("Historial", "H1"))

        self.summary = Card()
        self.summary.add(label("Resumen (últimos 7 días)", "H2"))
        self.summary_text = label("", "Muted")
        self.summary_text.setWordWrap(True)
        self.summary.add(self.summary_text)
        root.addWidget(self.summary)

        self.days_card = Card()
        self.days_card.add(label("Días registrados", "H2"))
        self.days_box = QVBoxLayout()
        self.days_box.setSpacing(6)
        self.days_card.v.addLayout(self.days_box)
        root.addWidget(self.days_card)

        root.addStretch()

    def _row(self, day: dict, target_kcal: int) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 6, 4, 6)
        left = QVBoxLayout()
        left.setSpacing(0)
        title = label(relative_label(day["day"]))
        title.setStyleSheet("font-weight:600;")
        sub = label(format_date_es(day["day"]), "Muted")
        left.addWidget(title)
        left.addWidget(sub)
        h.addLayout(left)
        h.addStretch()

        macros = label(
            f"{day['kcal']:.0f} kcal  ·  {day['protein']:.0f}P "
            f"{day['carbs']:.0f}C {day['fat']:.0f}G"
        )
        if target_kcal:
            diff = day["kcal"] - target_kcal
            sign = "+" if diff >= 0 else ""
            macros.setToolTip(f"{sign}{diff:.0f} kcal respecto al objetivo")
        macros.setAlignment(Qt.AlignmentFlag.AlignRight)
        h.addWidget(macros)
        return row

    def refresh(self):
        profile = db.get_profile()
        target = nutrition.compute_targets(profile)["kcal"] if profile else 0

        days = db.logged_days(30)
        _clear(self.days_box)

        if not days:
            self.days_box.addWidget(label("Aún no has registrado comidas.", "Muted"))
            self.summary_text.setText("Empieza a registrar comidas para ver tu progreso.")
            return

        recent = days[:7]
        n = len(recent)
        avg_kcal = sum(d["kcal"] for d in recent) / n
        avg_p = sum(d["protein"] for d in recent) / n
        avg_c = sum(d["carbs"] for d in recent) / n
        avg_f = sum(d["fat"] for d in recent) / n
        self.summary_text.setText(
            f"Media diaria: {avg_kcal:.0f} kcal · {avg_p:.0f}g proteína · "
            f"{avg_c:.0f}g carbos · {avg_f:.0f}g grasa\n"
            f"Días con registro: {len(days)}"
            + (f"   ·   Objetivo: {target} kcal/día" if target else "")
        )

        for day in days:
            self.days_box.addWidget(self._row(day, target))
