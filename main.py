"""
main.py — Orquestador del FutFox Prediction Engine.

Pipeline completo:
  1. Recolectar datos de la liga y equipos (data_collection)
  2. Analizar impacto de jugadores clave (player_impact)
  3. Ejecutar modelo Poisson con ajustes (model_poisson)
  4. Imprimir resultados en consola con formato profesional

Uso:
  python main.py [liga] [temporada] [equipo_local] [equipo_visitante]

  Ejemplos:
    python main.py
    python main.py EPL 2024 Arsenal Chelsea
    python main.py La_Liga 2024 Barcelona "Real Madrid"
    python main.py Serie_A 2024 "Inter Milan" "AC Milan"

Autor: FutFox Prediction Engine
"""

import sys
import traceback
from typing import Tuple

import pandas as pd

# Importar módulos del proyecto
from constants import (
    BAR_LENGTH,
    BETA,
    DEFAULT_AWAY_TEAM,
    DEFAULT_HOME_TEAM,
    DEFAULT_LEAGUE,
    DEFAULT_SEASON,
    HOME_ADVANTAGE,
    SEPARATOR,
    SEPARATOR_THIN,
    WORLD_CUP_HOME_ADVANTAGE,
)
from data_collection import run_collection
from model_poisson import (
    predict_match,
    MatchPrediction,
)


# ---------------------------------------------------------------------------
# Utilidades de formato (movidas desde model_poisson.py)
# ---------------------------------------------------------------------------

def prediction_to_dataframe(pred: MatchPrediction):
    """Convierte MatchPrediction en DataFrames para impresión en consola."""
    summary_data = {
        "Métrica": [
            "Probabilidad Local", "Probabilidad Empate", "Probabilidad Visitante",
            "Over 2.5 Goles", "Ambos Marcan (BTTS)", "Goles Esperados Totales",
            "Marcador Más Probable", "  └ Probabilidad",
        ],
        "Valor": [
            f"{pred.prob_home * 100:.1f}%", f"{pred.prob_draw * 100:.1f}%",
            f"{pred.prob_away * 100:.1f}%", f"{pred.prob_over_25 * 100:.1f}%",
            f"{pred.prob_btts * 100:.1f}%", f"{pred.expected_goals:.2f}",
            pred.most_likely_score, f"{pred.most_likely_score_prob * 100:.1f}%",
        ],
    }
    scores_data = {
        "#": list(range(1, len(pred.top_scores) + 1)),
        "Marcador": [s[0] for s in pred.top_scores],
        "Probabilidad": [f"{s[1] * 100:.1f}%" for s in pred.top_scores],
    }
    return pd.DataFrame(summary_data), pd.DataFrame(scores_data)


def print_detailed_analysis(pred: MatchPrediction) -> None:
    """Análisis detallado del modelo (debug/CLI)."""
    print(f"\n{'─'*60}")
    print(f"  ANÁLISIS DETALLADO DEL MODELO POISSON")
    print(f"{'─'*60}")
    print(f"  Partido: {pred.home_team} vs {pred.away_team}")
    print(f"\n  Parámetros de Fuerza:")
    print(f"    Ataque {pred.home_team:>12}: {pred.attack_strength_home:.4f}")
    print(f"    Defensa {pred.home_team:>12}: {pred.defense_strength_home:.4f}")
    print(f"    Ataque {pred.away_team:>12}: {pred.attack_strength_away:.4f}")
    print(f"    Defensa {pred.away_team:>12}: {pred.defense_strength_away:.4f}")
    print(f"\n  Tasas Esperadas de Goles (λ):")
    print(f"    λ Local ({pred.home_team}):     {pred.lambda_home:.4f}")
    print(f"    λ Visitante ({pred.away_team}): {pred.lambda_away:.4f}")
    print(f"\n  Probabilidades:")
    print(f"    Victoria Local:     {pred.prob_home*100:.1f}%")
    print(f"    Empate:             {pred.prob_draw*100:.1f}%")
    print(f"    Victoria Visitante: {pred.prob_away*100:.1f}%")
    print(f"{'─'*60}")
from player_impact import analyze_player_impact


# ---------------------------------------------------------------------------
# Funciones de impresión formateada
# ---------------------------------------------------------------------------

def print_header(home_team: str, away_team: str, league: str, season: int) -> None:
    """Imprime el encabezado principal del reporte."""
    print(f"\n{SEPARATOR}")
    print(f"  ⚽  FUTFOX PREDICTION ENGINE")
    print(f"  Predicción de Partido de Fútbol basada en Modelo Poisson + xG")
    print(f"{SEPARATOR}")
    print(f"  Partido:   {home_team} vs {away_team}")
    print(f"  Liga:      {league}")
    print(f"  Temporada: {season}/{season + 1}")
    print(f"{SEPARATOR}")


