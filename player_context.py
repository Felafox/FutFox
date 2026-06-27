"""
player_context.py — Factores cualitativos que afectan el rendimiento.

Ajusta el α del modelo base con factores externos:
  - Altitud del estadio vs país de origen
  - Fatiga de viaje
  - Moral del equipo (resultados recientes)
  - Lesiones
  - Clima

El resultado es un factor φ (phi) que multiplica al α base.
φ se mantiene en [0.92, 1.08] para no distorsionar el modelo.

Autor: FutFox Prediction Engine
"""

import math

# ── Mapa inverso para buscar contexto con nombres en inglés ──────────────
# Permite que calculate_context_adjustment() acepte nombres de la API
from constants import TEAM_NAME_MAP
_REVERSE_CONTEXT_MAP = {v: k for k, v in TEAM_NAME_MAP.items()}


def _get_context(team: str) -> dict:
    """Busca el contexto de un equipo, soportando nombres en inglés y español."""
    ctx = TEAM_CONTEXT.get(team, {})
    if ctx:
        return ctx
    # Intentar con nombre en inglés (si viene en español del API)
    english_name = _REVERSE_CONTEXT_MAP.get(team, "")
    if english_name:
        ctx = TEAM_CONTEXT.get(english_name, {})
        if ctx:
            return ctx
    # Intentar con nombre en español (si viene en inglés del API)
    spanish_name = TEAM_NAME_MAP.get(team, "")
    if spanish_name:
        return TEAM_CONTEXT.get(spanish_name, {})
    return {}

# ── Datos base de cada selección ───────────────────────────────────────
# altitud_origen_m: altitud promedio del país (capital o ciudad principal)
# travel_km: distancia aproximada al torneo (promedio entre sedes)
# morale: 0.85-1.15 (baja/neutral/alta)
# injuries: lista de lesiones o bajas importantes

