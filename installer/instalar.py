"""Instalador de Vita: copia la app a Documentos y crea accesos directos."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

APP_NAME = "Vita"
MODEL = "gemini-2.5-flash-lite"
CREATE_NO_WINDOW = 0x08000000

BG = "#1A1A1F"
CARD = "#26262E"
ACCENT = "#FF5C8A"
ACCENT_DK = "#E04A77"
TEXT = "#F2F2F5"
MUTED = "#9A9AA8"
OK = "#46D17F"
ERR = "#FF6B6B"


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def run_ps(command: str) -> str:
    """Ejecuta PowerShell sin abrir ventana; devuelve stdout (vacio si falla)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=30,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def documents_dir() -> Path:
    p = run_ps("[Environment]::GetFolderPath('MyDocuments')")
    if p and Path(p).exists():
        return Path(p)
    return Path(os.path.expanduser("~")) / "Documents"


def create_shortcut(lnk_path: str, target: str) -> None:
    q = lambda s: s.replace("'", "''")
    workdir = str(Path(target).parent)
    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{q(lnk_path)}'); "
        f"$s.TargetPath = '{q(target)}'; "
        f"$s.WorkingDirectory = '{q(workdir)}'; "
        f"$s.IconLocation = '{q(target)}'; "
        "$s.Description = 'Vita - tu compañera fitness'; "
        "$s.Save()"
    )
    run_ps(ps)


def preconfig_apikey() -> bool:
    """Si hay apikey.txt junto al instalador y aun no hay config, la preconfigura."""
    keyfile = base_dir() / "apikey.txt"
    if not keyfile.exists():
        return False
    try:
        key = keyfile.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if not key:
        return False
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    vita_data = Path(appdata) / APP_NAME
    cfg_path = vita_data / "config.json"
    if cfg_path.exists():
        return False
    try:
        vita_data.mkdir(parents=True, exist_ok=True)
        cfg = {"api_key": key, "model": MODEL, "water_goal_ml": 2500}
        cfg_path.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return True
    except OSError:
        return False


class Installer(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Instalar Vita")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._dest_exe: str | None = None

        w, h = 460, 340
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        try:
            ico = base_dir() / "Vita.exe"
            if ico.exists():
                self.iconbitmap(default=str(ico))
        except Exception:
            pass

        title_f = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        sub_f = tkfont.Font(family="Segoe UI", size=10)
        btn_f = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        st_f = tkfont.Font(family="Segoe UI", size=9)

        tk.Label(self, text="Vita", font=title_f, fg=ACCENT, bg=BG).pack(pady=(38, 0))
        tk.Label(
            self,
            text="Tu compañera fitness",
            font=sub_f,
            fg=MUTED,
            bg=BG,
        ).pack(pady=(2, 22))
        tk.Label(
            self,
            text="Se instalará en Documentos\\Vita y se creará\nun acceso directo en tu escritorio.",
            font=sub_f,
            fg=TEXT,
            bg=BG,
            justify="center",
        ).pack(pady=(0, 24))

        self._btn = tk.Button(
            self,
            text="Instalar",
            font=btn_f,
            fg="#FFFFFF",
            bg=ACCENT,
            activebackground=ACCENT_DK,
            activeforeground="#FFFFFF",
            relief="flat",
            width=18,
            height=2,
            cursor="hand2",
            command=self._install,
        )
        self._btn.pack()

        self._status = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self._status,
            font=st_f,
            fg=MUTED,
            bg=BG,
            wraplength=400,
            justify="center",
        ).pack(pady=(18, 0))

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self._status.set(text)
        self.update_idletasks()

    def _install(self) -> None:
        self._btn.config(state="disabled")
        self._set_status("Instalando...")
        self.update_idletasks()

        src = base_dir() / "Vita.exe"
        if not src.exists():
            self._set_status(
                "No encuentro Vita.exe. Extrae TODO el .zip a una carpeta "
                "y ejecuta el instalador desde ahí.",
                ERR,
            )
            self._btn.config(state="normal")
            return

        try:
            dest_dir = documents_dir() / APP_NAME
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_exe = dest_dir / "Vita.exe"
            shutil.copy2(src, dest_exe)
        except Exception as e:
            self._set_status(f"Error al copiar: {e}", ERR)
            self._btn.config(state="normal")
            return

        desktop = run_ps("[Environment]::GetFolderPath('Desktop')")
        if desktop:
            create_shortcut(str(Path(desktop) / "Vita.lnk"), str(dest_exe))
        programs = run_ps("[Environment]::GetFolderPath('Programs')")
        if programs:
            create_shortcut(str(Path(programs) / "Vita.lnk"), str(dest_exe))

        preconfig_apikey()

        self._dest_exe = str(dest_exe)
        self._set_status("¡Listo! Vita está en tu escritorio y en Documentos\\Vita.", OK)
        self._btn.config(
            text="Abrir Vita",
            state="normal",
            bg=OK,
            activebackground="#37B86A",
            command=self._open,
        )

    def _open(self) -> None:
        if self._dest_exe and os.path.exists(self._dest_exe):
            try:
                os.startfile(self._dest_exe)  # noqa: S606
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    Installer().mainloop()
