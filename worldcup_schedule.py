"""
worldcup_schedule.py — Fixture de la Copa del Mundo 2026 (Fase de Grupos).

Contiene los partidos reales con fechas, horarios CST, sede, ciudad,
altitud del estadio, y estado (live/upcoming/finished).

Autor: FutFox Prediction Engine
"""

import time
import copy
from datetime import datetime, timezone, timedelta
from constants import TEAM_NAME_MAP

# Guardar el momento en que se inicia el servidor de simulación
_START_TIME = time.time()

# ── Zona horaria de México (CST, UTC-6) ──────────────────────────
CST = timezone(timedelta(hours=-6))


# ── Countdown para próximos partidos ─────────────────────────────────
def get_countdown(datetime_str: str, utc_offset: int = -6) -> str:
    """
    Retorna un string amigable con el tiempo restante para el partido.
    
    La API devuelve horarios en hora local del estadio. Esta función:
    1. Convierte hora local → UTC usando el utc_offset del estadio
    2. Compara contra UTC real para calcular el tiempo restante
    3. Muestra el resultado en hora CDMX (CST = UTC-6)
    
    Args:
        datetime_str: formato "YYYY-MM-DD HH:MM" o "MM/DD/YYYY HH:MM"
        utc_offset: offset UTC del estadio donde se juega (default -6 = CST)
    
    Returns:
        "Falta Xh Xm (HH:MM CDMX)", "🔴 EN VIVO", "✅ Finalizado"
    """
    if not datetime_str or datetime_str == "N/A":
        return "—"
    try:
        # Intentar formato API: "MM/DD/YYYY HH:MM"
        if "/" in datetime_str:
            match_time_local = datetime.strptime(datetime_str, "%m/%d/%Y %H:%M")
        else:
            match_time_local = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return datetime_str  # devolver tal cual si no se puede parsear

    # Convertir hora local del estadio → UTC → comparar
    tz_stadium = timezone(timedelta(hours=utc_offset))
    match_utc = match_time_local.replace(tzinfo=tz_stadium)
    now_utc = datetime.now(timezone.utc)
    diff = match_utc - now_utc
    total_seconds = diff.total_seconds()

    # Hora CDMX para display
    match_cst = match_utc.astimezone(CST)
    cst_display = match_cst.strftime("%H:%M")
    
    if total_seconds < -7200:   # terminó hace más de 2 horas
        return f"✅ Finalizado"
    if total_seconds < 0:       # en vivo (empezó hace menos de 2h)
        return f"🔴 EN VIVO"
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    if hours > 0:
        return f"Falta {hours}h {minutes}m ({cst_display} CDMX)"
    return f"Falta {minutes}m ({cst_display} CDMX)"


def get_match_status(match: dict) -> str:
    """
    Retorna el status real del partido usando datos de la API, no heurística.
    
    Usa el campo 'status' del partido (ya parseado por _map_api_game)
    que refleja exactamente lo que la API reporta.
    """
    status = match.get("status", "upcoming")
    
    if status == "live":
        minute = match.get("minute", 0)
        score_h = match.get("score_home") or 0
        score_a = match.get("score_away") or 0
        return f"🔴 EN VIVO {minute}' ({score_h}-{score_a})"
    
    if status == "finished":
        score_h = match.get("score_home") or 0
        score_a = match.get("score_away") or 0
        return f"✅ Finalizado ({score_h}-{score_a})"
    
    # upcoming: mostrar countdown con timezone del estadio
    return get_countdown(match.get("datetime", ""), match.get("utc_offset", -6))

# Fase de Grupos — Copa del Mundo 2026
# Datos basados en el fixture oficial FIFA
# Horarios en CST (UTC-6)

