"""
live_api.py — Cliente para la API de worldcup26.ir (datos en vivo del Mundial 2026).

Maneja caché en memoria y reintentos automáticos con timeout.
"""

import time
import requests
import logging
from typing import Dict, List, Optional
from constants import WORLDCUP_API_BASE_URL, LIVE_CACHE_TTL, STATIC_CACHE_TTL, API_TIMEOUT

# Configurar logger
logger = logging.getLogger("live_api")

# Caché en memoria
_cache: Dict[str, any] = {}
_cache_time: Dict[str, float] = {}
_api_online: bool = True  # Para registrar estado de la API

def get_api_status() -> bool:
    """Retorna si la API estuvo online en la última petición."""
    return _api_online

def _fetch_endpoint(endpoint: str, ttl: int) -> Optional[any]:
    """Fetches data from an endpoint with caching and timeout.
    Returns None if the API is unreachable."""
    global _api_online
    now = time.time()
    if endpoint in _cache and (now - _cache_time.get(endpoint, 0)) < ttl:
        return _cache[endpoint]

    url = f"{WORLDCUP_API_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            _cache[endpoint] = data
            _cache_time[endpoint] = now
            _api_online = True
            logger.info(f"API OK: {endpoint} ({len(str(data))} bytes)")
            return data
        else:
            logger.warning(f"API error {response.status_code} en {endpoint}")
            _api_online = False
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout conectando a API {endpoint}")
        _api_online = False
    except requests.exceptions.ConnectionError:
        logger.warning(f"Error de conexión a API {endpoint}")
        _api_online = False
    except Exception as e:
        logger.warning(f"Excepción conectando a API {endpoint}: {e}")
        _api_online = False

    # Si la API falla pero tenemos caché antigua, la retornamos en lugar de fallar
    if endpoint in _cache:
        logger.info(f"Usando caché expirada para {endpoint} debido a fallo de API")
        return _cache[endpoint]
    return None

def fetch_games() -> Optional[List[dict]]:
    """Obtiene la lista de partidos de la API."""
    data = _fetch_endpoint("/get/games", LIVE_CACHE_TTL)
    if data and "games" in data:
        return data["games"]
    return None

def fetch_teams() -> Optional[List[dict]]:
    """Obtiene la lista de equipos de la API."""
    data = _fetch_endpoint("/get/teams", STATIC_CACHE_TTL)
    if data and "teams" in data:
        return data["teams"]
    return None

def fetch_stadiums() -> Optional[List[dict]]:
    """Obtiene la lista de estadios de la API."""
    data = _fetch_endpoint("/get/stadiums", STATIC_CACHE_TTL)
    if data and "stadiums" in data:
        return data["stadiums"]
    return None

# Mappings helpers
_stadium_map: Dict[str, dict] = {}
_team_map: Dict[str, dict] = {}

# Altitudes reales de los estadios del Mundial 2026
_STADIUM_ALTITUDES = {
    "1": 2240,  # Estadio Azteca, Ciudad de México
    "2": 1566,  # Estadio Akron, Guadalajara
    "3": 535,   # Estadio BBVA, Monterrey
    "4": 181,   # AT&T Stadium, Dallas (Arlington)
    "5": 13,    # NRG Stadium, Houston
    "6": 277,   # GEHA Field at Arrowhead, Kansas City
    "7": 320,   # Mercedes-Benz Stadium, Atlanta
    "8": 2,     # Hard Rock Stadium, Miami
    "9": 87,    # Gillette Stadium, Boston (Foxborough)
    "10": 12,   # Lincoln Financial Field, Philadelphia
    "11": 3,    # MetLife Stadium, NY/NJ (East Rutherford)
    "12": 76,   # BMO Field, Toronto
    "13": 2,    # BC Place, Vancouver
    "14": 53,   # Lumen Field, Seattle
    "15": 10,   # Levi's Stadium, San Francisco (Santa Clara)
    "16": 38,   # SoFi Stadium, Los Angeles (Inglewood)
}

