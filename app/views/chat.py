"""Chat con IA: asistente de nutricion + reporte de problemas."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from .. import ai, db
from ..theme import COLORS
from ..widgets import Card, label
from ..workers import run_async


class _AssistantTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[dict] = []
        self._typing: QWidget | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 12, 0, 0)
        root.setSpacing(12)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.msg_box = QVBoxLayout(self.container)
        self.msg_box.setContentsMargins(4, 4, 4, 4)
        self.msg_box.setSpacing(10)
        self.msg_box.addStretch()
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Pregúntame lo que quieras sobre tu dieta...")
        self.input.returnPressed.connect(self._send)
        self.send_btn = QPushButton("Enviar")
        self.send_btn.setObjectName("Primary")
        self.send_btn.clicked.connect(self._send)
        clear = QPushButton("Limpiar")
        clear.setObjectName("Ghost")
        clear.clicked.connect(self._clear)
        row.addWidget(self.input)
        row.addWidget(self.send_btn)
        row.addWidget(clear)
        root.addLayout(row)

    def _bubble(self, role: str, text: str) -> QLabel:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(2, 2, 2, 2)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setMaximumWidth(460)
        if role == "user":
            lbl.setStyleSheet(
                f"background:{COLORS['accent']}; color:white; "
                "border-radius:14px; padding:10px 14px;"
            )
            h.addStretch()
            h.addWidget(lbl)
        else:
            lbl.setStyleSheet(
                f"background:{COLORS['card2']}; border-radius:14px; padding:10px 14px;"
            )
            h.addWidget(lbl)
            h.addStretch()
        self.msg_box.insertWidget(self.msg_box.count() - 1, row)
        QTimer.singleShot(0, self._scroll_bottom)
        return row

    def _scroll_bottom(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._bubble("user", text)
        db.add_chat("user", text)
        prior = list(self._history)
        self._history.append({"role": "user", "content": text})

        self.send_btn.setEnabled(False)
        self.input.setEnabled(False)
        self._typing = self._bubble("assistant", "Escribiendo…")

        profile = db.get_profile()
        run_async(ai.chat, self._on_reply, self._on_error, text, profile, prior)

    def _on_reply(self, reply: str):
        if self._typing:
            self._typing.deleteLater()
            self._typing = None
        self._bubble("assistant", reply)
        db.add_chat("assistant", reply)
        self._history.append({"role": "assistant", "content": reply})
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()

    def _on_error(self, msg: str):
        if self._typing:
            self._typing.deleteLater()
            self._typing = None
        bubble = self._bubble("assistant", f"⚠ {msg}")
        # quitar el ultimo user del contexto para no arrastrar el fallo
        if self._history and self._history[-1]["role"] == "user":
            self._history.pop()
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)

    def _clear(self):
        db.clear_chat()
        self._history.clear()
        while self.msg_box.count() > 1:
            item = self.msg_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load(self):
        if self._history:
            return
        for m in db.chat_history():
            self._history.append({"role": m["role"], "content": m["content"]})
            self._bubble(m["role"], m["content"])
        if not self._history:
            self._bubble(
                "assistant",
                "¡Hola! Soy tu asistente de nutrición. Pregúntame qué cenar, "
                "si vas bien de proteína, ideas de comidas para tu objetivo... "
                "lo que necesites.",
            )


class _ReportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 12, 0, 0)
        root.setSpacing(12)

        form = Card()
        form.add(label("Reportar un problema o idea", "H2"))
        form.add(label(
            "¿Algo no funciona o se te ocurre una mejora? Cuéntamelo y quedará "
            "guardado para mejorar la app.", "Muted"))
        self.kind = QComboBox()
        self.kind.addItems(["Error", "Idea", "Mejora"])
        form.add(self.kind)
        self.message = QPlainTextEdit()
        self.message.setPlaceholderText("Describe el problema o la idea...")
        self.message.setFixedHeight(110)
        form.add(self.message)
        send = QPushButton("Enviar reporte")
        send.setObjectName("Primary")
        send.clicked.connect(self._send)
        form.add(send)
        self.status = label("", "Accent")
        form.add(self.status)
        root.addWidget(form)

        list_card = Card()
        list_card.add(label("Reportes enviados", "H2"))
        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(8)
        list_card.v.addLayout(self.list_box)
        root.addWidget(list_card, 1)

    def _send(self):
        text = self.message.toPlainText().strip()
        if not text:
            self.status.setText("Escribe algo antes de enviar.")
            return
        db.add_report(self.kind.currentText(), text)
        self.message.clear()
        self.status.setText("¡Gracias! Reporte guardado.")
        self.load()

    def load(self):
        while self.list_box.count():
            item = self.list_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        reports = db.get_reports()
        if not reports:
            self.list_box.addWidget(label("Todavía no hay reportes.", "Muted"))
            return
        for r in reports:
            row = QWidget()
            v = QVBoxLayout(row)
            v.setContentsMargins(0, 4, 0, 4)
            v.setSpacing(2)
            head = label(f"[{r['kind']}]  ·  {r['created_at'][:16].replace('T', ' ')}", "Muted")
            body = QLabel(r["message"])
            body.setWordWrap(True)
            v.addWidget(head)
            v.addWidget(body)
            self.list_box.addWidget(row)


class ChatView(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Root")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(12)
        root.addWidget(label("Asistente", "H1"))

        tabs = QTabWidget()
        self.assistant = _AssistantTab()
        self.report = _ReportTab()
        tabs.addTab(self.assistant, "Asistente IA")
        tabs.addTab(self.report, "Reportar problema")
        root.addWidget(tabs, 1)

    def refresh(self):
        self.assistant.load()
        self.report.load()
