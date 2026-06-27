"""
odds_fetcher.py — Obtención de cuotas de casas de apuestas (The Odds API).

Convierte odds decimales en probabilidades implícitas, remueve el
overround (margen del bookmaker), y cachea resultados.

Si no hay API key configurada, genera odds sintéticas basadas en
el modelo FutFox como fallback (para que la UI funcione igual).

Fuente: https://the-odds-api.com (free tier: 500 req/mes)

Autor: FutFox Prediction Engine
"""

import time
from typing import Dict, Optional, Tuple

import numpy as np
import requests

from constants import (
    ENSEMBLE_WEIGHT,
    ODDS_BOOKMAKERS,
    ODDS_CACHE_TTL,
    ODDS_REGIONS,
    THE_ODDS_API_KEY,
    THE_ODDS_API_URL,
)

# ── Caché en memoria ────────────────────────────────────────────────────
_odds_cache: Dict[str, dict] = {}
_cache_timestamps: Dict[str, float] = {}


def _cache_key(home: str, away: str) -> str:
    return f"{home.lower().strip()}__vs__{away.lower().strip()}"


def _get_cached(key: str) -> Optional[dict]:
    """Retorna odds cacheadas si están frescas."""
    if key in _odds_cache:
        age = time.time() - _cache_timestamps.get(key, 0)
        if age < ODDS_CACHE_TTL:
            return _odds_cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    _odds_cache[key] = data
    _cache_timestamps[key] = time.time()


# ── Fetch de The Odds API ────────────────────────────────────────────────

def fetch_odds_from_api(
    home_team: str,
    away_team: str,
) -> Optional[dict]:
    """
    Intenta obtener cuotas reales desde The Odds API.

    Retorna un dict con:
        - home_odds, draw_odds, away_odds (promedio entre bookmakers)
        - bookmakers: lista de nombres consultados
        - prob_home, prob_draw, prob_away (probabilidades implícitas sin overround)
        - overround: margen total del bookmaker
        - timestamp_utc
    """
    if not THE_ODDS_API_KEY:
        return None

    try:
        url = (
            f"{THE_ODDS_API_URL}/sports/soccer_world_cup/odds/"
            f"?apiKey={THE_ODDS_API_KEY}"
            f"&regions={ODDS_REGIONS}"
            f"&markets=h2h"
            f"&bookmakers={ODDS_BOOKMAKERS}"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None

        all_events = resp.json()
        # Buscar el partido específico
        for event in all_events:
            h = event.get("home_team", "").lower().strip()
            a = event.get("away_team", "").lower().strip()
            if home_team.lower().strip() in h and away_team.lower().strip() in a:
                return _parse_odds_event(event)

        return None
    except Exception:
        return None


def _parse_odds_event(event: dict) -> dict:
    """Extrae promedios de odds de todos los bookmakers en un evento."""
    home_odds_list = []
    draw_odds_list = []
    away_odds_list = []
    bookmakers_seen = []

    for bookie in event.get("bookmakers", []):
        bookmakers_seen.append(bookie.get("title", bookie.get("key", "?")))
        for market in bookie.get("markets", []):
            if market.get("key") != "h2h":
                continue
            outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}

            # Buscar home/draw/away en las outcomes
            home_odd = None
            draw_odd = None
            away_odd = None
            for name, price in outcomes.items():
                if name == event.get("home_team", ""):
                    home_odd = price
                elif name == event.get("away_team", ""):
                    away_odd = price
                elif name.lower() == "draw":
                    draw_odd = price

            if home_odd and draw_odd and away_odd:
                home_odds_list.append(home_odd)
                draw_odds_list.append(draw_odd)
                away_odds_list.append(away_odd)

    if not home_odds_list:
        return {}

    # Promedio entre bookmakers
    avg_home = np.mean(home_odds_list)
    avg_draw = np.mean(draw_odds_list)
    avg_away = np.mean(away_odds_list)

    # Convertir a probabilidades implícitas
    p_raw_h = 1 / avg_home
    p_raw_d = 1 / avg_draw
    p_raw_a = 1 / avg_away

    # Remover overround
    overround = p_raw_h + p_raw_d + p_raw_a
    prob_home = p_raw_h / overround
    prob_draw = p_raw_d / overround
    prob_away = p_raw_a / overround

    return {
        "home_odds": round(avg_home, 2),
        "draw_odds": round(avg_draw, 2),
        "away_odds": round(avg_away, 2),
        "bookmakers": bookmakers_seen[:3],
        "prob_home": float(prob_home),
        "prob_draw": float(prob_draw),
        "prob_away": float(prob_away),
        "overround": float((overround - 1) * 100),
    }


