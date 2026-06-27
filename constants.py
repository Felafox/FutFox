"""
constants.py — Constantes centralizadas del FutFox Prediction Engine.

Todas las constantes del proyecto viven aquí para evitar "magic numbers"
dispersos en los módulos. Si necesitás modificar un parámetro del modelo,
hacelo aquí y se reflejará en todo el sistema.

Autor: FutFox Prediction Engine
"""

# ---------------------------------------------------------------------------
# Configuración de liga por defecto
# ---------------------------------------------------------------------------
DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = 2024
DEFAULT_HOME_TEAM = "Arsenal"
DEFAULT_AWAY_TEAM = "Chelsea"

# ---------------------------------------------------------------------------
# Parámetros del modelo Poisson
# ---------------------------------------------------------------------------

# Ventaja de local (Home Advantage Factor γ)
# Basado en estudios de ligas europeas: el equipo local marca ~1.36x más
# goles de lo esperado en campo neutral.
# Ref: Dixon & Coles (1997) "Modelling Association Football Scores"
#      Pollard (2006) "Worldwide regional variations in home advantage"
HOME_ADVANTAGE = 1.36

# Porcentaje histórico de goles marcados por el equipo local en la Premier League
# Ref: https://www.soccerstats.com/homeaway.asp
HOME_GOAL_SHARE = 0.58

# Máximo de goles a considerar en la matriz de probabilidad conjunta
# (probabilidades para >10 goles son despreciables en partidos reales)
MAX_GOALS = 10

# Mínimo valor permitido para λ (evitar λ = 0 que rompe la Poisson)
MIN_LAMBDA = 0.01

# Máximo valor permitido para λ (sanity check: >5 goles esperados es irreal
# incluso para el mejor equipo contra el peor)
MAX_LAMBDA = 5.0

# Umbral de advertencia para λ: si λ supera este valor, se emite un warning
# (no bloquea la predicción, solo advierte de posible anomalía)
LAMBDA_WARN_THRESHOLD = 3.0

# Umbral de advertencia para probabilidad de un resultado: si algún resultado
# (local/empate/visitante) supera este valor, se emite un warning
PROB_DOMINANCE_WARN = 0.75

# ---------------------------------------------------------------------------
# Parámetros del modelo de impacto de jugadores
# ---------------------------------------------------------------------------

# Número de jugadores clave a considerar por equipo
TOP_N_PLAYERS = 3

# Factor de sensibilidad β: controla cuánto influye el rendimiento
# individual de los jugadores en la predicción del equipo.
#   - 0.10: conservador (los jugadores importan poco)
#   - 0.15: moderado (recomendado, balance entre equipo e individuo)
#   - 0.25: agresivo (mucha influencia de las estrellas)
BETA = 0.15

# Mínimo de minutos jugados para considerar a un jugador como "clave"
# (~5 partidos completos). Evita que suplentes con pocos minutos pero
# alto ratio por 90min distorsionen el análisis.
MIN_MINUTES = 450

# Rango permitido para el factor α (evita distorsiones extremas)
ALPHA_MIN = 0.80
ALPHA_MAX = 1.20

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

# Tolerancia para verificar que las probabilidades sumen ~100%
PROB_SUM_TOLERANCE = 0.01  # ±1%

# Ventaja de local en torneos internacionales (sede neutral parcial)
# Menor que en ligas domésticas porque pocos equipos juegan de local real.
# Ref: Pollard (2006) para torneos internacionales
WORLD_CUP_HOME_ADVANTAGE = 1.15

# Máximo xG+xA por 90 minutos esperado para un jugador real
# (incluso Messi en su mejor temporada rondaba ~1.5 xGI/90)
MAX_XGI_PER90 = 2.5

# ---------------------------------------------------------------------------
# Reintentos de conexión a Understat
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos entre reintentos

# ---------------------------------------------------------------------------
# Rutas de caché y datos
# ---------------------------------------------------------------------------
DATA_DIR = "data"
CACHE_DIR = "data/cache"
PREDICTIONS_LOG_PATH = "data/predictions.jsonl"

# ---------------------------------------------------------------------------
# WorldCup26.ir API (datos en tiempo real del Mundial 2026)
# API gratuita, sin autenticación. Fuente: https://worldcup26.ir
# ---------------------------------------------------------------------------
WORLDCUP_API_BASE_URL = "https://worldcup26.ir"
LIVE_CACHE_TTL = 60       # segundos — caché de partidos (refrescar cada minuto)
STATIC_CACHE_TTL = 300    # segundos — caché de equipos/estadios (cada 5 min)
API_TIMEOUT = 5            # segundos — timeout de conexión a la API

