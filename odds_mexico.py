"""
odds_mexico.py — Cuotas de casa de apuestas mexicana (Caliente/PlayDoit).

Datos extraidos de app de apuestas deportivas (modo oscuro, Money Line 90').
Horarios en CST (UTC-6, Ciudad de Mexico).

Convierte odds decimales en probabilidades implicitas removiendo el
overround (margen del bookmaker) via el metodo basico de normalizacion.

Fuente: Capturas de app de apuestas mexicana, junio 2026.
Autor: FutFox Prediction Engine
"""

from typing import Dict, Optional

# === ODDS RAW (decimales, Money Line 90 minutos) ===
# Formato: { "home_odds": float, "draw_odds": float, "away_odds": float }

MEXICO_ODDS = {
    "Panama__vs__Inglaterra": {"home_odds": 17.43, "draw_odds": 8.57, "away_odds": 1.14},
    "Croacia__vs__Ghana":     {"home_odds": 1.83,  "draw_odds": 3.19, "away_odds": 5.28},
    "Colombia__vs__Portugal": {"home_odds": 3.46,  "draw_odds": 3.73, "away_odds": 2.03},
    "Congo DR__vs__Uzbekistan": {"home_odds": 1.66, "draw_odds": 3.93, "away_odds": 5.20},
    "Jordania__vs__Argentina": {"home_odds": 21.45, "draw_odds": 8.53, "away_odds": 1.13},
    "Argelia__vs__Austria":    {"home_odds": 3.68,  "draw_odds": 2.08, "away_odds": 3.36},
    "Sudafrica__vs__Canada":   {"home_odds": 5.21,  "draw_odds": 3.56, "away_odds": 1.73},
    "Brasil__vs__Japon":       {"home_odds": 1.69,  "draw_odds": 3.79, "away_odds": 5.15},
    "Alemania__vs__Paraguay":  {"home_odds": 1.38,  "draw_odds": 4.93, "away_odds": 8.03},
    "Paises Bajos__vs__Marruecos": {"home_odds": 2.13, "draw_odds": 3.29, "away_odds": 3.62},
    "Costa de Marfil__vs__Noruega": {"home_odds": 3.76, "draw_odds": 3.56, "away_odds": 1.99},
}


def odds_to_probabilities(home_odds: float, draw_odds: float, away_odds: float) -> Dict[str, float]:
    """
    Convierte odds decimales a probabilidades implicitas,
    removiendo el overround del bookmaker (margen ~5-8%).

    Matematica:
       prob_raw = 1 / odds
       overround = sum(prob_raw)
       prob_clean = prob_raw / overround

    Returns:
        {"prob_home": float, "prob_draw": float, "prob_away": float,
         "overround_pct": float}
    """
    ph = 1.0 / home_odds
    pd = 1.0 / draw_odds
    pa = 1.0 / away_odds
    overround = ph + pd + pa

    return {
        "prob_home": ph / overround,
        "prob_draw": pd / overround,
        "prob_away": pa / overround,
        "overround_pct": round((overround - 1.0) * 100, 2),
    }