# Clima típico simulado (temperatura y humedad) para verano en esas ciudades
_STADIUM_WEATHER = {
    "1": {"temp": 24, "humidity": 40},   # Azteca
    "2": {"temp": 28, "humidity": 45},   # Akron
    "3": {"temp": 32, "humidity": 50},   # BBVA
    "4": {"temp": 32, "humidity": 55},   # AT&T
    "5": {"temp": 34, "humidity": 75},   # NRG
    "6": {"temp": 30, "humidity": 60},   # Arrowhead
    "7": {"temp": 30, "humidity": 70},   # Mercedes-Benz
    "8": {"temp": 32, "humidity": 80},   # Hard Rock
    "9": {"temp": 25, "humidity": 60},   # Gillette
    "10": {"temp": 26, "humidity": 65},  # Lincoln Financial
    "11": {"temp": 26, "humidity": 60},  # MetLife
    "12": {"temp": 22, "humidity": 65},  # BMO
    "13": {"temp": 18, "humidity": 65},  # BC Place
    "14": {"temp": 22, "humidity": 60},  # Lumen
    "15": {"temp": 24, "humidity": 50},  # Levi's
    "16": {"temp": 24, "humidity": 50},  # SoFi
}

# Timezone de cada estadio (offset UTC). Cada sede juega en su hora local.
STADIUM_TIMEZONES = {
    "1": -6,   # Estadio Azteca, Ciudad de México → CST
    "2": -6,   # Estadio Akron, Guadalajara → CST
    "3": -6,   # Estadio BBVA, Monterrey → CST
    "4": -5,   # AT&T Stadium, Arlington (Dallas) → CDT
    "5": -5,   # NRG Stadium, Houston → CDT
    "6": -5,   # GEHA Field at Arrowhead, Kansas City → CDT
    "7": -4,   # Mercedes-Benz Stadium, Atlanta → EDT
    "8": -4,   # Hard Rock Stadium, Miami → EDT
    "9": -4,   # Gillette Stadium, Foxborough (Boston) → EDT
    "10": -4,  # Lincoln Financial Field, Philadelphia → EDT
    "11": -4,  # MetLife Stadium, East Rutherford (NY/NJ) → EDT
    "12": -4,  # BMO Field, Toronto → EDT
    "13": -7,  # BC Place, Vancouver → PDT
    "14": -7,  # Lumen Field, Seattle → PDT
    "15": -7,  # Levi's Stadium, Santa Clara (SF) → PDT
    "16": -7,  # SoFi Stadium, Inglewood (LA) → PDT
}


def get_stadium_info(stadium_id: str) -> dict:
    """Mapea stadium_id a un diccionario con nombre, ciudad, país, altitud, temp y humedad."""
    global _stadium_map
    s_id_str = str(stadium_id)
    if not _stadium_map:
        stadiums = fetch_stadiums()
        if stadiums:
            for s in stadiums:
                id_key = str(s.get("id"))
                _stadium_map[id_key] = {
                    "name": s.get("name_en"),
                    "city": s.get("city_en"),
                    "country": s.get("country_en")
                }
    
    base_info = _stadium_map.get(s_id_str, {
        "name": f"Estadio {s_id_str}",
        "city": "Sede Mundialista",
        "country": "Mundial 2026"
    }).copy()
    
    # Agregar altitud, clima y timezone
    base_info["altitude_m"] = _STADIUM_ALTITUDES.get(s_id_str, 0)
    weather = _STADIUM_WEATHER.get(s_id_str, {"temp": 22, "humidity": 50})
    base_info["temperature_c"] = weather["temp"]
    base_info["humidity_pct"] = weather["humidity"]
    base_info["utc_offset"] = STADIUM_TIMEZONES.get(s_id_str, -6)
    
    return base_info

