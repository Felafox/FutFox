"""
model_poisson.py — Modelo matemático de Distribución de Poisson para predicción
de resultados de fútbol.

Fundamento Matemático:
----------------------
La distribución de Poisson modela la probabilidad de que un equipo marque
exactamente k goles en un partido:

    P(X = k) = (λ^k * e^(-λ)) / k!

Donde λ (lambda) es la tasa esperada de goles para ese equipo en ese partido.

Para cada equipo, λ se calcula como:

    λ_i = FuerzaAtaque_i × FuerzaDefensa_oponente × PromedioGolesLiga

Donde:
  - FuerzaAtaque_i = GolesPorPartido_i / GolesPromedioLiga
  - FuerzaDefensa_j = GolesConcedidosPorPartido_j / GolesConcedidosPromedioLiga

Adicionalmente se aplica:
  - Factor de ventaja local (γ ≈ 1.1-1.4) para ajustar λ del equipo local.
  - Factor de ajuste por rendimiento de jugadores clave (α) desde player_impact.

Probabilidades del partido:
  - P(Local)  = Σ_{i>j}  P(i, j)
  - P(Empate) = Σ_{i=j}  P(i, j)
  - P(Visitante) = Σ_{i<j}  P(i, j)

Donde P(i, j) = Poisson(i | λ_H) × Poisson(j | λ_A)
(asumiendo independencia entre los goles de ambos equipos).

Autor: FutFox Prediction Engine
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import poisson

from constants import (
    HOME_ADVANTAGE,
    MAX_GOALS,
    MAX_LAMBDA,
    MIN_LAMBDA,
    PROB_SUM_TOLERANCE,
)


# ======================================================================
# DataClass para almacenar el resultado del modelo
# ======================================================================

@dataclass
class MatchPrediction:
    """
    Contenedor para los resultados completos de la predicción de un partido.

    Attributes
    ----------
    home_team : str
    away_team : str
    lambda_home : float
        Tasa esperada de goles del equipo local (λ_H).
    lambda_away : float
        Tasa esperada de goles del equipo visitante (λ_A).
    prob_home : float
        Probabilidad de victoria local (0-1).
    prob_draw : float
        Probabilidad de empate (0-1).
    prob_away : float
        Probabilidad de victoria visitante (0-1).
    most_likely_score : str
        Marcador más probable (ej: "2-1").
    most_likely_score_prob : float
        Probabilidad del marcador más probable.
    top_scores : List[Tuple[str, float]]
        Lista de los 5 marcadores más probables con sus probabilidades.
    prob_over_25 : float
        Probabilidad de más de 2.5 goles en el partido.
    prob_btts : float
        Probabilidad de que ambos equipos marquen (Both Teams To Score).
    expected_goals : float
        Total de goles esperados (λ_H + λ_A).
    attack_strength_home : float
        Fuerza de ataque del local.
    defense_strength_home : float
        Fuerza de defensa del local.
    attack_strength_away : float
        Fuerza de ataque del visitante.
    defense_strength_away : float
        Fuerza de defensa del visitante.
    """

    home_team: str
    away_team: str
    lambda_home: float
    lambda_away: float
    prob_home: float = 0.0
    prob_draw: float = 0.0
    prob_away: float = 0.0
    most_likely_score: str = ""
    most_likely_score_prob: float = 0.0
    top_scores: List[Tuple[str, float]] = field(default_factory=list)
    prob_over_25: float = 0.0
    prob_btts: float = 0.0
    expected_goals: float = 0.0
    attack_strength_home: float = 1.0
    defense_strength_home: float = 1.0
    attack_strength_away: float = 1.0
    defense_strength_away: float = 1.0

    # Matriz completa de probabilidad de marcadores (para análisis avanzado)
    score_matrix: np.ndarray = field(default_factory=lambda: np.zeros((MAX_GOALS + 1, MAX_GOALS + 1)))


# ======================================================================
# Funciones del modelo
# ======================================================================

def calculate_strengths(
    team_name: str,
    league_stats: pd.DataFrame,
) -> Tuple[float, float]:
    """
    Calcula las fuerzas de ataque y defensa de un equipo respecto al promedio
    de la liga.

    Matemática:
      FuerzaAtaque_i = GF_per_game_i / avg(GF_per_game_liga)
      FuerzaDefensa_i = GA_per_game_i / avg(GA_per_game_liga)

    Parameters
    ----------
    team_name : str
        Nombre del equipo.
    league_stats : pd.DataFrame
        DataFrame con estadísticas de todos los equipos (de data_collection).

    Returns
    -------
    attack_strength : float
        Factor de fuerza ofensiva (>1 = mejor que el promedio).
    defense_strength : float
        Factor de fuerza defensiva (<1 = mejor que el promedio, ya que
        significa que concede menos goles).
    """
    team_row = league_stats[league_stats["team"] == team_name]
    if team_row.empty:
        raise ValueError(f"Equipo '{team_name}' no encontrado en league_stats.")

    team_gf_per_game = team_row["gf_per_game"].values[0]
    team_ga_per_game = team_row["ga_per_game"].values[0]

    league_avg_gf = league_stats["gf_per_game"].mean()
    league_avg_ga = league_stats["ga_per_game"].mean()

    # Evitar división por cero
    if league_avg_gf == 0:
        league_avg_gf = 1.0
    if league_avg_ga == 0:
        league_avg_ga = 1.0

    attack_strength = team_gf_per_game / league_avg_gf
    defense_strength = team_ga_per_game / league_avg_ga

    return attack_strength, defense_strength


def calculate_lambda(
    attack_strength: float,
    opponent_defense_strength: float,
    league_avg_goals: float,
    is_home: bool = False,
    player_adjustment: float = 1.0,
) -> float:
    """
    Calcula el parámetro λ (tasa esperada de goles) para un equipo en un partido.

    Fórmula base:
        λ = FuerzaAtaque × FuerzaDefensa_oponente × PromedioGolesLiga

    Ajustes:
        - Si is_home=True, se multiplica por HOME_ADVANTAGE (γ).
        - Se multiplica por player_adjustment (α) que refleja el rendimiento
          de los jugadores clave.

    Matemática completa:
        λ_local = Atk_H × Def_A × G_avg_local × γ × α_H
        λ_visit  = Atk_A × Def_H × G_avg_visit × α_A

    Parameters
    ----------
    attack_strength : float
        Fuerza de ataque del equipo.
    opponent_defense_strength : float
        Fuerza de defensa del oponente.
    league_avg_goals : float
        Promedio de goles por partido en la liga (local o visitante según
        corresponda).
    is_home : bool
        Si el equipo es local.
    player_adjustment : float
        Factor de ajuste por rendimiento de jugadores (default 1.0 = sin ajuste).

    Returns
    -------
    lambda_val : float
        Tasa esperada de goles (λ).
    """
    lambda_val = attack_strength * opponent_defense_strength * league_avg_goals

    # Ventaja de local
    if is_home:
        lambda_val *= HOME_ADVANTAGE

    # Ajuste por jugadores clave
    lambda_val *= player_adjustment

    # Sanity check: λ debe estar en [MIN_LAMBDA, MAX_LAMBDA]
    original_lambda = lambda_val
    lambda_val = max(lambda_val, MIN_LAMBDA)
    if lambda_val > MAX_LAMBDA:
        warnings.warn(
            f"λ = {original_lambda:.4f} excede MAX_LAMBDA = {MAX_LAMBDA}. "
            f"Se ha clampado a {MAX_LAMBDA}. "
            f"(Atk={attack_strength:.3f}, Def_op={opponent_defense_strength:.3f}, "
            f"AvgG={league_avg_goals:.3f}, is_home={is_home}, α={player_adjustment:.3f})"
        )
        lambda_val = MAX_LAMBDA

    return lambda_val


def build_score_probability_matrix(lambda_home: float, lambda_away: float) -> np.ndarray:
    """
    Construye la matriz de probabilidad conjunta P(i, j) para todos los
    marcadores posibles i, j ∈ [0, MAX_GOALS].

    P(i, j) = Poisson(i | λ_H) × Poisson(j | λ_A)

    Esta matriz es el corazón del modelo. Cada celda (i, j) representa
    la probabilidad de que el partido termine con marcador i-j.

    Parameters
    ----------
    lambda_home : float
        λ del equipo local.
    lambda_away : float
        λ del equipo visitante.

    Returns
    -------
    matrix : np.ndarray de shape (MAX_GOALS+1, MAX_GOALS+1)
        Matriz de probabilidades conjuntas.
    """
    # Calcular PMF para cada posible número de goles
    home_probs = poisson.pmf(np.arange(0, MAX_GOALS + 1), lambda_home)
    away_probs = poisson.pmf(np.arange(0, MAX_GOALS + 1), lambda_away)

    # Producto exterior: P(i, j) = P_home(i) × P_away(j)
    matrix = np.outer(home_probs, away_probs)

    return matrix


def compute_match_probabilities(
    score_matrix: np.ndarray,
) -> Tuple[float, float, float, float, float]:
    """
    A partir de la matriz de probabilidad de marcadores, calcula las
    probabilidades agregadas del partido.

    Parameters
    ----------
    score_matrix : np.ndarray
        Matriz de probabilidades conjuntas P(i, j).

    Returns
    -------
    prob_home : float
        P(Local gana) = Σ_{i>j} P(i, j)
    prob_draw : float
        P(Empate) = Σ_{i=j} P(i, j)
    prob_away : float
        P(Visitante gana) = Σ_{i<j} P(i, j)
    prob_over_25 : float
        P(Total goles > 2.5) = Σ_{i+j>2} P(i, j)
        (Nota: i+j>2 equivale a >2.5 goles ya que i,j son enteros)
    prob_btts : float
        P(Ambos marcan) = Σ_{i≥1, j≥1} P(i, j)
    """
    prob_home = 0.0
    prob_draw = 0.0
    prob_away = 0.0
    prob_over_25 = 0.0
    prob_btts = 0.0

    n_rows, n_cols = score_matrix.shape

    for i in range(n_rows):
        for j in range(n_cols):
            p = score_matrix[i, j]

            if i > j:
                prob_home += p
            elif i == j:
                prob_draw += p
            else:
                prob_away += p

            if i + j > 2:
                prob_over_25 += p

            if i >= 1 and j >= 1:
                prob_btts += p

    return prob_home, prob_draw, prob_away, prob_over_25, prob_btts


def find_top_scores(score_matrix: np.ndarray, top_n: int = 5) -> List[Tuple[str, float]]:
    """
    Encuentra los marcadores más probables a partir de la matriz.

    Parameters
    ----------
    score_matrix : np.ndarray
        Matriz de probabilidades conjuntas P(i, j).
    top_n : int
        Número de marcadores a retornar.

    Returns
    -------
    List[Tuple[str, float]]
        Lista de (marcador, probabilidad) ordenada de mayor a menor.
    """
    # Aplanar la matriz para ordenar
    flat_indices = np.dstack(
        np.unravel_index(
            np.argsort(score_matrix.ravel())[::-1],
            score_matrix.shape,
        )
    )[0]

    top_scores = []
    for idx in flat_indices[:top_n]:
        i, j = idx
        prob = score_matrix[i, j]
        score_str = f"{i}-{j}"
        top_scores.append((score_str, prob))

    return top_scores


def predict_match(
    home_team: str,
    away_team: str,
    league_stats: pd.DataFrame,
    league_averages: Dict,
    player_adjustment_home: float = 1.0,
    player_adjustment_away: float = 1.0,
    context_adjustment_home: float = 1.0,
    context_adjustment_away: float = 1.0,
) -> MatchPrediction:
    """
    Función principal del modelo: predice el resultado de un partido usando
    el modelo de Poisson con descomposición ataque/defensa.

    Pipeline matemático completo:
    1. Calcular FuerzaAtaque y FuerzaDefensa de cada equipo.
    2. Calcular λ_H y λ_A usando la fórmula de Poisson compuesta.
    3. Construir matriz de probabilidad de marcadores P(i, j).
    4. Calcular probabilidades agregadas (Local, Empate, Visitante).
    5. Identificar el marcador más probable y top 5.
    6. Calcular Over 2.5 y BTTS.

    Parameters
    ----------
    home_team : str
        Nombre del equipo local.
    away_team : str
        Nombre del equipo visitante.
    league_stats : pd.DataFrame
        DataFrame con estadísticas de todos los equipos.
    league_averages : Dict
        Diccionario con promedios de liga (de data_collection).
    player_adjustment_home : float
        Factor α de ajuste por jugadores del equipo local.
    player_adjustment_away : float
        Factor α de ajuste por jugadores del equipo visitante.
    context_adjustment_home : float
        Factor φ de ajuste contextual (altitud, viaje, moral) local.
    context_adjustment_away : float
        Factor φ de ajuste contextual visitante.

    Returns
    -------
    MatchPrediction
        Objeto con todos los resultados de la predicción.
    """
    # ------------------------------------------------------------------
    # Paso 1: Fuerzas de ataque y defensa
    # ------------------------------------------------------------------
    att_home, def_home = calculate_strengths(home_team, league_stats)
    att_away, def_away = calculate_strengths(away_team, league_stats)

    # ------------------------------------------------------------------
    # Paso 2: Cálculo de λ para cada equipo
    # ------------------------------------------------------------------
    # Para el local: su ataque × defensa del rival × promedio goles local × γ
    lambda_home = calculate_lambda(
        attack_strength=att_home,
        opponent_defense_strength=def_away,
        league_avg_goals=league_averages["avg_gf_home"],
        is_home=True,
        player_adjustment=player_adjustment_home,
    )

    # Para el visitante: su ataque × defensa del rival × promedio goles visitante
    lambda_away = calculate_lambda(
        attack_strength=att_away,
        opponent_defense_strength=def_home,
        league_avg_goals=league_averages["avg_gf_away"],
        is_home=False,
        player_adjustment=player_adjustment_away,
    )

    # ------------------------------------------------------------------
    # Paso 3: Matriz de probabilidad de marcadores
    # ------------------------------------------------------------------
    score_matrix = build_score_probability_matrix(lambda_home, lambda_away)

    # ------------------------------------------------------------------
    # Paso 4: Probabilidades agregadas
    # ------------------------------------------------------------------
    prob_home, prob_draw, prob_away, prob_over_25, prob_btts = (
        compute_match_probabilities(score_matrix)
    )

    # ------------------------------------------------------------------
    # Paso 5: Marcadores más probables
    # ------------------------------------------------------------------
    top_scores = find_top_scores(score_matrix, top_n=5)
    most_likely_score, most_likely_score_prob = top_scores[0] if top_scores else ("N/A", 0.0)

    # ------------------------------------------------------------------
    # Paso 6: Construir resultado
    # ------------------------------------------------------------------
    prediction = MatchPrediction(
        home_team=home_team,
        away_team=away_team,
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        prob_home=prob_home,
        prob_draw=prob_draw,
        prob_away=prob_away,
        most_likely_score=most_likely_score,
        most_likely_score_prob=most_likely_score_prob,
        top_scores=top_scores,
        prob_over_25=prob_over_25,
        prob_btts=prob_btts,
        expected_goals=lambda_home + lambda_away,
        attack_strength_home=att_home,
        defense_strength_home=def_home,
        attack_strength_away=att_away,
        defense_strength_away=def_away,
        score_matrix=score_matrix,
    )

    # ------------------------------------------------------------------
    # Paso 7: Sanity checks
    # ------------------------------------------------------------------
    is_valid, warnings_list = _sanity_check_prediction(prediction)
    if not is_valid:
        for w in warnings_list:
            warnings.warn(f"[Sanity Check] {w}")
    elif warnings_list:
        for w in warnings_list:
            print(f"  [INFO] {w}")

    # Verificar que las probabilidades sumen ~1.0
    prob_sum = prediction.prob_home + prediction.prob_draw + prediction.prob_away
    if abs(prob_sum - 1.0) > PROB_SUM_TOLERANCE:
        warnings.warn(
            f"Probabilidades no suman 1.0: Local={prediction.prob_home:.4f} + "
            f"Empate={prediction.prob_draw:.4f} + "
            f"Visitante={prediction.prob_away:.4f} = {prob_sum:.4f} "
            f"(diferencia: {prob_sum - 1.0:.6f})"
        )

    return prediction


def _sanity_check_prediction(pred: MatchPrediction) -> Tuple[bool, List[str]]:
    """
    Verifica que una predicción sea matemáticamente válida.

    Realiza los siguientes checks:
    1. λ_H y λ_A están en [MIN_LAMBDA, MAX_LAMBDA]
    2. Ninguna probabilidad es negativa
    3. Las probabilidades principales suman aproximadamente 1.0
    4. La matriz de score no contiene NaN o inf

    Parameters
    ----------
    pred : MatchPrediction
        Predicción a validar.

    Returns
    -------
    is_valid : bool
        True si la predicción pasa todos los checks críticos.
    warnings_list : List[str]
        Lista de advertencias encontradas (vacía si todo OK).
    """
    warnings_list = []
    is_valid = True

    # Check 1: λ en rango válido
    for team, lam in [("local", pred.lambda_home), ("visitante", pred.lambda_away)]:
        if lam < MIN_LAMBDA:
            warnings_list.append(
                f"λ_{team} = {lam:.4f} < MIN_LAMBDA ({MIN_LAMBDA}). "
                f"Esto puede indicar datos insuficientes."
            )
            is_valid = False
        if lam > MAX_LAMBDA:
            warnings_list.append(
                f"λ_{team} = {lam:.4f} > MAX_LAMBDA ({MAX_LAMBDA}). "
                f"Valor irreal para un partido de fútbol. Posible error en datos de entrada."
            )
            is_valid = False

    # Check 2: Probabilidades no negativas
    prob_checks = [
        ("Local", pred.prob_home),
        ("Empate", pred.prob_draw),
        ("Visitante", pred.prob_away),
        ("Over 2.5", pred.prob_over_25),
        ("BTTS", pred.prob_btts),
    ]
    for name, prob in prob_checks:
        if prob < 0:
            warnings_list.append(f"Probabilidad {name} es negativa: {prob:.6f}")
            is_valid = False
        if prob > 1.0:
            warnings_list.append(f"Probabilidad {name} excede 1.0: {prob:.6f}")
            is_valid = False

    # Check 3: Suma de probabilidades principales ≈ 1.0
    prob_sum = pred.prob_home + pred.prob_draw + pred.prob_away
    if abs(prob_sum - 1.0) > PROB_SUM_TOLERANCE:
        warnings_list.append(
            f"Suma de probabilidades ({prob_sum:.6f}) no está dentro "
            f"de tolerancia ±{PROB_SUM_TOLERANCE} de 1.0"
        )

    # Check 4: Matriz sin NaN ni inf
    if np.any(np.isnan(pred.score_matrix)):
        warnings_list.append("Matriz de probabilidad contiene valores NaN")
        is_valid = False
    if np.any(np.isinf(pred.score_matrix)):
        warnings_list.append("Matriz de probabilidad contiene valores infinitos")
        is_valid = False

    # Check 5: Marcador más probable tiene probabilidad > 0
    if pred.most_likely_score_prob <= 0:
        warnings_list.append(
            f"Marcador más probable ({pred.most_likely_score}) "
            f"tiene probabilidad {pred.most_likely_score_prob:.6f} ≤ 0"
        )
        is_valid = False

    return is_valid, warnings_list


def prediction_to_dataframe(pred: MatchPrediction) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convierte un MatchPrediction en DataFrames formateados para impresión
    en consola.

    Parameters
    ----------
    pred : MatchPrediction

    Returns
    -------
    summary_df : pd.DataFrame
        Tabla resumen con probabilidades principales.
    scores_df : pd.DataFrame
        Tabla con el top 5 de marcadores más probables.
    """
    # Tabla 1: Resumen
    summary_data = {
        "Métrica": [
            "Probabilidad Local",
            "Probabilidad Empate",
            "Probabilidad Visitante",
            "Over 2.5 Goles",
            "Ambos Marcan (BTTS)",
            "Goles Esperados Totales",
            "Marcador Más Probable",
            f"  └ Probabilidad",
        ],
        "Valor": [
            f"{pred.prob_home * 100:.1f}%",
            f"{pred.prob_draw * 100:.1f}%",
            f"{pred.prob_away * 100:.1f}%",
            f"{pred.prob_over_25 * 100:.1f}%",
            f"{pred.prob_btts * 100:.1f}%",
            f"{pred.expected_goals:.2f}",
            pred.most_likely_score,
            f"{pred.most_likely_score_prob * 100:.1f}%",
        ],
    }
    summary_df = pd.DataFrame(summary_data)

    # Tabla 2: Top 5 marcadores
    scores_data = {
        "#": list(range(1, len(pred.top_scores) + 1)),
        "Marcador": [s[0] for s in pred.top_scores],
        "Probabilidad": [f"{s[1] * 100:.1f}%" for s in pred.top_scores],
    }
    scores_df = pd.DataFrame(scores_data)

    return summary_df, scores_df


