"""
worldcup_schedule.py — Fixture de la Copa del Mundo 2026 (Fase de Grupos).

Contiene los partidos reales con fechas, horarios CST, sede, ciudad,
altitud del estadio, y estado (live/upcoming/finished).

Autor: FutFox Prediction Engine
"""

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
]


def get_live_matches() -> list:
    """Retorna los partidos que están en vivo ahora."""
    return [m for m in FIXTURE if m["status"] == "live"]


def get_upcoming_matches() -> list:
    """Retorna los próximos partidos (no empezados)."""
    return [m for m in FIXTURE if m["status"] == "upcoming"]


def get_all_matches() -> list:
    """Retorna todos los partidos del fixture."""
    return FIXTURE