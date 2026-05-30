"""Cliente de Google Gemini (API gratuita): macros con cache y chat asistente."""
from __future__ import annotations

import json
import re

import requests

from . import config, db, nutrition

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class AIError(Exception):
    """Error controlado para mostrar en la interfaz."""


def _api_key() -> str:
    key = config.get_api_key()
    if not key:
        raise AIError(
            "No hay API key configurada. Ve a Ajustes y pega tu clave gratuita "
            "de Google Gemini (se obtiene en aistudio.google.com)."
        )
    return key


def _model() -> str:
    return config.get("model", config.DEFAULT_MODEL) or config.DEFAULT_MODEL


def _error_message(resp: requests.Response) -> str:
    try:
        detail = resp.json().get("error", {}).get("message", "")
    except ValueError:
        detail = resp.text[:200]
    code = resp.status_code
    if code in (400, 401, 403):
        return (
            "API key inválida o sin permisos. Revisa tu clave de Gemini en "
            f"Ajustes. {detail}".strip()
        )
    if code == 404:
        return (
            "Modelo no encontrado. Cambia el nombre del modelo en Ajustes "
            f"(p. ej. gemini-1.5-flash). {detail}".strip()
        )
    if code == 429:
        return (
            "Límite de la capa gratuita alcanzado para este modelo. Si se repite, "
            "cambia el modelo en Ajustes (p. ej. gemini-2.5-flash-lite o "
            f"gemini-2.5-flash). Detalle: {detail}".strip()
        )
    return f"Error de la IA ({code}). {detail}".strip()


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason")
        if reason:
            raise AIError(f"La IA bloqueó la respuesta ({reason}).")
        raise AIError("La IA no devolvió respuesta.")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise AIError("La IA devolvió una respuesta vacía.")
    return text


def _generate(system: str, contents: list[dict], *, max_tokens: int,
              temperature: float, json_mode: bool = False) -> str:
    key = _api_key()
    model = _model()
    gen_cfg: dict = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": gen_cfg,
    }
    try:
        resp = requests.post(
            f"{_BASE}/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
    except requests.RequestException as exc:
        raise AIError(f"Sin conexión con la IA: {exc}") from exc
    if resp.status_code != 200:
        raise AIError(_error_message(resp))
    try:
        data = resp.json()
    except ValueError as exc:
        raise AIError("Respuesta no válida de la IA.") from exc
    return _extract_text(data)


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AIError("Respuesta de la IA no valida.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AIError("No se pudo interpretar la respuesta de la IA.") from exc


_MACRO_SYSTEM = (
    "Eres una base de datos nutricional precisa. El usuario te da el nombre de un "
    "alimento en espanol. Devuelve UNICAMENTE un objeto JSON, sin texto adicional, "
    "con los valores nutricionales por 100 gramos de la forma mas habitual de "
    "consumir ese alimento. Formato exacto:\n"
    '{"found": true, "kcal": <num>, "protein_g": <num>, "carbs_g": <num>, '
    '"fat_g": <num>, "grams_per_unit": <num o null>, "unit_name": <texto o null>}\n'
    "grams_per_unit es el peso aproximado de UNA unidad/porcion tipica si aplica "
    '(ej: huevo 55, platano 120, rebanada de pan 30); null si no tiene sentido '
    "(ej: arroz, leche). Si no reconoces el alimento, devuelve found=false y ceros."
)


def get_macros(name: str) -> dict:
    """Macros por 100g de un alimento. Usa cache local antes de llamar a la IA."""
    name = name.strip()
    if not name:
        raise AIError("Escribe el nombre de un alimento.")

    cached = db.get_cached_food(name)
    if cached:
        return {
            "name": name,
            "kcal100": cached["kcal100"],
            "protein100": cached["protein100"],
            "carbs100": cached["carbs100"],
            "fat100": cached["fat100"],
            "grams_per_unit": cached["grams_per_unit"],
            "unit_name": cached["unit_name"],
            "from_cache": True,
        }

    text = _generate(
        _MACRO_SYSTEM,
        [{"role": "user", "parts": [{"text": name}]}],
        max_tokens=300,
        temperature=0.0,
        json_mode=True,
    )
    data = _extract_json(text)
    if not data.get("found", False):
        raise AIError(f"No reconozco el alimento '{name}'. Prueba otro nombre.")

    try:
        kcal = float(data["kcal"])
        protein = float(data["protein_g"])
        carbs = float(data["carbs_g"])
        fat = float(data["fat_g"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AIError("La IA devolvio datos incompletos.") from exc

    gpu = data.get("grams_per_unit")
    gpu = float(gpu) if isinstance(gpu, (int, float)) else None
    unit_name = data.get("unit_name") or None

    db.cache_food(name, kcal, protein, carbs, fat, gpu, unit_name)
    return {
        "name": name,
        "kcal100": kcal,
        "protein100": protein,
        "carbs100": carbs,
        "fat100": fat,
        "grams_per_unit": gpu,
        "unit_name": unit_name,
        "from_cache": False,
    }


def _chat_system(profile: dict | None) -> str:
    base = (
        "Eres Vita, una asistente de nutricion y fitness cercana y motivadora que "
        "responde en espanol de forma breve, clara y practica. Das consejos "
        "alimentarios y de entrenamiento generales, nunca diagnosticos medicos. "
        "Si detectas un problema de salud serio, recomienda acudir a un profesional."
    )
    if not profile:
        return base
    t = nutrition.compute_targets(profile)
    today = db.today()
    tot = db.day_totals(today)
    base += (
        f"\n\nDatos de la usuaria: {profile['name']}, {profile['sex']}, "
        f"{profile['age']} anos, {profile['height_cm']:.0f} cm, "
        f"{profile['weight_kg']:.1f} kg. "
        f"Objetivo: {nutrition.GOAL_LABELS.get(profile['goal'], profile['goal'])}. "
        f"Objetivos diarios: {t['kcal']} kcal, {t['protein']}g proteina, "
        f"{t['carbs']}g carbohidratos, {t['fat']}g grasa.\n"
        f"Hoy lleva consumido: {tot['kcal']:.0f} kcal, {tot['protein']:.0f}g proteina, "
        f"{tot['carbs']:.0f}g carbos, {tot['fat']:.0f}g grasa."
    )
    return base


def chat(user_message: str, profile: dict | None, history: list[dict]) -> str:
    """Respuesta del asistente. history = lista de {role, content}."""
    contents = []
    for m in history:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})
    return _generate(
        _chat_system(profile),
        contents,
        max_tokens=800,
        temperature=0.7,
    )