FIXTURE = [
    # ── Partidos EN VIVO (26 de junio 2026) ──────────────────────────
    {
        "id": 1,
        "group": "A",
        "home": "Cabo Verde",
        "away": "Arabia Saudita",
        "datetime": "2026-06-26 19:00",
        "cst": "19:00",
        "stadium": "Houston Stadium",
        "city": "Houston",
        "country": "Estados Unidos",
        "altitude_m": 13,
        "temperature_c": 34,
        "humidity_pct": 75,
        "status": "live",
        "minute": 66,
        "score_home": 0,
        "score_away": 0,
    },
    {
        "id": 2,
        "group": "B",
        "home": "Uruguay",
        "away": "España",
        "datetime": "2026-06-26 19:00",
        "cst": "19:00",
        "stadium": "Estadio Akron",
        "city": "Guadalajara",
        "country": "México",
        "altitude_m": 1566,
        "temperature_c": 28,
        "humidity_pct": 45,
        "status": "live",
        "minute": 66,
        "score_home": 0,
        "score_away": 1,
    },

    # ── Próximos partidos HOY (26 de junio) ──────────────────────────
    {
        "id": 3,
        "group": "C",
        "home": "Nueva Zelanda",
        "away": "Bélgica",
        "datetime": "2026-06-26 21:00",
        "cst": "21:00",
        "stadium": "BC Place",
        "city": "Vancouver",
        "country": "Canadá",
        "altitude_m": 2,
        "temperature_c": 18,
        "humidity_pct": 65,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },
    {
        "id": 4,
        "group": "D",
        "home": "Egipto",
        "away": "Irán",
        "datetime": "2026-06-26 21:00",
        "cst": "21:00",
        "stadium": "Seattle Stadium",
        "city": "Seattle",
        "country": "Estados Unidos",
        "altitude_m": 53,
        "temperature_c": 22,
        "humidity_pct": 60,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },

    # ── Próximos partidos MAÑANA (27 de junio) ───────────────────────
    {
        "id": 5,
        "group": "E",
        "home": "México",
        "away": "Japón",
        "datetime": "2026-06-27 14:00",
        "cst": "14:00",
        "stadium": "Estadio Azteca",
        "city": "Ciudad de México",
        "country": "México",
        "altitude_m": 2240,
        "temperature_c": 24,
        "humidity_pct": 40,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },
    {
        "id": 6,
        "group": "E",
        "home": "Francia",
        "away": "Senegal",
        "datetime": "2026-06-27 17:00",
        "cst": "17:00",
        "stadium": "AT&T Stadium",
        "city": "Arlington",
        "country": "Estados Unidos",
        "altitude_m": 181,
        "temperature_c": 32,
        "humidity_pct": 55,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },
    {
        "id": 7,
        "group": "F",
        "home": "Argentina",
        "away": "Portugal",
        "datetime": "2026-06-27 19:00",
        "cst": "19:00",
        "stadium": "MetLife Stadium",
        "city": "East Rutherford",
        "country": "Estados Unidos",
        "altitude_m": 3,
        "temperature_c": 26,
        "humidity_pct": 60,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },
    {
        "id": 8,
        "group": "G",
        "home": "Brasil",
        "away": "Alemania",
        "datetime": "2026-06-27 19:00",
        "cst": "19:00",
        "stadium": "SoFi Stadium",
        "city": "Inglewood",
        "country": "Estados Unidos",
        "altitude_m": 38,
        "temperature_c": 24,
        "humidity_pct": 50,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },

    # ── 28 de junio ──────────────────────────────────────────────────
    {
        "id": 9,
        "group": "H",
        "home": "Inglaterra",
        "away": "Croacia",
        "datetime": "2026-06-28 14:00",
        "cst": "14:00",
        "stadium": "Mercedes-Benz Stadium",
        "city": "Atlanta",
        "country": "Estados Unidos",
        "altitude_m": 320,
        "temperature_c": 30,
        "humidity_pct": 70,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },
    {
        "id": 10,
        "group": "H",
        "home": "Italia",
        "away": "Estados Unidos",
        "datetime": "2026-06-28 17:00",
        "cst": "17:00",
        "stadium": "Hard Rock Stadium",
        "city": "Miami",
        "country": "Estados Unidos",
        "altitude_m": 2,
        "temperature_c": 32,
        "humidity_pct": 80,
        "status": "upcoming",
        "minute": 0,
        "score_home": None,
        "score_away": None,
    },

    # === 27 junio (odds casa Mexico) ===
    {"id":11,"group":"H","home":"Panama","away":"Inglaterra","datetime":"2026-06-27 15:00","cst":"15:00","stadium":"NRG Stadium","city":"Houston","country":"Estados Unidos","altitude_m":13,"temperature_c":34,"humidity_pct":75,"status":"live","minute":15,"score_home":0,"score_away":1},
    {"id":12,"group":"H","home":"Croacia","away":"Ghana","datetime":"2026-06-27 15:00","cst":"15:00","stadium":"AT&T Stadium","city":"Arlington","country":"Estados Unidos","altitude_m":181,"temperature_c":32,"humidity_pct":55,"status":"live","minute":15,"score_home":1,"score_away":0},
    {"id":13,"group":"F","home":"Colombia","away":"Portugal","datetime":"2026-06-27 17:30","cst":"17:30","stadium":"MetLife Stadium","city":"East Rutherford","country":"Estados Unidos","altitude_m":3,"temperature_c":26,"humidity_pct":60,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":14,"group":"I","home":"Congo DR","away":"Uzbekistan","datetime":"2026-06-27 17:30","cst":"17:30","stadium":"Lincoln Financial Field","city":"Philadelphia","country":"Estados Unidos","altitude_m":12,"temperature_c":28,"humidity_pct":65,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":15,"group":"F","home":"Jordania","away":"Argentina","datetime":"2026-06-27 20:00","cst":"20:00","stadium":"Estadio Azteca","city":"Ciudad de Mexico","country":"Mexico","altitude_m":2240,"temperature_c":24,"humidity_pct":40,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":16,"group":"J","home":"Argelia","away":"Austria","datetime":"2026-06-27 20:00","cst":"20:00","stadium":"Levis Stadium","city":"Santa Clara","country":"Estados Unidos","altitude_m":10,"temperature_c":22,"humidity_pct":50,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":17,"group":"J","home":"Sudafrica","away":"Canada","datetime":"2026-06-28 13:00","cst":"13:00","stadium":"BC Place","city":"Vancouver","country":"Canada","altitude_m":2,"temperature_c":18,"humidity_pct":65,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":18,"group":"G","home":"Brasil","away":"Japon","datetime":"2026-06-29 11:00","cst":"11:00","stadium":"Estadio Akron","city":"Guadalajara","country":"Mexico","altitude_m":1566,"temperature_c":28,"humidity_pct":45,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":19,"group":"G","home":"Alemania","away":"Paraguay","datetime":"2026-06-29 14:30","cst":"14:30","stadium":"BMO Field","city":"Toronto","country":"Canada","altitude_m":76,"temperature_c":22,"humidity_pct":55,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":20,"group":"K","home":"Paises Bajos","away":"Marruecos","datetime":"2026-06-29 19:00","cst":"19:00","stadium":"Gillette Stadium","city":"Foxborough","country":"Estados Unidos","altitude_m":87,"temperature_c":24,"humidity_pct":55,"status":"upcoming","minute":0,"score_home":None,"score_away":None},
    {"id":21,"group":"K","home":"Costa de Marfil","away":"Noruega","datetime":"2026-06-30 11:00","cst":"11:00","stadium":"Lumen Field","city":"Seattle","country":"Estados Unidos","altitude_m":53,"temperature_c":20,"humidity_pct":60,"status":"upcoming","minute":0,"score_home":None,"score_away":None},

]


def _get_live_matches_fallback() -> list:
    """Retorna los partidos en vivo del FIXTURE hardcodeado (último recurso)."""
    return [copy.deepcopy(m) for m in FIXTURE if m["status"] == "live"]


def _map_api_game(g: dict) -> dict:
    """Mapea un partido de la API worldcup26.ir a la estructura interna de FutFox.
    Normaliza nombres de equipos usando TEAM_NAME_MAP (inglés → español)."""
    import live_api
    stadium_id = str(g.get("stadium_id", ""))
    stadium_info = live_api.get_stadium_info(stadium_id)

    # ── Nombres de equipos normalizados ────────────────────────────
    home_en = g.get("home_team_name_en", "")
    away_en = g.get("away_team_name_en", "")
    home_label = g.get("home_team_label", "")
    away_label = g.get("away_team_label", "")
    
    # Si es un placeholder (ej: "Winner Match 86"), usar el label
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
        status = "finished"
        minute = 90
    elif time_elapsed == "notstarted" or time_elapsed == "none" or time_elapsed == "":
        status = "upcoming"
        minute = 0
    elif time_elapsed.isdigit():
        # Minuto numérico simple (ej: "66")
        status = "live"
        minute = int(time_elapsed)
    else:
        # Formato con comilla: "45+2'", "90+4'"
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

    # Horario local (extraer hora)
    local_date_str = g.get("local_date", "")
    cst_time = "N/A"
    if local_date_str and " " in local_date_str:
        try:
            cst_time = local_date_str.split(" ")[1][:5]  # e.g. "21:00"
        except Exception:
            pass

    # Convertir formato de fecha API "MM/DD/YYYY HH:MM" a "YYYY-MM-DD HH:MM"
    datetime_normalized = local_date_str
    if "/" in local_date_str:
        try:
            dt = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            datetime_normalized = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass

    # UTC offset del estadio (para convertir hora local → UTC → CST)
    utc_offset = stadium_info.get("utc_offset", -6)

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
    }


