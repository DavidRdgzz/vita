"""Diario de comidas: anadir/quitar alimentos por comida y fecha."""
from __future__ import annotations

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .. import ai, db
from ..theme import COLORS
from ..widgets import Card, label
from ..workers import run_async


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()


class AddFoodDialog(QDialog):
    """Pide un alimento, consulta sus macros a la IA y deja anadirlo."""

    def __init__(self, meal: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Añadir a {meal}")
        self.setMinimumWidth(420)
        self.setObjectName("Root")
        self._macros: dict | None = None
        self.result_data: dict | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lay.addWidget(label(f"Añadir a {meal}", "H2"))

        search_row = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Ej: pechuga de pollo, manzana, arroz...")
        self.name.returnPressed.connect(self._search)
        self.name.textChanged.connect(self._invalidate)
        self.search_btn = QPushButton("Buscar")
        self.search_btn.setObjectName("Primary")
        self.search_btn.clicked.connect(self._search)
        search_row.addWidget(self.name)
        search_row.addWidget(self.search_btn)
        lay.addLayout(search_row)

        self.status = label("Escribe un alimento y pulsa Buscar.", "Muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        self.info = label("", "Accent")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)

        qty_row = QHBoxLayout()
        self.qty = QDoubleSpinBox()
        self.qty.setRange(1, 5000)
        self.qty.setValue(100)
        self.qty.setEnabled(False)
        self.qty.valueChanged.connect(self._update_preview)
        self.mode = QComboBox()
        self.mode.setEnabled(False)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        qty_row.addWidget(self.qty, 2)
        qty_row.addWidget(self.mode, 1)
        lay.addLayout(qty_row)

        self.preview = label("", "H2")
        self.preview.setWordWrap(True)
        lay.addWidget(self.preview)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        self.add_btn = QPushButton("Añadir")
        self.add_btn.setObjectName("Primary")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self._accept)
        btns.addWidget(cancel)
        btns.addWidget(self.add_btn)
        lay.addLayout(btns)

    def _invalidate(self):
        self._macros = None
        self.add_btn.setEnabled(False)
        self.qty.setEnabled(False)
        self.mode.setEnabled(False)
        self.info.setText("")
        self.preview.setText("")

    def _search(self):
        name = self.name.text().strip()
        if not name:
            return
        self.search_btn.setEnabled(False)
        self.status.setText("Consultando a la IA...")
        run_async(ai.get_macros, self._on_found, self._on_error, name)

    def _on_found(self, data: dict):
        self.search_btn.setEnabled(True)
        self._macros = data
        src = "guardado" if data.get("from_cache") else "vía IA"
        self.status.setText(f"Encontrado ({src}).")
        self.info.setText(
            f"Por 100 g: {data['kcal100']:.0f} kcal · {data['protein100']:.0f}g P · "
            f"{data['carbs100']:.0f}g C · {data['fat100']:.0f}g G"
        )
        self.mode.blockSignals(True)
        self.mode.clear()
        self.mode.addItem("gramos (g)", None)
        if data.get("grams_per_unit"):
            unit = data.get("unit_name") or "unidad"
            self.mode.addItem(f"{unit} (~{data['grams_per_unit']:.0f} g)",
                              data["grams_per_unit"])
        self.mode.blockSignals(False)
        self.qty.setEnabled(True)
        self.mode.setEnabled(True)
        self.qty.setValue(100)
        self.add_btn.setEnabled(True)
        self._update_preview()

    def _on_error(self, msg: str):
        self.search_btn.setEnabled(True)
        self.status.setStyleSheet(f"color:{COLORS['danger']};")
        self.status.setText(msg)

    def _mode_changed(self):
        if self.mode.currentData() is None:
            self.qty.setValue(100)
            self.qty.setSingleStep(10)
            self.qty.setSuffix("")
        else:
            self.qty.setValue(1)
            self.qty.setSingleStep(1)
            self.qty.setSuffix(" u")
        self._update_preview()

    def _grams(self) -> float:
        factor = self.mode.currentData()
        if factor is None:
            return self.qty.value()
        return self.qty.value() * float(factor)

    def _scaled(self) -> dict:
        g = self._grams()
        m = self._macros
        f = g / 100.0
        return {
            "grams": g,
            "kcal": m["kcal100"] * f,
            "protein": m["protein100"] * f,
            "carbs": m["carbs100"] * f,
            "fat": m["fat100"] * f,
        }

    def _update_preview(self):
        if not self._macros:
            return
        s = self._scaled()
        self.preview.setText(
            f"{s['grams']:.0f} g  →  {s['kcal']:.0f} kcal · {s['protein']:.0f}g P · "
            f"{s['carbs']:.0f}g C · {s['fat']:.0f}g G"
        )

    def _accept(self):
        if not self._macros:
            return
        s = self._scaled()
        self.result_data = {"name": self._macros["name"], **s}
        self.accept()


class DiaryView(QWidget):
    data_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Root")
        self._boxes: dict[str, dict] = {}

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

        head = QHBoxLayout()
        head.addWidget(label("Diario", "H1"))
        head.addStretch()
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.dateChanged.connect(self.refresh)
        head.addWidget(self.date_edit)
        root.addLayout(head)

        for meal in db.MEALS:
            card = Card()
            header = QHBoxLayout()
            header.addWidget(label(meal, "H2"))
            header.addStretch()
            total = label("0 kcal", "Muted")
            header.addWidget(total)
            card.v.addLayout(header)

            items = QVBoxLayout()
            items.setSpacing(8)
            card.v.addLayout(items)

            add = QPushButton(f"+ Añadir a {meal}")
            add.clicked.connect(lambda _=False, m=meal: self._add(m))
            card.add(add)

            root.addWidget(card)
            self._boxes[meal] = {"items": items, "total": total}

        root.addStretch()

    def _current_day(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    def _add(self, meal: str):
        dlg = AddFoodDialog(meal, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            d = dlg.result_data
            db.add_food(self._current_day(), meal, d["name"], d["grams"],
                        d["kcal"], d["protein"], d["carbs"], d["fat"])
            self.refresh()
            self.data_changed.emit()

    def _make_row(self, food: dict) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        left = QVBoxLayout()
        left.setSpacing(0)
        name = QLabel(f"{food['name'].capitalize()}  ·  {food['grams']:.0f} g")
        name.setStyleSheet("font-weight:600;")
        macros = QLabel(
            f"{food['kcal']:.0f} kcal · {food['protein']:.0f}P "
            f"{food['carbs']:.0f}C {food['fat']:.0f}G"
        )
        macros.setObjectName("Muted")
        left.addWidget(name)
        left.addWidget(macros)
        h.addLayout(left)
        h.addStretch()
        rm = QPushButton("✕")
        rm.setObjectName("Ghost")
        rm.setFixedWidth(34)
        rm.clicked.connect(lambda _=False, fid=food["id"]: self._remove(fid))
        h.addWidget(rm)
        return row

    def _remove(self, food_id: int):
        db.delete_food(food_id)
        self.refresh()
        self.data_changed.emit()

    def refresh(self):
        day = self._current_day()
        foods = db.foods_for_day(day)
        by_meal: dict[str, list] = {m: [] for m in db.MEALS}
        for f in foods:
            by_meal.setdefault(f["meal"], []).append(f)

        for meal, box in self._boxes.items():
            _clear_layout(box["items"])
            meal_foods = by_meal.get(meal, [])
            if not meal_foods:
                empty = label("Sin alimentos todavía.", "Muted")
                box["items"].addWidget(empty)
                box["total"].setText("0 kcal")
                continue
            kcal = 0.0
            for food in meal_foods:
                box["items"].addWidget(self._make_row(food))
                kcal += food["kcal"]
            box["total"].setText(f"{kcal:.0f} kcal")
