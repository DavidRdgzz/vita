"""Ajustes: API key, perfil/objetivos, hidratacion y datos."""
from __future__ import annotations

import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from .. import config, db, nutrition
from ..widgets import Card, label


def _select_data(combo: QComboBox, value):
    for i in range(combo.count()):
        if combo.itemData(i) == value:
            combo.setCurrentIndex(i)
            return


class SettingsView(QWidget):
    profile_changed = Signal()

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

        root.addWidget(label("Ajustes", "H1"))

        # --- IA ---
        ai_card = Card()
        ai_card.add(label("Conexión con la IA (Google Gemini)", "H2"))
        ai_card.add(label(
            "Pega tu API key gratuita de Google Gemini (se obtiene gratis y sin "
            "tarjeta en aistudio.google.com). Es necesaria para calcular los macros "
            "de los alimentos y para el asistente. Se guarda solo en este equipo.",
            "Muted"))
        key_row = QHBoxLayout()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("AIza...")
        toggle = QPushButton("👁")
        toggle.setFixedWidth(42)
        toggle.clicked.connect(self._toggle_key)
        key_row.addWidget(self.api_key)
        key_row.addWidget(toggle)
        ai_card.v.addLayout(key_row)

        self.model = QLineEdit()
        self.model.setPlaceholderText(config.DEFAULT_MODEL)
        ai_card.add(label("Modelo", "Muted"))
        ai_card.add(self.model)

        save_ai = QPushButton("Guardar conexión")
        save_ai.setObjectName("Primary")
        save_ai.clicked.connect(self._save_ai)
        ai_card.add(save_ai)
        self.ai_status = label("", "Accent")
        ai_card.add(self.ai_status)
        root.addWidget(ai_card)

        # --- Perfil ---
        prof_card = Card()
        prof_card.add(label("Tu perfil y objetivos", "H2"))
        form = QFormLayout()
        form.setSpacing(10)

        self.name = QLineEdit()
        form.addRow("Nombre", self.name)
        self.sex = QComboBox()
        self.sex.addItem("Mujer", "mujer")
        self.sex.addItem("Hombre", "hombre")
        form.addRow("Sexo", self.sex)
        self.age = QSpinBox(); self.age.setRange(12, 100); self.age.setSuffix(" años")
        form.addRow("Edad", self.age)
        self.height = QSpinBox(); self.height.setRange(120, 230); self.height.setSuffix(" cm")
        form.addRow("Altura", self.height)
        self.weight = QDoubleSpinBox(); self.weight.setRange(30, 250)
        self.weight.setDecimals(1); self.weight.setSuffix(" kg")
        form.addRow("Peso", self.weight)
        self.activity = QComboBox()
        for k, v in nutrition.ACTIVITY_LABELS.items():
            self.activity.addItem(v, k)
        form.addRow("Actividad", self.activity)
        self.goal = QComboBox()
        for k, v in nutrition.GOAL_LABELS.items():
            self.goal.addItem(v, k)
        form.addRow("Objetivo", self.goal)
        self.rate = QComboBox()
        for k, v in nutrition.RATE_LABELS.items():
            self.rate.addItem(v, k)
        form.addRow("Ritmo", self.rate)
        self.protein = QDoubleSpinBox()
        self.protein.setRange(1.0, 3.5); self.protein.setDecimals(1)
        self.protein.setSingleStep(0.1); self.protein.setSuffix(" g/kg")
        form.addRow("Proteína", self.protein)
        self.fat = QSpinBox(); self.fat.setRange(15, 45); self.fat.setSuffix(" %")
        form.addRow("Grasa (% kcal)", self.fat)

        wrap = QWidget(); wrap.setLayout(form)
        prof_card.add(wrap)
        save_prof = QPushButton("Guardar y recalcular")
        save_prof.setObjectName("Primary")
        save_prof.clicked.connect(self._save_profile)
        prof_card.add(save_prof)
        self.prof_status = label("", "Accent")
        self.prof_status.setWordWrap(True)
        prof_card.add(self.prof_status)
        root.addWidget(prof_card)

        # --- Agua ---
        water_card = Card()
        water_card.add(label("Objetivo de hidratación", "H2"))
        wr = QHBoxLayout()
        self.water_goal = QSpinBox()
        self.water_goal.setRange(500, 6000); self.water_goal.setSingleStep(250)
        self.water_goal.setSuffix(" ml")
        save_water = QPushButton("Guardar")
        save_water.setObjectName("Primary")
        save_water.clicked.connect(self._save_water)
        wr.addWidget(self.water_goal)
        wr.addWidget(save_water)
        water_card.v.addLayout(wr)
        root.addWidget(water_card)

        # --- Datos ---
        data_card = Card()
        data_card.add(label("Datos", "H2"))
        clear_chat = QPushButton("Borrar historial del chat")
        clear_chat.setObjectName("Danger")
        clear_chat.clicked.connect(self._clear_chat)
        data_card.add(clear_chat)
        self.data_status = label("", "Muted")
        data_card.add(self.data_status)
        root.addWidget(data_card)

        root.addStretch()

    def _toggle_key(self):
        if self.api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key.setEchoMode(QLineEdit.EchoMode.Password)

    def _save_ai(self):
        config.set_value("api_key", self.api_key.text().strip())
        config.set_value("model", self.model.text().strip() or config.DEFAULT_MODEL)
        self.ai_status.setText("Conexión guardada.")

    def _collect_profile(self) -> dict:
        return {
            "name": self.name.text().strip() or "Atleta",
            "sex": self.sex.currentData(),
            "age": self.age.value(),
            "height_cm": float(self.height.value()),
            "weight_kg": float(self.weight.value()),
            "activity": self.activity.currentData(),
            "goal": self.goal.currentData(),
            "rate": int(self.rate.currentData()),
            "protein_per_kg": self.protein.value(),
            "fat_pct": self.fat.value() / 100.0,
        }

    def _save_profile(self):
        data = self._collect_profile()
        db.save_profile(data)
        t = nutrition.compute_targets(data)
        self.prof_status.setText(
            f"Guardado. Nuevo objetivo: {t['kcal']} kcal · {t['protein']}g P · "
            f"{t['carbs']}g C · {t['fat']}g G"
        )
        self.profile_changed.emit()

    def _save_water(self):
        config.set_value("water_goal_ml", self.water_goal.value())
        self.profile_changed.emit()

    def _clear_chat(self):
        db.clear_chat()
        self.data_status.setText("Historial del chat borrado.")

    def refresh(self):
        cfg = config.load_config()
        self.api_key.setText(cfg.get("api_key", ""))
        self.model.setText(cfg.get("model", config.DEFAULT_MODEL))
        self.water_goal.setValue(int(cfg.get("water_goal_ml", 2500)))
        if not cfg.get("api_key") and os.environ.get("GEMINI_API_KEY"):
            self.ai_status.setText("Usando la API key de la variable de entorno.")

        p = db.get_profile()
        if p:
            self.name.setText(p["name"])
            _select_data(self.sex, p["sex"])
            self.age.setValue(p["age"])
            self.height.setValue(int(p["height_cm"]))
            self.weight.setValue(p["weight_kg"])
            _select_data(self.activity, p["activity"])
            _select_data(self.goal, p["goal"])
            _select_data(self.rate, p["rate"])
            self.protein.setValue(p["protein_per_kg"])
            self.fat.setValue(int(round(p["fat_pct"] * 100)))