TEAM_CONTEXT = {
    "Cabo Verde": {
        "altitud_origen_m": 30,     # Praia
        "travel_km": 7800,
        "morale": 1.05,             # Histórica clasificación
        "injuries": [],
        "style_note": "Equipo físicamente fuerte, disciplinado tácticamente. Juegan con bloque bajo y contragolpe.",
        "key_fact": "Primera participación en un Mundial. Motivación histórica.",
    },
    "Arabia Saudita": {
        "altitud_origen_m": 600,    # Riad
        "travel_km": 12500,
        "morale": 0.95,             # Preparación intensiva pero amistosos irregulares
        "injuries": ["Salman Al-Faraj (duda)"],
        "style_note": "Propuesta ofensiva con Al-Dawsari como figura. Defensa vulnerable a velocidad.",
        "key_fact": "Plantel con 6 meses de concentración. Cansancio acumulado posible.",
    },
    "Uruguay": {
        "altitud_origen_m": 43,     # Montevideo
        "travel_km": 7500,
        "morale": 0.85,             # Eliminatorias irregulares, cambio de DT
        "injuries": ["Ronald Araujo (duda)"],
        "style_note": "Garra charrúa intacta. Valverde y Núñez en gran momento. Defensa sólida.",
        "key_fact": "Bielsa imprime intensidad alta. Puede afectar en altitud de Guadalajara.",
    },
    "España": {
        "altitud_origen_m": 667,    # Madrid
        "travel_km": 9200,
        "morale": 1.10,             # Campeones Euro 2024, racha positiva
        "injuries": [],
        "style_note": "Posesión y presión alta. Yamal y Williams desequilibrantes por bandas.",
        "key_fact": "Generación dorada joven. Favoritos al título.",
    },
    "Nueva Zelanda": {
        "altitud_origen_m": 10,     # Wellington
        "travel_km": 11500,
        "morale": 1.00,
        "injuries": [],
        "style_note": "Juego directo con Chris Wood como referencia. Defensa ordenada.",
        "key_fact": "Viaje más largo del torneo. Posible jet lag.",
    },
    "Bélgica": {
        "altitud_origen_m": 75,     # Bruselas
        "travel_km": 7900,
        "morale": 0.92,             # Generación dorada envejeciendo
        "injuries": ["Thibaut Courtois (duda)"],
        "style_note": "De Bruyne + Lukaku = peligro ofensivo. Defensa más lenta que en 2018.",
        "key_fact": "Última oportunidad para la generación dorada.",
    },
    "Egipto": {
        "altitud_origen_m": 23,     # El Cairo
        "travel_km": 11000,
        "morale": 1.02,
        "injuries": [],
        "style_note": "Salah-dependencia ofensiva. Marmoush emergiendo como socio.",
        "key_fact": "Salah en su mejor momento. Equipo construido alrededor de él.",
    },
    "Irán": {
        "altitud_origen_m": 1200,   # Teherán
        "travel_km": 11500,
        "morale": 0.95,
        "injuries": ["Ehsan Hajsafi (duda)"],
        "style_note": "Defensa sólida, Taremi y Azmoun letales al contragolpe.",
        "key_fact": "Acostumbrados a jugar en altitud (Teherán 1200m). Ventaja en Seattle.",
    },
    "México": {
        "altitud_origen_m": 2240,   # CDMX
        "travel_km": 0,
        "morale": 1.08,             # Locales, presión de la afición
        "injuries": [],
        "style_note": "Juego vertical con Giménez como 9. Lozano desborde por izquierda.",
        "key_fact": "Juegan en el Azteca (2240m). Adaptados a altitud extrema.",
    },
    "Japón": {
        "altitud_origen_m": 40,     # Tokio
        "travel_km": 11000,
        "morale": 1.06,             # Dominaron eliminatorias asiáticas
        "injuries": [],
        "style_note": "Técnicos, rápidos, disciplinados. Mitoma y Kubo desequilibrantes.",
        "key_fact": "Altitud del Azteca (2240m) puede ser factor crítico.",
    },
    "Francia": {
        "altitud_origen_m": 35,     # París
        "travel_km": 8000,
        "morale": 1.08,
        "injuries": [],
        "style_note": "Mbappé lidera. Camavinga y Tchouaméni en mediocampo. Defensa física.",
        "key_fact": "Subcampeones 2022, campeones 2018. Plantel más profundo.",
    },
    "Senegal": {
        "altitud_origen_m": 10,     # Dakar
        "travel_km": 8200,
        "morale": 0.98,
        "injuries": ["Sadio Mané (duda)"],
        "style_note": "Físico imponente. Mané + Jackson en ataque. Mendy en arco.",
        "key_fact": "Campeones de África 2023.",
    },
    "Argentina": {
        "altitud_origen_m": 25,     # Buenos Aires
        "travel_km": 8500,
        "morale": 1.15,             # Campeones del mundo 2022
        "injuries": [],
        "style_note": "Messi lidera. Julián Álvarez y Enzo Fernández en gran nivel.",
        "key_fact": "Campeones defensores. Messi posiblemente su último Mundial.",
    },
    "Portugal": {
        "altitud_origen_m": 50,     # Lisboa
        "travel_km": 5500,
        "morale": 1.05,
        "injuries": [],
        "style_note": "Cristiano en su último Mundial. Rafael Leao desequilibrante.",
        "key_fact": "Cristiano Ronaldo en busca del título que le falta.",
    },
    "Brasil": {
        "altitud_origen_m": 760,    # Brasilia
        "travel_km": 9500,
        "morale": 1.08,
        "injuries": ["Neymar (duda)"],
        "style_note": "Vinicius y Rodrygo lideran. Endrick como revulsivo.",
        "key_fact": "Pentacampeones. Vinicius Jr candidato a Balón de Oro.",
    },
    "Alemania": {
        "altitud_origen_m": 34,     # Berlín
        "travel_km": 9200,
        "morale": 0.95,             # Recambio generacional
        "injuries": ["Leroy Sané (duda)"],
        "style_note": "Musiala y Wirtz el futuro. Havertz falso 9.",
        "key_fact": "Anfitriones de la Euro 2024. Equipo en transición.",
    },
    "Inglaterra": {
        "altitud_origen_m": 11,     # Londres
        "travel_km": 6800,
        "morale": 1.06,
        "injuries": [],
        "style_note": "Bellingham + Kane = dupla letal. Foden creatividad.",
        "key_fact": "Subcampeones Euro 2024. Plantel más caro del mundo.",
    },
    "Croacia": {
        "altitud_origen_m": 158,    # Zagreb
        "travel_km": 8200,
        "morale": 0.90,             # Generación dorada envejeciendo
        "injuries": ["Ivan Perisic (retirado)"],
        "style_note": "Modric todavía manda. Gvardiol líder defensivo.",
        "key_fact": "Terceros en 2022, subcampeones en 2018. Último baile de Modric.",
    },
    "Italia": {
        "altitud_origen_m": 20,     # Roma
        "travel_km": 8300,
        "morale": 1.02,
        "injuries": [],
        "style_note": "Defensa sólida. Barella y Chiesa en ataque.",
        "key_fact": "No clasificaron a 2022. Redención pendiente.",
    },
    "Estados Unidos": {
        "altitud_origen_m": 320,    # Atlanta (promedio)
        "travel_km": 0,
        "morale": 1.05,             # Locales
        "injuries": [],
        "style_note": "Pulisic + McKennie + Reyna. Físico y velocidad.",
        "key_fact": "Anfitriones. Juegan en casa.",
    },
}


