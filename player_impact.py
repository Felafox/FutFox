"""
player_impact.py — Análisis de impacto individual de jugadores clave en el
modelo de predicción.

Fundamento:
-----------
Los jugadores con mayor xG + xA acumulado tienen una influencia
desproporcionada en el rendimiento ofensivo de su equipo. Este módulo:

1. Identifica a los 3 jugadores más influyentes de cada equipo (basado en
   xG + xA por 90 minutos, normalizado por minutos jugados).
2. Calcula un factor de ajuste α para cada equipo que modifica el λ del
   modelo Poisson:

   α = 1 + β × [(xG_key + xA_key) / (xG_avg + xA_avg) - 1]

   Donde:
     - xG_key + xA_key = suma de xG+xA por 90min de los 3 jugadores clave
     - xG_avg + xA_avg = promedio de xG+xA por 90min del top 3 de la liga
     - β = factor de sensibilidad que controla cuánto pesa el rendimiento
       individual en el modelo de equipo (default 0.15)

   Intuición:
     - α > 1: los jugadores clave están rindiendo por encima del promedio
              → el equipo se potencia ofensivamente.
     - α < 1: los jugadores clave están por debajo → el equipo se debilita.
     - α = 1: sin efecto (jugadores en la media).

3. Genera la tabla "Jugadores Clave a Seguir" con los top 3 jugadores
   del partido (combinando ambos equipos), ordenados por xG+xA proyectado.

Autor: FutFox Prediction Engine
"""

import warnings
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from constants import (
    ALPHA_MAX,
    ALPHA_MIN,
    BETA,
    MAX_XGI_PER90,
    MIN_MINUTES,
    TOP_N_PLAYERS,
)


# ======================================================================
# Funciones de análisis
# ======================================================================