def print_match_prediction(pred: MatchPrediction) -> None:
    """
    Imprime la Tabla 1: Predicción del Partido.
    """
    summary_df, scores_df = prediction_to_dataframe(pred)

    print(f"\n{SEPARATOR}")
    print(f"  📊  TABLA 1: PREDICCIÓN DEL PARTIDO")
    print(f"  {pred.home_team} vs {pred.away_team}")
    print(f"{SEPARATOR}")

    print(f"\n  ┌─────────────────────────────────────────────────┐")
    print(f"  │  PROBABILIDADES DE RESULTADO                    │")
    print(f"  ├─────────────────────────────────────────────────┤")

    home_bar = "█" * int(pred.prob_home * BAR_LENGTH)
    draw_bar = "█" * int(pred.prob_draw * BAR_LENGTH)
    away_bar = "█" * int(pred.prob_away * BAR_LENGTH)

    print(f"  │  Victoria Local:     {pred.prob_home*100:5.1f}%  {home_bar}")
    print(f"  │  Empate:             {pred.prob_draw*100:5.1f}%  {draw_bar}")
    print(f"  │  Victoria Visitante: {pred.prob_away*100:5.1f}%  {away_bar}")
    print(f"  ├─────────────────────────────────────────────────┤")
    print(f"  │  Over 2.5 Goles:     {pred.prob_over_25*100:5.1f}%")
    print(f"  │  Ambos Marcan (BTTS): {pred.prob_btts*100:5.1f}%")
    print(f"  │  Goles Esperados:    {pred.expected_goals:5.2f}")
    print(f"  └─────────────────────────────────────────────────┘")

    print(f"\n  ⭐  MARCADOR MÁS PROBABLE: "
          f"{pred.most_likely_score} "
          f"({pred.most_likely_score_prob*100:.1f}%)")

    print(f"\n  Top 5 Marcadores Más Probables:")
    print()
    _print_table(scores_df)
    print()


def print_key_players(key_table: pd.DataFrame) -> None:
    """Imprime la Tabla 2: Jugadores Clave a Seguir."""
    print(f"\n{SEPARATOR}")
    print(f"  ⭐  TABLA 2: JUGADORES CLAVE A SEGUIR")
    print(f"  (Basado en Expected Goal Involvements por 90 min)")
    print(f"{SEPARATOR}\n")

    if key_table.empty:
        print("  ⚠ No hay datos de jugadores disponibles para este partido.\n")
        return

    _print_table(key_table)

    print(f"\n  {'─'*66}")
    print(f"  xG/90  = Goles Esperados por 90 minutos")
    print(f"  xA/90  = Asistencias Esperadas por 90 minutos")
    print(f"  xGI/90 = Expected Goal Involvements por 90 min (xG + xA)")
    print(f"  {'─'*66}")
    print()


def _print_table(df: pd.DataFrame) -> None:
    """Imprime un DataFrame como tabla formateada (tabulate o fallback)."""
    try:
        from tabulate import tabulate
        table_str = tabulate(df, headers="keys", tablefmt="fancy_grid",
                             showindex=False, numalign="center", stralign="center")
        for line in table_str.split("\n"):
            print(f"  {line}")
    except ImportError:
        print(df.to_string(index=False))


def print_model_parameters(
    pred: MatchPrediction,
    alpha_home: float,
    alpha_away: float,
) -> None:
    """
    Imprime los parámetros internos del modelo con fines de transparencia
    y comprensión matemática.
    """
    print(f"\n{SEPARATOR_THIN}")
    print(f"  🔬  PARÁMETROS DEL MODELO (Transparencia Matemática)")
    print(f"{SEPARATOR_THIN}")

    print(f"""
  Ecuación del modelo Poisson compuesto:

    λ_local    = Ataque_local × Defensa_visitante × G_neutral × γ × α_local
    λ_visitante = Ataque_visitante × Defensa_local × G_neutral × α_visitante

  Donde:
    - Ataque = GF_per_game / avg(GF_liga)
    - Defensa = GA_per_game / avg(GA_liga)
    - γ = {HOME_ADVANTAGE} (ventaja de local, Dixon & Coles 1997)
    - α = factor de ajuste por jugadores clave (β = {BETA})

  Valores calculados:
    Ataque {pred.home_team:>12}: {pred.attack_strength_home:.4f}
    Defensa {pred.home_team:>12}: {pred.defense_strength_home:.4f}
    Ataque {pred.away_team:>12}: {pred.attack_strength_away:.4f}
    Defensa {pred.away_team:>12}: {pred.defense_strength_away:.4f}
    α {pred.home_team:>12}: {alpha_home:.4f}
    α {pred.away_team:>12}: {alpha_away:.4f}
    λ {pred.home_team:>12}: {pred.lambda_home:.4f} goles esperados
    λ {pred.away_team:>12}: {pred.lambda_away:.4f} goles esperados

  Probabilidad de marcador exacto (i, j):
    P(i, j) = Poisson(i | λ_H) × Poisson(j | λ_A)
""")

    # Mostrar matriz de probabilidad truncada (0-5 goles)
    print(f"  Matriz de Probabilidad de Marcadores (P(i,j) en %):\n")
    header = "     " + "".join(f"  j={j} " for j in range(6))
    print(f"  {header}")
    print(f"  {'─'*50}")
    for i in range(6):
        row_vals = "".join(f" {pred.score_matrix[i, j]*100:4.1f}" for j in range(6))
        print(f"  i={i} {row_vals}")
    print(f"\n  i = goles local, j = goles visitante")
    print(f"  (Matriz truncada a 0-5 goles por legibilidad)\n")