def get_mexico_odds(home_team: str, away_team: str) -> Optional[Dict]:
    """
    Obtiene las cuotas y probabilidades del mercado mexicano para un partido.

    Args:
        home_team: equipo local (nombre como aparece en el fixture o API)
        away_team: equipo visitante

    Returns:
        Dict con odds decimales, probabilidades limpias, bookmaker, source.
        None si el partido no esta en los datos.
    """
    # Mapa de nombres API (inglés) → claves de MEXICO_ODDS (español)
    en_to_es = {
        "Panama": "Panama", "England": "Inglaterra", "Croatia": "Croacia",
        "Ghana": "Ghana", "Colombia": "Colombia", "Portugal": "Portugal",
        "Democratic Republic of the Congo": "Congo DR",
        "Uzbekistan": "Uzbekistan", "Jordan": "Jordania",
        "Argentina": "Argentina", "Algeria": "Argelia", "Austria": "Austria",
        "South Africa": "Sudafrica", "Canada": "Canada", "Brazil": "Brasil",
        "Japan": "Japon", "Germany": "Alemania", "Paraguay": "Paraguay",
        "Netherlands": "Paises Bajos", "Morocco": "Marruecos",
        "Ivory Coast": "Costa de Marfil", "Norway": "Noruega",
    }
    
    # Normalizar nombres (inglés → español primero, luego acentos)
    home_key = en_to_es.get(home_team, home_team)
    away_key = en_to_es.get(away_team, away_team)
    
    # Normalizar nombres a como estan en MEXICO_ODDS (sin acentos, sin caracteres especiales)
    # Mapeo de nombres del fixture a nombres en odds
    name_map = {
        "Panama": "Panama", "Panamá": "Panama",
        "Inglaterra": "Inglaterra",
        "Croacia": "Croacia",
        "Ghana": "Ghana",
        "Colombia": "Colombia",
        "Portugal": "Portugal",
        "Congo DR": "Congo DR",
        "Uzbekistan": "Uzbekistan", "Uzbekistán": "Uzbekistan",
        "Jordania": "Jordania",
        "Argentina": "Argentina",
        "Argelia": "Argelia",
        "Austria": "Austria",
        "Sudafrica": "Sudafrica", "Sudáfrica": "Sudafrica",
        "Canada": "Canada", "Canadá": "Canada",
        "Brasil": "Brasil",
        "Japon": "Japon", "Japón": "Japon",
        "Alemania": "Alemania",
        "Paraguay": "Paraguay",
        "Paises Bajos": "Paises Bajos", "Países Bajos": "Paises Bajos",
        "Marruecos": "Marruecos",
        "Costa de Marfil": "Costa de Marfil",
        "Noruega": "Noruega",
    }
    
    home_key = name_map.get(home_key, home_key)
    away_key = name_map.get(away_key, away_key)
    cache_key = f"{home_key}__vs__{away_key}"

    if cache_key not in MEXICO_ODDS:
        # Intentar en orden inverso
        cache_key_rev = f"{away_key}__vs__{home_key}"
        if cache_key_rev not in MEXICO_ODDS:
            return None
        # Si esta en orden inverso, intercambiar home/away
        odds = MEXICO_ODDS[cache_key_rev]
        probs = odds_to_probabilities(odds["away_odds"], odds["draw_odds"], odds["home_odds"])
        result = {
            "home_odds": odds["away_odds"],
            "draw_odds": odds["draw_odds"],
            "away_odds": odds["home_odds"],
        }
        result.update(probs)
        result["bookmakers"] = ["Caliente (Mexico)"]
        result["source"] = "mexico_hardcoded"
        return result

    odds = MEXICO_ODDS[cache_key]
    probs = odds_to_probabilities(odds["home_odds"], odds["draw_odds"], odds["away_odds"])
    result = {
        "home_odds": odds["home_odds"],
        "draw_odds": odds["draw_odds"],
        "away_odds": odds["away_odds"],
    }
    result.update(probs)
    result["bookmakers"] = ["Caliente (Mexico)"]
    result["source"] = "mexico_hardcoded"
    return result


def get_all_mexico_matches() -> list:
    """Retorna todos los partidos con cuotas mexicanas disponibles."""
    matches = []
    for key, odds in MEXICO_ODDS.items():
        home, away = key.split("__vs__")
        probs = odds_to_probabilities(odds["home_odds"], odds["draw_odds"], odds["away_odds"])
        matches.append({
            "home": home,
            "away": away,
            "home_odds": odds["home_odds"],
            "draw_odds": odds["draw_odds"],
            "away_odds": odds["away_odds"],
            "prob_home": round(probs["prob_home"] * 100, 1),
            "prob_draw": round(probs["prob_draw"] * 100, 1),
            "prob_away": round(probs["prob_away"] * 100, 1),
            "overround_pct": probs["overround_pct"],
        })
    return matches


if __name__ == "__main__":
    print("=== ODDS CASA MEXICANA (Money Line 90') ===\n")
    for m in get_all_mexico_matches():
        print(f"{m['home']} vs {m['away']}")
        print(f"  Cuotas: {m['home_odds']}x / {m['draw_odds']}x / {m['away_odds']}x")
        print(f"  Prob: {m['prob_home']}% / {m['prob_draw']}% / {m['prob_away']}%")
        print(f"  Overround: {m['overround_pct']}%")
        print()