# ---------------------------------------------------------------------------
# The Odds API (cuotas de casas de apuestas)
# ---------------------------------------------------------------------------

# Registrate gratis en https://the-odds-api.com para obtener tu API key
# La app lee de st.secrets en Streamlit Cloud o variable de entorno FUTFOX_ODDS_API_KEY.
# Si está vacío, la app funciona con odds sintéticas.
THE_ODDS_API_KEY = ""

# Al importar, intentar override desde Streamlit secrets o variable de entorno
try:
    import os as _os
    _env_key = _os.environ.get("FUTFOX_ODDS_API_KEY", "")
    if _env_key:
        THE_ODDS_API_KEY = _env_key
except Exception:
    pass
try:
    import streamlit as _st
    _secret_key = _st.secrets.get("THE_ODDS_API_KEY", "")
    if _secret_key:
        THE_ODDS_API_KEY = _secret_key
except Exception:
    pass
THE_ODDS_API_URL = "https://api.the-odds-api.com/v4"

# Peso del modelo FutFox vs el mercado en el ensemble (0-1)
# 0.4 = 40% modelo FutFox, 60% consenso del mercado
ENSEMBLE_WEIGHT = 0.4

# Bookmakers a consultar (separados por coma, máx 3 en free tier)
ODDS_BOOKMAKERS = "pinnacle,bet365"

# Regiones para odds
ODDS_REGIONS = "us,eu,uk"

# Tiempo de caché de odds (segundos) — free tier: 500 req/mes
ODDS_CACHE_TTL = 3600  # 1 hora

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Mapa de nombres de equipos: API (inglés) → UI / Fallback (español)
# La API worldcup26.ir retorna nombres en inglés; los fallbacks y odds usan
# español. Este mapa unifica ambos mundos.
# ---------------------------------------------------------------------------
TEAM_NAME_MAP = {
    "Panama": "Panamá", "England": "Inglaterra", "Croatia": "Croacia",
    "Ghana": "Ghana", "Colombia": "Colombia", "Portugal": "Portugal",
    "Democratic Republic of the Congo": "Congo DR",
    "Uzbekistan": "Uzbekistán", "Jordan": "Jordania",
    "Argentina": "Argentina", "Algeria": "Argelia", "Austria": "Austria",
    "South Africa": "Sudáfrica", "Canada": "Canadá", "Brazil": "Brasil",
    "Japan": "Japón", "Germany": "Alemania", "Paraguay": "Paraguay",
    "Netherlands": "Países Bajos", "Morocco": "Marruecos",
    "Ivory Coast": "Costa de Marfil", "Norway": "Noruega",
    "Mexico": "México", "South Korea": "Corea del Sur",
    "Senegal": "Senegal", "France": "Francia", "Spain": "España",
    "Uruguay": "Uruguay", "Iran": "Irán", "New Zealand": "Nueva Zelanda",
    "Egypt": "Egipto", "Belgium": "Bélgica", "Saudi Arabia": "Arabia Saudita",
    "Cape Verde": "Cabo Verde", "United States": "Estados Unidos",
    "Ecuador": "Ecuador", "Italy": "Italia", "Denmark": "Dinamarca",
    "Nigeria": "Nigeria", "Cameroon": "Camerún", "Serbia": "Serbia",
    "Switzerland": "Suiza", "Tunisia": "Túnez", "Australia": "Australia",
    "Sweden": "Suecia", "Peru": "Perú", "Chile": "Chile",
    "Costa Rica": "Costa Rica", "Qatar": "Qatar", "Turkey": "Turquía",
    "Bosnia and Herzegovina": "Bosnia y Herzegovina",
    "Iraq": "Irak", "Haiti": "Haití", "Scotland": "Escocia",
    "Curaçao": "Curazao", "Czech Republic": "República Checa",
    "Sudan": "Sudán", "Greece": "Grecia", "Wales": "Gales",
    "Ukraine": "Ucrania", "Poland": "Polonia", "Romania": "Rumania",
    "Slovakia": "Eslovaquia", "Hungary": "Hungría", "Bulgaria": "Bulgaria",
    "Ireland": "Irlanda", "Finland": "Finlandia",
    "Venezuela": "Venezuela", "Bolivia": "Bolivia",
}

# ---------------------------------------------------------------------------
# Auto-refresh de la UI (Streamlit)
# ---------------------------------------------------------------------------
AUTO_REFRESH_SECONDS = 60  # segundos entre recargas automáticas

# ---------------------------------------------------------------------------
# Formatos de display
# ---------------------------------------------------------------------------
SEPARATOR = "═" * 70
SEPARATOR_THIN = "─" * 70
BAR_LENGTH = 40  # caracteres para las barras de probabilidad visual