"""Capa de datos SQLite. Conexion por operacion (segura entre hilos)."""
from __future__ import annotations

import sqlite3
from datetime import date as _date
from typing import Any

from . import config

MEALS = ["Desayuno", "Comida", "Cena", "Snacks"]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS profile (
                id          INTEGER PRIMARY KEY CHECK (id = 1),
                name        TEXT NOT NULL,
                sex         TEXT NOT NULL,
                age         INTEGER NOT NULL,
                height_cm   REAL NOT NULL,
                weight_kg   REAL NOT NULL,
                activity    TEXT NOT NULL,
                goal        TEXT NOT NULL,
                rate        INTEGER NOT NULL DEFAULT 2,
                protein_per_kg REAL NOT NULL DEFAULT 2.0,
                fat_pct     REAL NOT NULL DEFAULT 0.27,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS food_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                day       TEXT NOT NULL,
                meal      TEXT NOT NULL,
                name      TEXT NOT NULL,
                grams     REAL NOT NULL,
                kcal      REAL NOT NULL,
                protein   REAL NOT NULL,
                carbs     REAL NOT NULL,
                fat       REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_foodlog_day ON food_log(day);

            CREATE TABLE IF NOT EXISTS food_cache (
                name       TEXT PRIMARY KEY,
                kcal100    REAL NOT NULL,
                protein100 REAL NOT NULL,
                carbs100   REAL NOT NULL,
                fat100     REAL NOT NULL,
                grams_per_unit REAL,
                unit_name  TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS weight_log (
                day        TEXT PRIMARY KEY,
                weight_kg  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS water_log (
                day  TEXT PRIMARY KEY,
                ml   REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS bug_reports (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                kind       TEXT NOT NULL,
                message    TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'nuevo'
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def _now() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return _date.today().isoformat()


# ---------- Perfil ----------

def get_profile() -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM profile WHERE id = 1").fetchone()
        return dict(row) if row else None


def has_profile() -> bool:
    return get_profile() is not None


def save_profile(data: dict) -> None:
    now = _now()
    with connect() as c:
        exists = c.execute("SELECT 1 FROM profile WHERE id = 1").fetchone()
        if exists:
            c.execute(
                """UPDATE profile SET name=?, sex=?, age=?, height_cm=?, weight_kg=?,
                   activity=?, goal=?, rate=?, protein_per_kg=?, fat_pct=?, updated_at=?
                   WHERE id = 1""",
                (
                    data["name"], data["sex"], data["age"], data["height_cm"],
                    data["weight_kg"], data["activity"], data["goal"], data["rate"],
                    data["protein_per_kg"], data["fat_pct"], now,
                ),
            )
        else:
            c.execute(
                """INSERT INTO profile (id, name, sex, age, height_cm, weight_kg,
                   activity, goal, rate, protein_per_kg, fat_pct, created_at, updated_at)
                   VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data["name"], data["sex"], data["age"], data["height_cm"],
                    data["weight_kg"], data["activity"], data["goal"], data["rate"],
                    data["protein_per_kg"], data["fat_pct"], now, now,
                ),
            )
    # Registrar peso del dia al guardar perfil
    set_weight(today(), data["weight_kg"])


# ---------- Comidas ----------

def add_food(day: str, meal: str, name: str, grams: float,
             kcal: float, protein: float, carbs: float, fat: float) -> int:
    with connect() as c:
        cur = c.execute(
            """INSERT INTO food_log (day, meal, name, grams, kcal, protein, carbs, fat, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (day, meal, name, grams, kcal, protein, carbs, fat, _now()),
        )
        return cur.lastrowid


def delete_food(food_id: int) -> None:
    with connect() as c:
        c.execute("DELETE FROM food_log WHERE id = ?", (food_id,))


def foods_for_day(day: str) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM food_log WHERE day = ? ORDER BY id", (day,)
        ).fetchall()
        return [dict(r) for r in rows]


def day_totals(day: str) -> dict:
    with connect() as c:
        row = c.execute(
            """SELECT COALESCE(SUM(kcal),0) kcal, COALESCE(SUM(protein),0) protein,
                      COALESCE(SUM(carbs),0) carbs, COALESCE(SUM(fat),0) fat
               FROM food_log WHERE day = ?""",
            (day,),
        ).fetchone()
        return dict(row)


def logged_days(limit: int = 30) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            """SELECT day, COALESCE(SUM(kcal),0) kcal, COALESCE(SUM(protein),0) protein,
                      COALESCE(SUM(carbs),0) carbs, COALESCE(SUM(fat),0) fat
               FROM food_log GROUP BY day ORDER BY day DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Cache de alimentos ----------

def get_cached_food(name: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM food_cache WHERE name = ?", (name.strip().lower(),)
        ).fetchone()
        return dict(row) if row else None


def cache_food(name: str, kcal100: float, protein100: float, carbs100: float,
               fat100: float, grams_per_unit: float | None, unit_name: str | None) -> None:
    with connect() as c:
        c.execute(
            """INSERT OR REPLACE INTO food_cache
               (name, kcal100, protein100, carbs100, fat100, grams_per_unit, unit_name, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name.strip().lower(), kcal100, protein100, carbs100, fat100,
             grams_per_unit, unit_name, _now()),
        )


def recent_foods(limit: int = 12) -> list[str]:
    with connect() as c:
        rows = c.execute(
            "SELECT DISTINCT name FROM food_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [r["name"] for r in rows]


# ---------- Peso ----------

def set_weight(day: str, weight_kg: float) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO weight_log (day, weight_kg) VALUES (?,?)",
            (day, weight_kg),
        )


def weight_history(limit: int = 90) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT day, weight_kg FROM weight_log ORDER BY day DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


# ---------- Agua ----------

def get_water(day: str) -> float:
    with connect() as c:
        row = c.execute("SELECT ml FROM water_log WHERE day = ?", (day,)).fetchone()
        return row["ml"] if row else 0.0


def add_water(day: str, ml: float) -> float:
    current = get_water(day)
    new_val = max(0.0, current + ml)
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO water_log (day, ml) VALUES (?,?)", (day, new_val)
        )
    return new_val


# ---------- Reportes ----------

def add_report(kind: str, message: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO bug_reports (created_at, kind, message, status) VALUES (?,?,?, 'nuevo')",
            (_now(), kind, message),
        )


def get_reports() -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM bug_reports ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Chat ----------

def add_chat(role: str, content: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO chat_history (role, content, created_at) VALUES (?,?,?)",
            (role, content, _now()),
        )


def chat_history(limit: int = 50) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def clear_chat() -> None:
    with connect() as c:
        c.execute("DELETE FROM chat_history")
