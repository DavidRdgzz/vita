"""Panel de inicio: resumen del dia (calorias, macros, plan, agua)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from .. import config, db, nutrition
from ..theme import COLORS
from ..util import format_date_es
from ..widgets import Card, CircularProgress, MacroBar, label


class DashboardView(QWidget):
    go_diary = Signal()

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
        root.setSpacing(18)

        # Cabecera
        head = QVBoxLayout()
        head.setSpacing(2)
        self.greeting = label("", "H1")
        self.date_lbl = label(format_date_es(self._today), "Muted")
        head.addWidget(self.greeting)
        head.addWidget(self.date_lbl)
        root.addLayout(head)

        # Fila: calorias + macros
        row1 = QHBoxLayout()
        row1.setSpacing(18)
        root.addLayout(row1)

        cal_card = Card()
        cal_card.add(label("Calorías", "H2"))
        self.ring = CircularProgress(COLORS["kcal"])
        ring_wrap = QHBoxLayout()
        ring_wrap.addStretch()
        ring_wrap.addWidget(self.ring)
        ring_wrap.addStretch()
        cal_card.v.addLayout(ring_wrap)
        self.remaining = label("", "Muted")
        self.remaining.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cal_card.add(self.remaining)
        row1.addWidget(cal_card, 1)

        macro_card = Card()
        macro_card.add(label("Macros de hoy", "H2"))
        self.bar_protein = MacroBar("Proteína", COLORS["protein"])
        self.bar_carbs = MacroBar("Carbohidratos", COLORS["carbs"])
        self.bar_fat = MacroBar("Grasa", COLORS["fat"])
        for b in (self.bar_protein, self.bar_carbs, self.bar_fat):
            macro_card.add(b)
        macro_card.v.addStretch()
        add_btn = QPushButton("+ Registrar comida")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self.go_diary.emit)
        macro_card.add(add_btn)
        row1.addWidget(macro_card, 1)

        # Fila: plan + agua
        row2 = QHBoxLayout()
        row2.setSpacing(18)
        root.addLayout(row2)

        self.plan_card = Card()
        self.plan_card.add(label("Tu plan", "H2"))
        self.plan_goal = label("", "Accent")
        self.plan_detail = label("", "Muted")
        self.plan_detail.setWordWrap(True)
        self.plan_card.add(self.plan_goal)
        self.plan_card.add(self.plan_detail)
        self.plan_card.v.addStretch()
        row2.addWidget(self.plan_card, 2)

        water_card = Card()
        water_card.add(label("Agua", "H2"))
        self.water_lbl = label("", "Muted")
        self.water_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.water_bar = QProgressBar()
        self.water_bar.setTextVisible(False)
        self.water_bar.setFixedHeight(10)
        self.water_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {COLORS['water']}; border-radius:5px; }}"
        )
        water_card.add(self.water_lbl)
        water_card.add(self.water_bar)
        wbtns = QHBoxLayout()
        minus = QPushButton("-250 ml")
        plus = QPushButton("+250 ml")
        plus.setObjectName("Primary")
        minus.clicked.connect(lambda: self._water(-250))
        plus.clicked.connect(lambda: self._water(250))
        wbtns.addWidget(minus)
        wbtns.addWidget(plus)
        water_card.v.addLayout(wbtns)
        water_card.v.addStretch()
        row2.addWidget(water_card, 1)

        root.addStretch()

    def _water(self, ml: int):
        db.add_water(self._today, ml)
        self.refresh()

    def refresh(self):
        profile = db.get_profile()
        if not profile:
            return
        self._today = db.today()
        self.date_lbl.setText(format_date_es(self._today))
        self.greeting.setText(f"Hola, {profile['name']}")

        t = nutrition.compute_targets(profile)
        tot = db.day_totals(self._today)

        self.ring.set_values(tot["kcal"], t["kcal"])
        rem = t["kcal"] - tot["kcal"]
        if rem >= 0:
            self.remaining.setText(f"Te quedan {rem:.0f} kcal")
        else:
            self.remaining.setText(f"Te has pasado {abs(rem):.0f} kcal")

        self.bar_protein.set_values(tot["protein"], t["protein"])
        self.bar_carbs.set_values(tot["carbs"], t["carbs"])
        self.bar_fat.set_values(tot["fat"], t["fat"])

        self.plan_goal.setText(nutrition.GOAL_LABELS.get(profile["goal"], ""))
        self.plan_detail.setText(
            f"Metabolismo basal: {t['bmr']} kcal\n"
            f"Gasto diario (TDEE): {t['tdee']} kcal\n"
            f"Objetivo calórico: {t['kcal']} kcal ({nutrition.RATE_LABELS.get(profile['rate'], '')})\n"
            f"Proteína objetivo: {profile['protein_per_kg']:.1f} g/kg"
        )

        goal_ml = config.get("water_goal_ml", 2500)
        water = db.get_water(self._today)
        self.water_bar.setMaximum(int(goal_ml))
        self.water_bar.setValue(int(min(water, goal_ml)))
        self.water_lbl.setText(f"{water:.0f} / {goal_ml:.0f} ml")