def calculate_per90_metrics(players_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas por 90 minutos para cada jugador.

    xG_per90 = xG / (minutes / 90)
    xA_per90 = xA / (minutes / 90)
    xGI_per90 = (xG + xA) / (minutes / 90)   [Expected Goal Involvements]

    Parameters
    ----------
    players_df : pd.DataFrame
        DataFrame con columnas: player_name, team, xG, xA, goals, shots, minutes.

    Returns
    -------
    pd.DataFrame
        DataFrame con columnas adicionales xG_per90, xA_per90, xGI_per90.
    """
    df = players_df.copy()

    # Evitar división por cero: reemplazar minutes=0 con NaN
    df["minutes"] = df["minutes"].replace(0, np.nan)

    # Calcular per90 solo donde minutes es válido
    valid_mask = df["minutes"].notna()
    df["xG_per90"] = np.nan
    df["xA_per90"] = np.nan
    df.loc[valid_mask, "xG_per90"] = df.loc[valid_mask, "xG"] / (df.loc[valid_mask, "minutes"] / 90)
    df.loc[valid_mask, "xA_per90"] = df.loc[valid_mask, "xA"] / (df.loc[valid_mask, "minutes"] / 90)
    df["xGI_per90"] = df["xG_per90"] + df["xA_per90"]

    # Sanity check: xGI_per90 no debe exceder MAX_XGI_PER90
    if not df["xGI_per90"].dropna().empty:
        extreme_mask = df["xGI_per90"].notna() & (df["xGI_per90"] > MAX_XGI_PER90)
        if extreme_mask.any():
            for idx in df[extreme_mask].index:
                warnings.warn(
                    f"xGI_per90 = {df.loc[idx, 'xGI_per90']:.2f} para "
                    f"'{df.loc[idx, 'player_name']}' excede MAX_XGI_PER90 = {MAX_XGI_PER90}. "
                    f"Se clampó a {MAX_XGI_PER90}."
                )
            df.loc[extreme_mask, "xGI_per90"] = MAX_XGI_PER90

    # Rellenar NaN en per90 columns con la mediana del equipo;
    # si todo el equipo es NaN, usar 0.0 como fallback de último recurso.
    for col in ["xG_per90", "xA_per90", "xGI_per90"]:
        team_median = df[col].median()
        if pd.isna(team_median):
            team_median = 0.0
        df[col] = df[col].fillna(team_median)

    return df


def identify_key_players(
    players_df: pd.DataFrame,
    top_n: int = TOP_N_PLAYERS,
    min_minutes: int = MIN_MINUTES,
) -> pd.DataFrame:
    """
    Identifica los top N jugadores clave de un equipo basado en xGI_per90
    (Expected Goal Involvements por 90 minutos), filtrando por minutos mínimos.

    Parameters
    ----------
    players_df : pd.DataFrame
        DataFrame de jugadores de UN equipo (debe tener columna 'team').
    top_n : int
        Número de jugadores clave a seleccionar.
    min_minutes : int
        Minutos mínimos para ser considerado.

    Returns
    -------
    pd.DataFrame
        Top N jugadores ordenados por xGI_per90 descendente.
    """
    if players_df.empty:
        return players_df

    df = calculate_per90_metrics(players_df)

    # Filtrar por minutos mínimos
    df = df[df["minutes"] >= min_minutes].copy()

    if df.empty:
        # Si no hay jugadores con suficientes minutos, usar los disponibles
        df = calculate_per90_metrics(players_df)
        print(f"  [WARN] Ningún jugador de {players_df['team'].iloc[0]} "
              f"alcanza {min_minutes} min. Usando todos los disponibles.")

    # Ordenar por xGI_per90 descendente y tomar top N
    key_players = df.nlargest(top_n, "xGI_per90")

    return key_players


def calculate_player_adjustment(
    team_players: pd.DataFrame,
    league_all_players: pd.DataFrame,
    beta: float = BETA,
) -> float:
    """
    Calcula el factor de ajuste α para un equipo basado en el rendimiento
    de sus jugadores clave respecto al promedio de la liga.

    Matemática:
      α = 1 + β × [(xGI_key_avg - xGI_league_avg) / xGI_league_avg]

    Donde:
      xGI_key_avg = promedio de xGI_per90 de los 3 jugadores clave del equipo
      xGI_league_avg = promedio de xGI_per90 de todos los jugadores
                       clave de la liga

    Esta fórmula asegura que α sea simétrico: si los jugadores rinden
    igual que el promedio, α = 1.

    Parameters
    ----------
    team_players : pd.DataFrame
        Jugadores del equipo (ya filtrados a los top N clave).
    league_all_players : pd.DataFrame
        Todos los jugadores de la liga con métricas per90 calculadas.
    beta : float
        Factor de sensibilidad.

    Returns
    -------
    float
        Factor α de ajuste. Rango típico: [0.85, 1.15].
    """
    if team_players.empty or league_all_players.empty:
        return 1.0

    # xGI promedio de los jugadores clave del equipo
    team_xgi_avg = team_players["xGI_per90"].mean()

    # xGI promedio del top 3 de todos los equipos de la liga
    league_all_with_p90 = calculate_per90_metrics(league_all_players)
    league_all_filtered = league_all_with_p90[
        league_all_with_p90["minutes"] >= MIN_MINUTES
    ]
    if league_all_filtered.empty:
        league_all_filtered = league_all_with_p90

    # Tomamos el top N global de la liga para tener una referencia justa
    league_top_avg = league_all_filtered.nlargest(
        TOP_N_PLAYERS * 5, "xGI_per90"  # top 15 para tener una muestra representativa
    )["xGI_per90"].mean()

    if league_top_avg == 0:
        return 1.0

    # Cálculo de α
    relative_performance = (team_xgi_avg - league_top_avg) / league_top_avg
    alpha = 1.0 + beta * relative_performance

    # Limitar α a un rango razonable para evitar distorsiones extremas
    alpha = np.clip(alpha, ALPHA_MIN, ALPHA_MAX)

    return alpha


def compute_team_adjustments(
    home_players: pd.DataFrame,
    away_players: pd.DataFrame,
    league_stats: pd.DataFrame,
    beta: float = BETA,
) -> Tuple[float, float, pd.DataFrame, pd.DataFrame]:
    """
    Calcula los factores de ajuste α para ambos equipos y retorna los
    DataFrames de jugadores clave.

    Parameters
    ----------
    home_players : pd.DataFrame
        Jugadores del equipo local.
    away_players : pd.DataFrame
        Jugadores del equipo visitante.
    league_stats : pd.DataFrame
        Estadísticas de todos los equipos de la liga (para contexto).
    beta : float
        Factor de sensibilidad.

    Returns
    -------
    alpha_home : float
        Factor de ajuste para el equipo local.
    alpha_away : float
        Factor de ajuste para el equipo visitante.
    home_key : pd.DataFrame
        Top 3 jugadores clave del equipo local.
    away_key : pd.DataFrame
        Top 3 jugadores clave del equipo visitante.
    """
    # Identificar jugadores clave de cada equipo
    home_key = identify_key_players(home_players)
    away_key = identify_key_players(away_players)

    # Para el cálculo de α, necesitamos una referencia de liga.
    # Construimos un DataFrame combinado con todos los jugadores disponibles.
    all_players_list = []
    if not home_players.empty:
        all_players_list.append(home_players)
    if not away_players.empty:
        all_players_list.append(away_players)

    if all_players_list:
        all_players = pd.concat(all_players_list, ignore_index=True)
    else:
        all_players = pd.DataFrame()

    alpha_home = calculate_player_adjustment(home_key, all_players, beta)
    alpha_away = calculate_player_adjustment(away_key, all_players, beta)

    return alpha_home, alpha_away, home_key, away_key


def build_key_players_table(
    home_key: pd.DataFrame,
    away_key: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye la tabla "Jugadores Clave a Seguir" combinando los top
    jugadores de ambos equipos, ordenados por xGI_per90 descendente.

    Parameters
    ----------
    home_key : pd.DataFrame
        Jugadores clave del equipo local.
    away_key : pd.DataFrame
        Jugadores clave del equipo visitante.

    Returns
    -------
    pd.DataFrame
        Tabla combinada con columnas: #, Jugador, Equipo, xG/90, xA/90,
        xGI/90 (Expected Goal Involvements por 90 min).
    """
    combined = pd.concat([home_key, away_key], ignore_index=True)

    if combined.empty:
        return pd.DataFrame(columns=["#", "Jugador", "Equipo", "xG/90", "xA/90", "xGI/90"])

    # Ordenar por xGI_per90 descendente
    combined = combined.sort_values("xGI_per90", ascending=False).reset_index(drop=True)

    # Construir tabla formateada
    table = pd.DataFrame({
        "#": range(1, len(combined) + 1),
        "Jugador": combined["player_name"],
        "Equipo": combined["team"],
        "xG/90": combined["xG_per90"].round(2),
        "xA/90": combined["xA_per90"].round(2),
        "xGI/90": combined["xGI_per90"].round(2),
    })

    return table


# ======================================================================
# Función de conveniencia para obtener todo de una vez
# ======================================================================

def analyze_player_impact(
    home_players: pd.DataFrame,
    away_players: pd.DataFrame,
    league_stats: pd.DataFrame,
    beta: float = BETA,
    verbose: bool = True,
) -> Dict:
    """
    Función principal de análisis de impacto de jugadores.

    Realiza el pipeline completo:
    1. Identifica jugadores clave por equipo.
    2. Calcula factores de ajuste α.
    3. Construye la tabla de jugadores clave a seguir.

    Parameters
    ----------
    home_players : pd.DataFrame
    away_players : pd.DataFrame
    league_stats : pd.DataFrame
    beta : float
    verbose : bool
        Si True, imprime información del proceso.

    Returns
    -------
    dict con keys:
        - 'alpha_home': float
        - 'alpha_away': float
        - 'home_key_players': pd.DataFrame
        - 'away_key_players': pd.DataFrame
        - 'key_players_table': pd.DataFrame (tabla combinada para output final)
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"  ANÁLISIS DE IMPACTO DE JUGADORES")
        print(f"{'='*60}")

    alpha_home, alpha_away, home_key, away_key = compute_team_adjustments(
        home_players, away_players, league_stats, beta,
    )

    if verbose:
        home_name = home_players["team"].iloc[0] if not home_players.empty else "Local"
        away_name = away_players["team"].iloc[0] if not away_players.empty else "Visitante"
        print(f"\n  Factores de ajuste (α):")
        print(f"    α {home_name}: {alpha_home:.4f}")
        print(f"    α {away_name}: {alpha_away:.4f}")

        print(f"\n  Jugadores clave {home_name}:")
        if not home_key.empty:
            print(home_key[["player_name", "xG_per90", "xA_per90", "xGI_per90"]]
                  .to_string(index=False))
        else:
            print("    (sin datos)")

        print(f"\n  Jugadores clave {away_name}:")
        if not away_key.empty:
            print(away_key[["player_name", "xG_per90", "xA_per90", "xGI_per90"]]
                  .to_string(index=False))
        else:
            print("    (sin datos)")

    key_table = build_key_players_table(home_key, away_key)

    return {
        "alpha_home": alpha_home,
        "alpha_away": alpha_away,
        "home_key_players": home_key,
        "away_key_players": away_key,
        "key_players_table": key_table,
    }


# ======================================================================
# Ejecución standalone para testing
# ======================================================================
if __name__ == "__main__":
    import sys
    from data_collection import run_collection

    print("Test de player_impact.py\n")

    try:
        league_stats, home_players, away_players, league_avgs, _ = run_collection(
            league="EPL", season=2024,
            home_team="Arsenal", away_team="Chelsea",
        )

        result = analyze_player_impact(
            home_players=home_players,
            away_players=away_players,
            league_stats=league_stats,
            verbose=True,
        )

        print(f"\n--- Tabla Final: Jugadores Clave a Seguir ---")
        print(result["key_players_table"].to_string(index=False))

        print("\n[OK] Test exitoso.")
    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)