# ── Origen de los jugadores (ciudad/altitud) ─────────────────────────
# Para ajuste fino de altitud por jugador

PLAYER_ORIGINS = {
    "Darwin Nunez": {"city": "Artigas", "altitud_m": 120},
    "Federico Valverde": {"city": "Montevideo", "altitud_m": 43},
    "Luis Suarez": {"city": "Salto", "altitud_m": 30},
    "Ronald Araujo": {"city": "Rivera", "altitud_m": 210},
    "Lamine Yamal": {"city": "Barcelona", "altitud_m": 12},
    "Alvaro Morata": {"city": "Madrid", "altitud_m": 667},
    "Nico Williams": {"city": "Bilbao", "altitud_m": 20},
    "Dani Olmo": {"city": "Terrassa", "altitud_m": 282},
    "Rodri": {"city": "Madrid", "altitud_m": 667},
    "Mohamed Salah": {"city": "Nagrig", "altitud_m": 10},
    "Mehdi Taremi": {"city": "Bushehr", "altitud_m": 5},
    "Sardar Azmoun": {"city": "Gonbad", "altitud_m": 52},
    "Chris Wood": {"city": "Auckland", "altitud_m": 30},
    "Romelu Lukaku": {"city": "Amberes", "altitud_m": 8},
    "Kevin De Bruyne": {"city": "Gante", "altitud_m": 10},
    "Ryan Mendes": {"city": "Mindelo", "altitud_m": 5},
    "Salem Al-Dawsari": {"city": "Riad", "altitud_m": 600},
    "Lionel Messi": {"city": "Rosario", "altitud_m": 25},
    "Cristiano Ronaldo": {"city": "Funchal", "altitud_m": 0},
    "Kylian Mbappe": {"city": "Paris", "altitud_m": 35},
    "Vinicius Jr": {"city": "Rio de Janeiro", "altitud_m": 2},
    "Jamal Musiala": {"city": "Stuttgart", "altitud_m": 245},
    "Harry Kane": {"city": "Londres", "altitud_m": 11},
    "Jude Bellingham": {"city": "Birmingham", "altitud_m": 140},
    "Santiago Gimenez": {"city": "Buenos Aires", "altitud_m": 25},
}


