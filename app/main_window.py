"""Ventana principal: navegacion lateral y enrutado de vistas."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QListWidget, QMainWindow, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from . import APP_NAME, APP_VERSION, db, updater
from .theme import COLORS
from .views.chat import ChatView
from .views.dashboard import DashboardView
from .views.diary import DiaryView
from .views.history import HistoryView
from .views.onboarding import OnboardingView
from .views.progress import ProgressView
from .views.settings import SettingsView
from .widgets import label
from .workers import run_async

NAV_ITEMS = [
    "🏠  Inicio",
    "🍽  Diario",
    "📊  Historial",
    "📈  Progreso",
    "💬  Asistente",
    "⚙  Ajustes",
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1060, 730)
        self.setMinimumSize(900, 600)

        self._update_info: dict | None = None
        self.root_stack = QStackedWidget()

        # Banner de actualizacion (oculto) encima de toda la app
        container = QWidget()
        container.setObjectName("Root")
        cv = QVBoxLayout(container)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        self.update_banner = self._build_update_banner()
        cv.addWidget(self.update_banner)
        cv.addWidget(self.root_stack, 1)
        self.setCentralWidget(container)

        # Pantalla de bienvenida
        self.onboarding = OnboardingView()
        self.onboarding.completed.connect(self._finish_onboarding)
        self.root_stack.addWidget(self.onboarding)

        # App principal
        self.root_stack.addWidget(self._build_main())

        if db.has_profile():
            self.root_stack.setCurrentIndex(1)
            self.nav.setCurrentRow(0)
        else:
            self.root_stack.setCurrentIndex(0)

        # Solo la version empaquetada puede autoactualizarse.
        if updater.current_exe():
            run_async(updater.check, self._on_update_found, lambda _e: None)

    def _build_main(self) -> QWidget:
        main = QWidget()
        main.setObjectName("Root")
        layout = QHBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(212)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(0, 22, 0, 16)
        sv.setSpacing(8)

        logo = label(f"❤  {APP_NAME}", "H2")
        logo.setStyleSheet("padding: 0 20px 8px 20px; font-size:22px;")
        sv.addWidget(logo)

        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.addItems(NAV_ITEMS)
        self.nav.currentRowChanged.connect(self._navigate)
        sv.addWidget(self.nav, 1)

        footer = label(f"v{APP_VERSION}", "Muted")
        footer.setStyleSheet("padding: 0 20px; font-size:11px;")
        sv.addWidget(footer)
        layout.addWidget(sidebar)

        # Vistas
        self.stack = QStackedWidget()
        self.dashboard = DashboardView()
        self.diary = DiaryView()
        self.history = HistoryView()
        self.progress = ProgressView()
        self.chat = ChatView()
        self.settings = SettingsView()
        self.views = [
            self.dashboard, self.diary, self.history,
            self.progress, self.chat, self.settings,
        ]
        for v in self.views:
            self.stack.addWidget(v)
        layout.addWidget(self.stack, 1)

        # Conexiones entre vistas
        self.dashboard.go_diary.connect(lambda: self.nav.setCurrentRow(1))
        self.diary.data_changed.connect(self.dashboard.refresh)
        self.progress.data_changed.connect(self.dashboard.refresh)
        self.settings.profile_changed.connect(self.dashboard.refresh)
        return main

    def _navigate(self, index: int):
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        self.views[index].refresh()

    def _finish_onboarding(self):
        self.settings.refresh()
        self.root_stack.setCurrentIndex(1)
        self.nav.setCurrentRow(0)
        self._navigate(0)

    # --- Auto-actualizacion -------------------------------------------------
    def _build_update_banner(self) -> QWidget:
        banner = QWidget()
        banner.setObjectName("UpdateBanner")
        banner.setStyleSheet(
            f"QWidget#UpdateBanner {{ background: {COLORS['card2']};"
            f" border-bottom: 2px solid {COLORS['accent']}; }}"
        )
        lay = QHBoxLayout(banner)
        lay.setContentsMargins(20, 11, 16, 11)
        lay.setSpacing(12)

        self._update_msg = label("Hay una nueva actualización disponible.", "Accent")
        lay.addWidget(self._update_msg, 1)

        self._update_btn = QPushButton("Actualizar")
        self._update_btn.setObjectName("Primary")
        self._update_btn.clicked.connect(self._start_update)
        lay.addWidget(self._update_btn)

        self._update_later = QPushButton("Ahora no")
        self._update_later.setObjectName("Ghost")
        self._update_later.clicked.connect(banner.hide)
        lay.addWidget(self._update_later)

        banner.hide()
        return banner

    def _on_update_found(self, info: dict | None) -> None:
        if not info:
            return
        self._update_info = info
        self._update_msg.setText(
            f"Hay una nueva versión de {APP_NAME} (v{info['version']}). "
            "¿Quieres actualizar?"
        )
        self.update_banner.show()

    def _start_update(self) -> None:
        if not self._update_info:
            return
        self._update_btn.setEnabled(False)
        self._update_later.setEnabled(False)
        self._update_msg.setText("Descargando la actualización…")
        run_async(
            updater.download,
            self._on_downloaded,
            self._on_update_error,
            self._update_info["url"],
        )

    def _on_downloaded(self, dest: str) -> None:
        self._update_msg.setText("Reiniciando para aplicar la actualización…")
        updater.apply_and_relaunch(dest)
        QApplication.quit()

    def _on_update_error(self, _err: str) -> None:
        self._update_msg.setText("No se pudo actualizar. Inténtalo más tarde.")
        self._update_btn.setEnabled(True)
        self._update_later.setEnabled(True)
