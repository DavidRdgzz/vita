"""Utilidades varias."""
from __future__ import annotations

from datetime import date, datetime

_DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _to_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_date_es(value: str | date, *, full: bool = True) -> str:
    d = _to_date(value)
    if full:
        return f"{_DAYS[d.weekday()]}, {d.day} de {_MONTHS[d.month - 1]} de {d.year}"
    return f"{d.day} {_MONTHS[d.month - 1][:3]}"


def relative_label(value: str | date) -> str:
    d = _to_date(value)
    delta = (date.today() - d).days
    if delta == 0:
        return "Hoy"
    if delta == 1:
        return "Ayer"
    return format_date_es(d, full=False)