def map_game_to_match(g: dict) -> dict:
    """Mapea un partido de la API worldcup26.ir a la estructura interna de FutFox.
    Normaliza nombres de equipos usando TEAM_NAME_MAP (inglés → español)."""
    from datetime import datetime
    from constants import TEAM_NAME_MAP

    stadium_id = str(g.get("stadium_id", ""))
    stadium_info = get_stadium_info(stadium_id)

    # ── Nombres de equipos normalizados ────────────────────────────
    home_en = g.get("home_team_name_en", "")
    away_en = g.get("away_team_name_en", "")
    home_label = g.get("home_team_label", "")
    away_label = g.get("away_team_label", "")

    if not home_en and home_label:
        home_en = home_label
    if not away_en and away_label:
        away_en = away_label

    home_name = TEAM_NAME_MAP.get(home_en, home_en)
    away_name = TEAM_NAME_MAP.get(away_en, away_en)

    # Parse scores
    try:
        score_home = int(g.get("home_score")) if g.get("home_score") is not None else None
    except (ValueError, TypeError):
        score_home = None

    try:
        score_away = int(g.get("away_score")) if g.get("away_score") is not None else None
    except (ValueError, TypeError):
        score_away = None

    # Parse status & minute
    time_elapsed = str(g.get("time_elapsed", "notstarted")).strip().lower()
    finished_val = str(g.get("finished", "FALSE")).upper().strip()

    if time_elapsed == "finished" or finished_val == "TRUE":
        status, minute = "finished", 90
    elif time_elapsed == "notstarted" or time_elapsed == "none" or time_elapsed == "":
        status, minute = "upcoming", 0
    elif time_elapsed.isdigit():
        status, minute = "live", int(time_elapsed)
    else:
        status = "live"
        min_clean = time_elapsed.replace("'", "").strip()
        if "+" in min_clean:
            try:
                minute = sum(int(p) for p in min_clean.split("+"))
            except ValueError:
                minute = 45
        else:
            try:
                minute = int(min_clean)
            except ValueError:
                minute = 45

    # Horario local
    local_date_str = g.get("local_date", "")
    cst_time = "N/A"
    if local_date_str and " " in local_date_str:
        try:
            cst_time = local_date_str.split(" ")[1][:5]
        except Exception:
            pass

    datetime_normalized = local_date_str
    if "/" in local_date_str:
        try:
            dt = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            datetime_normalized = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass

    utc_offset = stadium_info.get("utc_offset", -6)
    raw_home_scorers = str(g.get("home_scorers", "null"))
    raw_away_scorers = str(g.get("away_scorers", "null"))

    return {
        "id": int(g.get("id", 0)),
        "group": g.get("group", ""),
        "home": home_name,
        "away": away_name,
        "datetime": datetime_normalized,
        "cst": cst_time,
        "stadium": stadium_info.get("name", "Estadio"),
        "city": stadium_info.get("city", "Sede"),
        "country": stadium_info.get("country", ""),
        "altitude_m": stadium_info.get("altitude_m", 0),
        "temperature_c": stadium_info.get("temperature_c", 22),
        "humidity_pct": stadium_info.get("humidity_pct", 50),
        "status": status,
        "minute": minute,
        "score_home": score_home,
        "score_away": score_away,
        "utc_offset": utc_offset,
        "_raw_home_scorers": raw_home_scorers,
        "_raw_away_scorers": raw_away_scorers,
    }


def parse_scorers(home_scorers: str, away_scorers: str) -> list:
    """
    Extrae eventos de gol desde los campos de scorers de la API.

    Formato API: '{"Player Name 45'","Player Name 78'"}'

    Returns:
        Lista de (minuto, "home"|"away") ordenada por minuto.
    """
    import re
    events = []

    for scorers_str, side in [(home_scorers, "home"), (away_scorers, "away")]:
        if not scorers_str or scorers_str == "null":
            continue
        matches = re.findall(r'\"([^"]+\d+)\\\?"', scorers_str)
        if not matches:
            matches = re.findall(r'"([^"]+\d+)\'?"', scorers_str)
        if not matches:
            parts = scorers_str.replace('{', '').replace('}', '').split('","')
            matches = [p.strip().strip('"').strip("'") for p in parts if p.strip()]

        for entry in matches:
            if not entry:
                continue
            nums = re.findall(r'(\d+)', entry)
            if not nums:
                continue
            try:
                minute = int(nums[-1])
                if 0 < minute <= 130:
                    events.append((minute, side))
            except ValueError:
                continue

    return sorted(events, key=lambda x: x[0])

if __name__ == "__main__":
    print("Probando conexión a worldcup26.ir...")
    games = fetch_games()
    if games:
        print(f"Éxito: Se obtuvieron {len(games)} partidos.")
        # Mostrar el primer partido
        print("Muestra:", games[0])
    else:
        print("Fallo al obtener partidos.")