# ======================================================================
# Función auxiliar para debug / análisis
# ======================================================================

def print_detailed_analysis(pred: MatchPrediction) -> None:
    """
    Imprime un análisis detallado del modelo incluyendo los parámetros
    internos (útil para depuración y comprensión del modelo).
    """
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
    print(f"    Total goles esperados:       {pred.expected_goals:.2f}")
    print(f"\n  Probabilidades:")
    print(f"    Victoria Local:     {pred.prob_home*100:.1f}%")
    print(f"    Empate:             {pred.prob_draw*100:.1f}%")
    print(f"    Victoria Visitante: {pred.prob_away*100:.1f}%")
    print(f"{'─'*60}")


# ======================================================================
# Ejecución standalone para testing
# ======================================================================
if __name__ == "__main__":
    import sys
    from data_collection import run_collection

    print("Test de model_poisson.py\n")

    try:
        # Obtener datos
        league_stats, home_players, away_players, league_avgs = run_collection(
            league="EPL", season=2024,
            home_team="Arsenal", away_team="Chelsea",
        )

        # Predecir sin ajuste de jugadores
        pred = predict_match(
            home_team="Arsenal",
            away_team="Chelsea",
            league_stats=league_stats,
            league_averages=league_avgs,
        )

        print_detailed_analysis(pred)

        summary_df, scores_df = prediction_to_dataframe(pred)
        print("\n--- Tabla Resumen ---")
        print(summary_df.to_string(index=False))
        print("\n--- Top 5 Marcadores ---")
        print(scores_df.to_string(index=False))

        print("\n[OK] Test exitoso.")
    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)