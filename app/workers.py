"""Ejecucion de tareas en segundo plano para no congelar la GUI."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    result = Signal(object)
    error = Signal(str)


class Worker(QRunnable):
    """Ejecuta una funcion en un hilo y emite el resultado o el error."""

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _Signals()

    def run(self) -> None:
        try:
            res = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 - reportamos cualquier fallo a la GUI
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(res)


def run_async(fn: Callable, on_result: Callable, on_error: Callable, *args, **kwargs) -> None:
    """Lanza fn en segundo plano; on_result/on_error se ejecutan en el hilo de la GUI."""
    worker = Worker(fn, *args, **kwargs)
    worker.signals.result.connect(on_result)
    worker.signals.error.connect(on_error)
    QThreadPool.globalInstance().start(worker)
