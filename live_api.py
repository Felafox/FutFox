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

def get_team_info_by_id(team_id: str) -> dict:
    """Mapea team_id a info del equipo (nombre inglés/bandera)."""
    global _team_map
    if not _team_map:
        teams = fetch_teams()
        if teams:
            for t in teams:
                t_id = str(t.get("id"))
                _team_map[t_id] = {
                    "name": t.get("name_en"),
                    "flag": t.get("flag"),
                    "fifa_code": t.get("fifa_code")
                }
    return _team_map.get(str(team_id), {})

if __name__ == "__main__":
    print("Probando conexión a worldcup26.ir...")
    games = fetch_games()
    if games:
        print(f"Éxito: Se obtuvieron {len(games)} partidos.")
        # Mostrar el primer partido
        print("Muestra:", games[0])
    else:
        print("Fallo al obtener partidos.")
