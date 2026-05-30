"""Paleta de color y hoja de estilos (QSS)."""
from __future__ import annotations

COLORS = {
    "bg":        "#0F121A",
    "bg2":       "#151926",
    "card":      "#1B2130",
    "card2":     "#212838",
    "hover":     "#28304370",
    "border":    "#2B3346",
    "text":      "#ECEFF6",
    "muted":     "#8A93A8",
    "accent":    "#FF5C8A",   # rosa coral (identidad)
    "accent2":   "#7C6BFF",   # violeta secundario
    "kcal":      "#FF7A66",   # calorias
    "protein":   "#FF5C8A",   # proteina
    "carbs":     "#46B1FF",   # carbohidratos
    "fat":       "#FFC04D",   # grasa
    "water":     "#46B1FF",
    "good":      "#34D399",
    "danger":    "#F46A6A",
}


def stylesheet() -> str:
    c = COLORS
    return f"""
    * {{
        font-family: 'Segoe UI', 'Inter', sans-serif;
        color: {c['text']};
        font-size: 14px;
    }}
    QMainWindow, QWidget#Root {{ background: {c['bg']}; }}
    QWidget {{ background: transparent; }}

    QLabel#H1 {{ font-size: 26px; font-weight: 700; }}
    QLabel#H2 {{ font-size: 19px; font-weight: 600; }}
    QLabel#Muted {{ color: {c['muted']}; }}
    QLabel#Accent {{ color: {c['accent']}; font-weight: 600; }}

    /* Tarjetas */
    QFrame#Card {{
        background: {c['card']};
        border: 1px solid {c['border']};
        border-radius: 16px;
    }}
    QFrame#Card:hover {{ border: 1px solid {c['accent']}55; }}

    /* Sidebar */
    QWidget#Sidebar {{ background: {c['bg2']}; border-right: 1px solid {c['border']}; }}
    QListWidget#Nav {{
        background: transparent; border: none; outline: 0;
        font-size: 15px;
    }}
    QListWidget#Nav::item {{
        padding: 12px 16px; margin: 4px 10px; border-radius: 12px;
        color: {c['muted']};
    }}
    QListWidget#Nav::item:hover {{ background: {c['card']}; color: {c['text']}; }}
    QListWidget#Nav::item:selected {{
        background: {c['accent']}; color: white; font-weight: 600;
    }}

    /* Botones */
    QPushButton {{
        background: {c['card2']};
        border: 1px solid {c['border']};
        border-radius: 11px;
        padding: 9px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {c['card']}; border-color: {c['accent']}66; }}
    QPushButton:pressed {{ background: {c['bg2']}; }}
    QPushButton#Primary {{
        background: {c['accent']}; border: none; color: white;
    }}
    QPushButton#Primary:hover {{ background: #FF74A0; }}
    QPushButton#Primary:pressed {{ background: #E84F7C; }}
    QPushButton#Ghost {{ background: transparent; border: none; color: {c['muted']}; }}
    QPushButton#Ghost:hover {{ color: {c['accent']}; }}
    QPushButton#Danger {{ background: transparent; border: 1px solid {c['danger']}66; color: {c['danger']}; }}
    QPushButton#Danger:hover {{ background: {c['danger']}22; }}

    /* Inputs */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit, QDateEdit {{
        background: {c['bg2']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: 9px 12px;
        selection-background-color: {c['accent']};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
    QPlainTextEdit:focus, QTextEdit:focus, QDateEdit:focus {{
        border: 1px solid {c['accent']};
    }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{
        background: {c['card']}; border: 1px solid {c['border']};
        border-radius: 10px; selection-background-color: {c['accent']};
        padding: 4px;
    }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 18px; }}

    /* Tabs */
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{
        background: transparent; color: {c['muted']};
        padding: 9px 18px; margin-right: 4px;
        border-radius: 10px; font-weight: 600;
    }}
    QTabBar::tab:selected {{ background: {c['card']}; color: {c['accent']}; }}

    /* Barras de progreso */
    QProgressBar {{
        background: {c['bg2']}; border: none; border-radius: 7px;
        height: 12px; text-align: center; color: transparent;
    }}
    QProgressBar::chunk {{ border-radius: 7px; background: {c['accent']}; }}

    /* Scrollbars */
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; min-width: 30px; }}

    QScrollArea {{ border: none; background: transparent; }}

    QToolTip {{
        background: {c['card']}; color: {c['text']};
        border: 1px solid {c['border']}; border-radius: 8px; padding: 6px;
    }}
    """