# ── Odds sintéticas (fallback sin API key) ──────────────────────────────

def generate_synthetic_odds(
    prob_home: float,
    prob_draw: float,
    prob_away: float,
) -> dict:
    """
    Genera cuotas sintéticas a partir de las probabilidades del modelo.
    Aplica un margen sintético (~6%) para simular el overround del bookmaker.

    Esto permite mostrar la comparación FutFox vs "Mercado simulado"
    incluso sin API key configurada.
    """
    # Aplicar margen sintético
    margin = 1.06
    p_h = prob_home * margin
    p_d = prob_draw * margin
    p_a = prob_away * margin
    total = p_h + p_d + p_a
    p_h /= total
    p_d /= total
    p_a /= total

    return {
        "home_odds": round(1 / p_h, 2),
        "draw_odds": round(1 / p_d, 2),
        "away_odds": round(1 / p_a, 2),
        "bookmakers": ["Sintético (basado en FutFox)"],
        "prob_home": float(p_h),
        "prob_draw": float(p_d),
        "prob_away": float(p_a),
        "overround": float((margin - 1) * 100),
    }


# ── API pública ──────────────────────────────────────────────────────────

def get_market_odds(
    home_team: str,
    away_team: str,
    model_probs: Optional[Dict[str, float]] = None,
) -> dict:
    """
    Obtiene probabilidades del mercado de apuestas para un partido.

    Args:
        home_team: equipo local
        away_team: equipo visitante
        model_probs: dict con 'prob_home', 'prob_draw', 'prob_away' del
                     modelo FutFox (para fallback sintético)

    Returns:
        Dict con home_odds, draw_odds, away_odds, prob_home, prob_draw,
        prob_away, bookmakers, source ('api' o 'synthetic')
    """
    key = _cache_key(home_team, away_team)

    # 1. Intentar caché
    cached = _get_cached(key)
    if cached:
        return cached

    # 2. Intentar odds de casa mexicana (hardcoded, offline)
    try:
        from odds_mexico import get_mexico_odds
        mex_data = get_mexico_odds(home_team, away_team)
        if mex_data:
            mex_data["source"] = "mexico"
            _set_cache(key, mex_data)
            return mex_data
    except ImportError:
        pass

    # 3. Intentar The Odds API
    api_data = fetch_odds_from_api(home_team, away_team)
    if api_data and api_data.get("home_odds"):
        api_data["source"] = "api"
        _set_cache(key, api_data)
        return api_data

    # 4. Fallback sintético
    if model_probs:
        synth = generate_synthetic_odds(
            model_probs["prob_home"],
            model_probs["prob_draw"],
            model_probs["prob_away"],
        )
        synth["source"] = "synthetic"
        _set_cache(key, synth)
        return synth

    return {
        "source": "unavailable",
        "prob_home": 0.33,
        "prob_draw": 0.34,
        "prob_away": 0.33,
        "bookmakers": ["No disponible"],
    }


def ensemble_probability(
    model_prob: float,
    market_prob: float,
    weight: float = ENSEMBLE_WEIGHT,
) -> float:
    """
    Combina la probabilidad del modelo con la del mercado.

    P_ensemble = w × P_model + (1-w) × P_market

    Args:
        model_prob: probabilidad del modelo FutFox
        market_prob: probabilidad implícita del mercado
        weight: peso del modelo (0-1), default ENSEMBLE_WEIGHT

    Returns:
        Probabilidad combinada
    """
    return weight * model_prob + (1 - weight) * market_prob