def print_footer() -> None:
    """Imprime el pie del reporte con disclaimer."""
    print(f"{SEPARATOR}")
    print(f"  📝  DISCLAIMER")
    print(f"  Este modelo es una herramienta analítica basada en datos")
    print(f"  históricos. El fútbol es inherentemente impredecible y")
    print(f"  eventos de baja probabilidad ocurren con frecuencia.")
    print(f"  Estas predicciones NO constituyen asesoramiento de apuestas.")
    print(f"{SEPARATOR}\n")


# ---------------------------------------------------------------------------
# Función principal del pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    league: str = DEFAULT_LEAGUE,
    season: int = DEFAULT_SEASON,
    home_team: str = DEFAULT_HOME_TEAM,
    away_team: str = DEFAULT_AWAY_TEAM,
) -> Tuple[MatchPrediction, pd.DataFrame, float, float]:
    """
    Ejecuta el pipeline completo de predicción.

    Parameters
    ----------
    league : str
    season : int
    home_team : str
    away_team : str

    Returns
    -------
    prediction : MatchPrediction
    key_players_table : pd.DataFrame
    alpha_home : float
    alpha_away : float
    """
    # ------------------------------------------------------------------
    # Fase 1: Recolección de datos
    # ------------------------------------------------------------------
    print(f"\n  [FASE 1/3] Recolectando datos...")
    league_stats, home_players, away_players, league_avgs, is_world_cup = run_collection(
        league=league,
        season=season,
        home_team=home_team,
        away_team=away_team,
    )

    # Usar ventaja de local apropiada según el modo
    effective_home_adv = WORLD_CUP_HOME_ADVANTAGE if is_world_cup else HOME_ADVANTAGE

    # ------------------------------------------------------------------
    # Fase 2: Análisis de impacto de jugadores
    # ------------------------------------------------------------------
    print(f"\n  [FASE 2/3] Analizando impacto de jugadores clave...")
    player_impact_result = analyze_player_impact(
        home_players=home_players,
        away_players=away_players,
        league_stats=league_stats,
        verbose=False,
    )

    alpha_home = player_impact_result["alpha_home"]
    alpha_away = player_impact_result["alpha_away"]
    key_players_table = player_impact_result["key_players_table"]

    # ------------------------------------------------------------------
    # Fase 3: Modelo Poisson y predicción
    # ------------------------------------------------------------------
    print(f"\n  [FASE 3/3] Ejecutando modelo Poisson...")
    prediction = predict_match(
        home_team=home_team,
        away_team=away_team,
        league_stats=league_stats,
        league_averages=league_avgs,
        player_adjustment_home=alpha_home,
        player_adjustment_away=alpha_away,
    )

    return prediction, key_players_table, alpha_home, alpha_away


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Punto de entrada principal del programa."""
    # Parsear argumentos de línea de comandos
    if len(sys.argv) >= 5:
        league = sys.argv[1]
        season = int(sys.argv[2])
        home_team = sys.argv[3]
        away_team = sys.argv[4]
    elif len(sys.argv) >= 3:
        league = sys.argv[1]
        season = int(sys.argv[2])
        home_team = DEFAULT_HOME_TEAM
        away_team = DEFAULT_AWAY_TEAM
        print(f"\n  ℹ  Usando equipos por defecto: {home_team} vs {away_team}")
    else:
        league = DEFAULT_LEAGUE
        season = DEFAULT_SEASON
        home_team = DEFAULT_HOME_TEAM
        away_team = DEFAULT_AWAY_TEAM
        print(f"\n  ℹ  Usando configuración por defecto:")
        print(f"     Liga: {league} | Temporada: {season}/{season+1}")
        print(f"     Partido: {home_team} vs {away_team}")
        print(f"\n  💡  Uso personalizado:")
        print(f"     python main.py <liga> <temporada> <local> <visitante>")
        print(f"     Ejemplo: python main.py EPL 2024 \"Manchester City\" Liverpool")

    # Ejecutar pipeline
    try:
        prediction, key_players_table, alpha_home, alpha_away = run_pipeline(
            league=league,
            season=season,
            home_team=home_team,
            away_team=away_team,
        )

        # ---- OUTPUT FINAL ----
        print_header(home_team, away_team, league, season)

        # Tabla 1: Predicción del Partido
        print_match_prediction(prediction)

        # Tabla 2: Jugadores Clave a Seguir
        print_key_players(key_players_table)

        # Parámetros del modelo (transparencia)
        print_model_parameters(prediction, alpha_home, alpha_away)

        # Footer
        print_footer()

    except ValueError as e:
        print(f"\n  ❌ ERROR: {e}")
        print(f"\n  Verifica los nombres de los equipos. Sugerencias:")
        print(f"  - Usa comillas para nombres con espacios: \"Manchester City\"")
        print(f"  - Revisa que los equipos existan en la liga '{league}' temporada {season}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌ ERROR INESPERADO: {e}")
        print(f"\n  Stack trace:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()