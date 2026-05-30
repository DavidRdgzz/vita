"""Motor de calculo nutricional: BMR, TDEE y reparto de macros."""
from __future__ import annotations

# Multiplicadores de actividad (sobre el BMR) -> TDEE
ACTIVITY_FACTORS = {
    "sedentario": 1.20,      # poco o nada de ejercicio
    "ligero": 1.375,         # 1-3 dias/semana
    "moderado": 1.55,        # 3-5 dias/semana
    "activo": 1.725,         # 6-7 dias/semana
    "muy_activo": 1.90,      # ejercicio intenso o trabajo fisico
}

ACTIVITY_LABELS = {
    "sedentario": "Sedentario (poco o nada de ejercicio)",
    "ligero": "Ligero (1-3 dias/semana)",
    "moderado": "Moderado (3-5 dias/semana)",
    "activo": "Activo (6-7 dias/semana)",
    "muy_activo": "Muy activo (ejercicio intenso / trabajo fisico)",
}

GOAL_LABELS = {
    "volumen": "Volumen (ganar musculo)",
    "definicion": "Definicion (perder grasa)",
    "mantenimiento": "Mantenimiento",
}

# Ajuste calorico segun objetivo y ritmo (1=suave, 2=moderado, 3=agresivo)
CALORIE_ADJUST = {
    "volumen": {1: 200, 2: 350, 3: 500},
    "definicion": {1: -300, 2: -500, 3: -700},
    "mantenimiento": {1: 0, 2: 0, 3: 0},
}

RATE_LABELS = {1: "Suave", 2: "Moderado", 3: "Agresivo"}

# Proteina recomendada (g por kg de peso) por objetivo
DEFAULT_PROTEIN_PER_KG = {
    "volumen": 2.0,
    "definicion": 2.2,
    "mantenimiento": 1.8,
}


def bmr_mifflin(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Tasa metabolica basal (Mifflin-St Jeor)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "hombre" else base - 161


def tdee(bmr: float, activity: str) -> float:
    return bmr * ACTIVITY_FACTORS.get(activity, 1.2)


def target_calories(tdee_val: float, goal: str, rate: int) -> float:
    adjust = CALORIE_ADJUST.get(goal, {}).get(rate, 0)
    return max(1200.0, tdee_val + adjust)


def macro_split(target_kcal: float, weight_kg: float,
                protein_per_kg: float, fat_pct: float) -> dict:
    """Reparte las calorias en proteina, grasa y carbos (en gramos)."""
    protein_g = protein_per_kg * weight_kg
    protein_kcal = protein_g * 4

    fat_kcal = target_kcal * fat_pct
    fat_g = fat_kcal / 9

    carb_kcal = max(0.0, target_kcal - protein_kcal - fat_kcal)
    carb_g = carb_kcal / 4

    return {
        "protein": round(protein_g),
        "fat": round(fat_g),
        "carbs": round(carb_g),
    }


def compute_targets(profile: dict) -> dict:
    """Calcula todos los objetivos diarios a partir del perfil."""
    bmr = bmr_mifflin(
        profile["sex"], profile["weight_kg"], profile["height_cm"], profile["age"]
    )
    tdee_val = tdee(bmr, profile["activity"])
    kcal = target_calories(tdee_val, profile["goal"], profile["rate"])
    macros = macro_split(
        kcal, profile["weight_kg"],
        profile["protein_per_kg"], profile["fat_pct"],
    )
    return {
        "bmr": round(bmr),
        "tdee": round(tdee_val),
        "kcal": round(kcal),
        "protein": macros["protein"],
        "carbs": macros["carbs"],
        "fat": macros["fat"],
    }