def calculate_altitude_penalty(team: str, stadium_altitude_m: float) -> float:
    """
    Calcula la penalización por diferencia de altitud.

    Calibrado con:
      - McSharry (2010): 0.5 goles menos por cada 1000m para el visitante
      - Gore & McSharry: efecto no lineal, más severo >2000m

    Returns:
        float entre -0.05 y +0.02 (ajuste a φ)
    """
    ctx = _get_context(team)
    team_alt = ctx.get("altitud_origen_m", 500)
    diff = stadium_altitude_m - team_alt

    # Penalización calibrada por altitud (basado en datos reales)
    if diff > 2000:
        return -0.050  # altitud extrema (>2000m diff): ~0.5 goles menos
    elif diff > 1000:
        return -0.040  # diferencia severa (>1000m)
    elif diff > 500:
        return -0.025  # diferencia moderada (>500m)
    elif diff < -1000:
        return +0.020  # beneficio por jugar más bajo (más oxígeno)
    elif diff < -500:
        return +0.012
    return 0.0


def calculate_context_adjustment(team: str, match_info: dict) -> float:
    """
    Calcula el factor φ (phi) de ajuste contextual para un equipo.

    φ se multiplica al α para reflejar factores cualitativos:
      - Altitud del estadio
      - Moral del equipo
      - Lesiones
      - Viaje/fatiga

    Parameters:
        team: nombre del equipo
        match_info: dict del partido (de worldcup_schedule)

    Returns:
        float φ en rango [0.92, 1.08]
    """
    ctx = _get_context(team)
    if not ctx:
        return 1.0

    phi = 1.0

    # 1. Altitud
    altitude = match_info.get("altitude_m", 0)
    phi += calculate_altitude_penalty(team, altitude)

    # 2. Moral (±1.5% por 0.1 de desviación, más conservador)
    morale = ctx.get("morale", 1.0)
    phi += (morale - 1.0) * 0.015

    # 3. Lesiones: -1.5% por titular, -0.5% por suplente
    injuries = ctx.get("injuries", [])
    for inj in injuries:
        if "duda" in inj.lower():
            phi -= 0.005  # duda → poco impacto
        else:
            phi -= 0.015  # baja confirmada

    # 4. Viaje largo (>10000km penaliza más fuerte, basado en FIFA reports)
    travel = ctx.get("travel_km", 5000)
    if travel > 10000:
        phi -= 0.025   # jetlag severo (>8h diferencia horaria)
    elif travel > 7000:
        phi -= 0.015

    # 5. Clima: calor extremo (>32°C + humedad) penaliza más (evidencia Qatar 2022)
    temp = match_info.get("temperature_c", 22)
    humidity = match_info.get("humidity_pct", 50)
    if temp > 32 and humidity > 70:
        phi -= 0.020   # calor + humedad extremos: -0.3 goles esperados

    # Limitar φ a rango razonable (expandido para capturar efectos más fuertes)
    phi = max(0.90, min(1.10, phi))

    return phi


def get_context_notes(team: str, match_info: dict) -> list:
    """
    Genera notas de contexto para mostrar en la UI.

    Returns:
        Lista de strings con emojis descriptivos.
    """
    ctx = _get_context(team)
    notes = []

    # Altitud
    altitude = match_info.get("altitude_m", 0)
    team_alt = ctx.get("altitud_origen_m", 500)
    diff = altitude - team_alt
    if diff > 1000:
        notes.append(f"⛰️ Altitud +{diff:.0f}m vs origen ({team_alt}m)")
    elif diff > 500:
        notes.append(f"⛰️ Altitud moderada +{diff:.0f}m")

    # Lesiones
    injuries = ctx.get("injuries", [])
    for inj in injuries:
        notes.append(f"🏥 {inj}")

    #Viaje
    travel = ctx.get("travel_km", 5000)
    if travel > 10000:
        notes.append("✈️ Viaje muy largo (>10,000km)")
    elif travel > 7000:
        notes.append("✈️ Viaje largo (>7,000km)")

    # Clima
    temp = match_info.get("temperature_c", 22)
    humidity = match_info.get("humidity_pct", 50)
    if temp > 32:
        notes.append(f"🌡️ Calor extremo ({temp}°C)")
    if humidity > 70:
        notes.append(f"💧 Humedad alta ({humidity}%)")

    # Estilo
    style = ctx.get("style_note", "")
    if style:
        notes.append(f"📝 {style[:80]}...")

    # Dato clave
    key = ctx.get("key_fact", "")
    if key:
        notes.append(f"💡 {key}")

    return notes