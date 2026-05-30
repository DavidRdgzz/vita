"""Comprobacion y aplicacion de actualizaciones (Windows, exe onefile)."""
from __future__ import annotations

import os
import subprocess
import sys

import requests

from . import APP_VERSION, config

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008


def _parse(v: str) -> tuple:
    out = []
    for part in str(v).strip().lstrip("vV").split("."):
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    return tuple(out)


def check() -> dict | None:
    """Devuelve {version, url, notes} si hay una version mas nueva; si no, None."""
    url = (config.UPDATE_URL or "").strip()
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10, headers={"Cache-Control": "no-cache"})
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None
    latest = str(data.get("version", "")).strip()
    dl = str(data.get("url", "")).strip()
    if not latest or not dl or _parse(latest) <= _parse(APP_VERSION):
        return None
    return {"version": latest, "url": dl, "notes": str(data.get("notes", ""))}


def current_exe() -> str | None:
    """Ruta del exe en ejecucion (solo cuando esta empaquetado con PyInstaller)."""
    return sys.executable if getattr(sys, "frozen", False) else None


def download(url: str) -> str:
    """Descarga el nuevo exe junto al actual y devuelve su ruta."""
    exe = current_exe()
    if not exe:
        raise RuntimeError("Solo se puede autoactualizar la version empaquetada.")
    dest = os.path.join(os.path.dirname(exe), "Vita.update.exe")
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=262144):
                if chunk:
                    f.write(chunk)
    return dest


def apply_and_relaunch(new_exe: str) -> None:
    """Lanza un proceso que espera a que cierre la app, reemplaza el exe y relanza."""
    exe = current_exe()
    if not exe:
        return
    e = exe.replace("'", "''")
    n = new_exe.replace("'", "''")
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        "for($i=0;$i -lt 120;$i++){"
        f"try{{Move-Item -Force -LiteralPath '{n}' -Destination '{e}' -ErrorAction Stop;break}}"
        "catch{Start-Sleep -Milliseconds 500}}"
        f"Start-Process -FilePath '{e}'"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
        close_fds=True,
    )
