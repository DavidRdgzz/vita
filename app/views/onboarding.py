"""Pantalla de bienvenida: recoge los datos para calcular las necesidades."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from .. import db, nutrition
from ..widgets import Card, label


class OnboardingView(QWidget):
    completed = Signal()

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
        center = QHBoxLayout(host)
        center.addStretch()

        col = QVBoxLayout()
        col.setContentsMargins(0, 40, 0, 40)
        col.setSpacing(0)
        center.addLayout(col)
        center.addStretch()

        card = Card()
        card.setFixedWidth(520)
        col.addWidget(card)

        card.add(label("Bienvenida a Vita", "H1"))
        sub = label(
            "Hecha con cariño para ti. Rellena tus datos y calculamos "
            "exactamente las calorías y macros que tu cuerpo necesita.",
            "Muted",
        )
        sub.setWordWrap(True)
        card.add(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Tu nombre")
        form.addRow("Nombre", self.name)

        self.sex = QComboBox()
        self.sex.addItem("Mujer", "mujer")
        self.sex.addItem("Hombre", "hombre")
        form.addRow("Sexo", self.sex)

        self.age = QSpinBox()
        self.age.setRange(12, 100)
        self.age.setValue(25)
        self.age.setSuffix(" años")
        form.addRow("Edad", self.age)

        self.height = QSpinBox()
        self.height.setRange(120, 230)
        self.height.setValue(165)
        self.height.setSuffix(" cm")
        form.addRow("Altura", self.height)

        self.weight = QDoubleSpinBox()
        self.weight.setRange(30, 250)
        self.weight.setDecimals(1)
        self.weight.setValue(60.0)
        self.weight.setSuffix(" kg")
        form.addRow("Peso", self.weight)

        self.activity = QComboBox()
        for key, lbl in nutrition.ACTIVITY_LABELS.items():
            self.activity.addItem(lbl, key)
        self.activity.setCurrentIndex(2)
        form.addRow("Actividad", self.activity)

        self.goal = QComboBox()
        for key, lbl in nutrition.GOAL_LABELS.items():
            self.goal.addItem(lbl, key)
        form.addRow("Objetivo", self.goal)

        self.rate = QComboBox()
        for key, lbl in nutrition.RATE_LABELS.items():
            self.rate.addItem(lbl, key)
        self.rate.setCurrentIndex(1)
        form.addRow("Ritmo", self.rate)

        wrap = QWidget()
        wrap.setLayout(form)
        card.add(wrap)

        self.preview = label("", "Accent")
        self.preview.setWordWrap(True)
        card.add(self.preview)

        btn = QPushButton("Empezar")
        btn.setObjectName("Primary")
        btn.setMinimumHeight(44)
        btn.clicked.connect(self._save)
        card.add(btn)

        for w in (self.sex, self.activity, self.goal, self.rate):
            w.currentIndexChanged.connect(self._update_preview)
        for w in (self.age, self.height):
            w.valueChanged.connect(self._update_preview)
        self.weight.valueChanged.connect(self._update_preview)
        self._update_preview()

    def _collect(self) -> dict:
        goal = self.goal.currentData()
        return {
            "name": self.name.text().strip() or "Atleta",
            "sex": self.sex.currentData(),
            "age": self.age.value(),
            "height_cm": float(self.height.value()),
            "weight_kg": float(self.weight.value()),
            "activity": self.activity.currentData(),
            "goal": goal,
            "rate": int(self.rate.currentData()),
            "protein_per_kg": nutrition.DEFAULT_PROTEIN_PER_KG.get(goal, 1.8),
            "fat_pct": 0.27,
        }

    def _update_preview(self):
        t = nutrition.compute_targets(self._collect())
        self.preview.setText(
            f"Tu objetivo: {t['kcal']} kcal/día  ·  {t['protein']}g proteína  ·  "
            f"{t['carbs']}g carbos  ·  {t['fat']}g grasa"
        )

    def _save(self):
        db.save_profile(self._collect())
        self.completed.emit()