def _sort_by_datetime(matches: list) -> list:
    """Ordena partidos por fecha/hora más cercana primero."""
    def sort_key(m):
        dt = m.get("datetime", "")
        if dt and dt != "N/A":
            try:
                return datetime.strptime(dt, "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass
        return datetime(2099, 1, 1)  # mandar al final si no se puede parsear
    return sorted(matches, key=sort_key)


def get_live_matches() -> list:
    """Retorna los partidos que están en vivo ahora (API → fallback)."""
    import live_api
    api_games = live_api.fetch_games()
    
    if api_games is not None:
        live_games = []
        for g in api_games:
            mapped = _map_api_game(g)
            if mapped["status"] == "live":
                live_games.append(mapped)
        # Si la API funciona, confiamos en sus datos (no mezclar con FIXTURE)
        return _sort_by_datetime(live_games)
    
    # Fallback: fixture hardcodeado (solo si la API no responde)
    fallback = [copy.deepcopy(m) for m in FIXTURE if m["status"] == "live"]
    return _sort_by_datetime(fallback)


def get_upcoming_matches() -> list:
    """Retorna los próximos partidos (no empezados), ordenados por fecha."""
    import live_api
    api_games = live_api.fetch_games()
    
    if api_games is not None:
        upcoming_games = []
        for g in api_games:
            mapped = _map_api_game(g)
            if mapped["status"] == "upcoming":
                upcoming_games.append(mapped)
        # Filtrar placeholders (sin equipos reales)
        upcoming_games = [
            m for m in upcoming_games
            if m["home"] and m["away"]
            and "Winner" not in m["home"] and "Winner" not in m["away"]
            and "Runner" not in m["home"] and "Runner" not in m["away"]
            and "Loser" not in m["home"] and "Loser" not in m["away"]
        ]
        return _sort_by_datetime(upcoming_games)
    
    # Fallback: fixture hardcodeado
    return _sort_by_datetime([m for m in FIXTURE if m["status"] == "upcoming"])


def get_all_matches() -> list:
    """Retorna todos los partidos del fixture (API → fallback)."""
    import live_api
    api_games = live_api.fetch_games()
    
    if api_games is not None:
        return _sort_by_datetime([_map_api_game(g) for g in api_games])
    
    return FIXTURE