"""
validate_data.py — Herramienta de diagnóstico y validación del pipeline FutFox.
Ejecuta el pipeline completo paso a paso mostrando valores intermedios.

Uso: python3 validate_data.py [liga] [temporada] [local] [visitante]
Autor: FutFox Prediction Engine
"""

import sys, traceback, warnings
from typing import Dict, Tuple
import numpy as np, pandas as pd

from constants import (
    ALPHA_MAX, ALPHA_MIN, BETA, DEFAULT_AWAY_TEAM, DEFAULT_HOME_TEAM,
    DEFAULT_LEAGUE, DEFAULT_SEASON, HOME_ADVANTAGE, LAMBDA_WARN_THRESHOLD,
    MAX_LAMBDA, MIN_LAMBDA, PROB_DOMINANCE_WARN, PROB_SUM_TOLERANCE,
    SEPARATOR, SEPARATOR_THIN, WORLD_CUP_HOME_ADVANTAGE,
)
from data_collection import run_collection, FALLBACK_TEAM_STATS
from model_poisson import MatchPrediction, calculate_lambda, calculate_strengths, predict_match
from player_impact import analyze_player_impact

CHECK_OK, CHECK_WARN, CHECK_ERR, CHECK_INFO = "✅", "🟡", "🔴", "ℹ️"

def _section(title: str) -> None:
    print(f"\n{SEPARATOR}\n  {title}\n{SEPARATOR}")

def _subsection(title: str) -> None:
    print(f"\n  {SEPARATOR_THIN}\n  {title}\n  {SEPARATOR_THIN}")

def _check(condition: bool, label: str, is_critical: bool = False) -> Tuple[bool, str]:
    if condition: return True, f"  {CHECK_OK} {label}"
    icon = CHECK_ERR if is_critical else CHECK_WARN
    return False, f"  {icon} {label}"

def _bar(value: float, max_val: float = 1.0, width: int = 40) -> str:
    n = int((value / max_val) * width)
    return "█" * n + "░" * (width - n)


# =========================================================================
# FASE 0: Validación de entrada
# =========================================================================
def validate_inputs(league: str, season: int, home_team: str, away_team: str) -> Tuple[bool, list]:
    lines, all_ok = [], True
    valid = ["EPL", "La_Liga", "Serie_A", "Bundesliga", "Ligue_1", "WC"]
    if league not in valid:
        all_ok = False
        lines.append(f"  {CHECK_ERR} Liga '{league}' no soportada. Válidas: {valid}")
    else:
        lines.append(f"  {CHECK_OK} Liga '{league}' válida")
    if league == "EPL":
        for team, label in [(home_team, "Local"), (away_team, "Visitante")]:
            if team in FALLBACK_TEAM_STATS:
                lines.append(f"  {CHECK_OK} {label} '{team}' encontrado en fallback")
            else:
                all_ok = False
                lines.append(f"  {CHECK_ERR} {label} '{team}' NO encontrado")
    lines.append(f"  {CHECK_INFO} Temporada: {season}/{season+1}")
    return all_ok, lines


# =========================================================================
# FASE 1: Datos recoleccionados
# =========================================================================
def phase1_data_collection(league, season, home_team, away_team):
    lines = []
    print(f"\n  Recolectando datos de '{league}' temporada {season}...")
    league_stats, home_players, away_players, league_avgs, is_world_cup = run_collection(
        league=league, season=season, home_team=home_team, away_team=away_team)

    n_teams = len(league_stats)
    ok, line = _check(n_teams >= 2, f"Liga tiene {n_teams} equipos")
    lines.append(line)

    total_gf = league_stats["gf"].sum()
    total_ga = league_stats["ga"].sum()
    ok, line = _check(abs(total_gf - total_ga) < 5,
        f"GF total ({total_gf:.0f}) ≈ GA total ({total_ga:.0f}) — diff {abs(total_gf - total_ga):.0f}")
    lines.append(line)

    for label, df in [("Local", home_players), ("Visitante", away_players)]:
        ok, line = _check(not df.empty, f"Jugadores {label}: {len(df)}", is_critical=True)
        lines.append(line)

    avg_gpg = league_avgs.get("avg_goals_per_game", 0)
    ok, line = _check(1.5 < avg_gpg < 5.0, f"Promedio goles/partido = {avg_gpg:.2f}")
    lines.append(line)

    for label, df in [("Local", home_players), ("Visitante", away_players)]:
        n_min = (df["minutes"] >= 450).sum()
        lines.append(f"  {CHECK_OK} Jugadores {label} con >=450 min: {n_min}/{len(df)}")

    for label, df in [("Local", home_players), ("Visitante", away_players)]:
        nan_cols = [c for c in ["xG", "xA", "goals", "minutes"] if df[c].isna().any()]
        if nan_cols:
            lines.append(f"  {CHECK_WARN} Jugadores {label}: NaN en {nan_cols}")
        else:
            lines.append(f"  {CHECK_OK} Jugadores {label}: sin NaN críticos")

    # Tabla League Stats
    print(f"\n  {'─'*70}")
    print(f"  📊  LEAGUE STATS ({n_teams} equipos) — Fuerzas Ataque/Defensa")
    print(f"  {'─'*70}")
    display = league_stats[["team", "gp", "gf", "ga", "gf_per_game", "ga_per_game"]].copy()
    avg_gf = league_stats["gf_per_game"].mean()
    avg_ga = league_stats["ga_per_game"].mean()
    display["Atk"] = (display["gf_per_game"] / avg_gf).round(3)
    display["Def"] = (display["ga_per_game"] / avg_ga).round(3)
    display["⚽"] = display["team"].apply(
        lambda t: "◀ LOCAL" if t == home_team else ("◀ VISIT" if t == away_team else ""))
    print(display.to_string(index=False))

    # Promedios
    print(f"\n  📊  PROMEDIOS DE LIGA")
    for k, v in league_avgs.items():
        print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")

    return league_stats, home_players, away_players, league_avgs, is_world_cup, lines


# =========================================================================
# FASE 2: Impacto de jugadores
# =========================================================================
def phase2_player_impact(home_players, away_players, league_stats):
    lines = []
    result = analyze_player_impact(
        home_players=home_players, away_players=away_players,
        league_stats=league_stats, verbose=False)
    alpha_home = result["alpha_home"]
    alpha_away = result["alpha_away"]
    home_key = result["home_key_players"]
    away_key = result["away_key_players"]
    key_table = result["key_players_table"]

    for label, alpha in [("Local", alpha_home), ("Visitante", alpha_away)]:
        ok, line = _check(ALPHA_MIN <= alpha <= ALPHA_MAX,
            f"\u03b1 {label} = {alpha:.4f} \u2208 [{ALPHA_MIN}, {ALPHA_MAX}]")
        lines.append(line)

    for label, df_key in [("Local", home_key), ("Visitante", away_key)]:
        ok, line = _check(not df_key.empty, f"Top jugadores {label}: {len(df_key)}", is_critical=True)
        lines.append(line)

    home_team = home_players["team"].iloc[0] if not home_players.empty else "Local"
    away_team = away_players["team"].iloc[0] if not away_players.empty else "Visitante"

    print(f"\n  \U0001f4ca  DESGLOSE DE AJUSTE \u03b1")
    print(f"    \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510")
    print(f"    \u2502 {'M\u00e9trica':<19} \u2502 {'Local':>8} \u2502 {'Visit.':>8} \u2502")
    print(f"    \u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524")
    print(f"    \u2502 {'\u03b1 (ajuste)':<19} \u2502 {alpha_home:>8.4f} \u2502 {alpha_away:>8.4f} \u2502")
    print(f"    \u2502 {'\u03b2 (sensibilidad)':<19} \u2502 {BETA:>8.2f} \u2502 {BETA:>8.2f} \u2502")
    print(f"    \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518")

    print(f"\n  \U0001f4ca  TOP JUGADORES CLAVE POR EQUIPO")
    for label, df_key, team_name in [("LOCAL", home_key, home_team), ("VISITANTE", away_key, away_team)]:
        print(f"\n    {label}: {team_name}")
        if not df_key.empty:
            display = df_key[["player_name", "xG_per90", "xA_per90", "xGI_per90", "minutes"]].copy()
            for c in ["xG_per90", "xA_per90", "xGI_per90"]:
                display[c] = display[c].round(3)
            print(display.to_string(index=False))
        else:
            print("      (sin datos)")

    return alpha_home, alpha_away, key_table, lines


# =========================================================================
# FASE 3: Modelo Poisson
# =========================================================================
def phase3_model(home_team, away_team, league_stats, league_avgs,
                 alpha_home, alpha_away, is_world_cup=False):
    lines = []
    att_home, def_home = calculate_strengths(home_team, league_stats)
    att_away, def_away = calculate_strengths(away_team, league_stats)
    g_neutral = league_avgs["avg_goals_per_game"] / 2.0
    effective_home_adv = WORLD_CUP_HOME_ADVANTAGE if is_world_cup else HOME_ADVANTAGE

    prediction = predict_match(
        home_team=home_team, away_team=away_team,
        league_stats=league_stats, league_averages=league_avgs,
        player_adjustment_home=alpha_home, player_adjustment_away=alpha_away)

    print(f"\n  📐  DESGLOSE MATEMATICO DE λ")
    print(f"    Formula: λ_local = Atk_H x Def_A x G_neutral x γ x α_H")
    print(f"    ┌──────────────────────┬──────────┬──────────┐")
    print(f"    │ {'Factor':<20} │ {'Local':>8} │ {'Visit.':>8} │")
    print(f"    ├──────────────────────┼──────────┼──────────┤")
    print(f"    │ {'Ataque':<20} │ {att_home:>8.4f} │ {att_away:>8.4f} │")
    print(f"    │ {'Defensa oponente':<20} │ {def_away:>8.4f} │ {def_home:>8.4f} │")
    print(f"    │ {'G_neutral (avg/2)':<20} │ {g_neutral:>8.4f} │ {g_neutral:>8.4f} │")
    print(f"    │ {'γ (home advantage)':<20} │ {effective_home_adv:>8.4f} │ {'1.0000':>8} │")
    print(f"    │ {'α (jugadores)':<20} │ {alpha_home:>8.4f} │ {alpha_away:>8.4f} │")
    print(f"    ├──────────────────────┼──────────┼──────────┤")
    print(f"    │ {'λ RESULTANTE':<20} │ {prediction.lambda_home:>8.4f} │ {prediction.lambda_away:>8.4f} │")
    print(f"    └──────────────────────┴──────────┴──────────┘")

    for team, lam, label in [("local", prediction.lambda_home, home_team),
                               ("visitante", prediction.lambda_away, away_team)]:
        ok, line = _check(MIN_LAMBDA <= lam <= MAX_LAMBDA,
            f"λ {label} = {lam:.4f} ∈ [{MIN_LAMBDA}, {MAX_LAMBDA}]", is_critical=True)
        lines.append(line)
        if lam > LAMBDA_WARN_THRESHOLD:
            lines.append(f"  {CHECK_WARN} λ {label} = {lam:.4f} > {LAMBDA_WARN_THRESHOLD} (muy desbalanceado)")

    prob_sum = prediction.prob_home + prediction.prob_draw + prediction.prob_away
    ok, line = _check(abs(prob_sum - 1.0) <= PROB_SUM_TOLERANCE,
        f"Σ probabilidades = {prob_sum:.6f} (tol ±{PROB_SUM_TOLERANCE})", is_critical=True)
    lines.append(line)

    for name, prob in [("Victoria Local", prediction.prob_home),
                        ("Empate", prediction.prob_draw),
                        ("Victoria Visitante", prediction.prob_away)]:
        if prob > PROB_DOMINANCE_WARN:
            lines.append(f"  {CHECK_WARN} {name} = {prob*100:.1f}% > {PROB_DOMINANCE_WARN*100:.0f}%")

    ok, line = _check(not np.any(np.isnan(prediction.score_matrix)),
        "Matriz de probabilidad: sin NaN", is_critical=True)
    lines.append(line)
    ok, line = _check(prediction.most_likely_score_prob > 0,
        f"Marcador mas probable: {prediction.most_likely_score} ({prediction.most_likely_score_prob*100:.1f}%)")
    lines.append(line)

    # Matriz
    print(f"\n  📊  MATRIZ DE PROBABILIDAD P(i,j) EN %")
    matrix = prediction.score_matrix * 100
    cols = list(range(6))
    print(f"    {'':5}  " + "  ".join([f"j={j:<4}" for j in cols]))
    print(f"    {'─'*50}")
    for i in range(6):
        row_vals = "  ".join([f"{matrix[i, j]:>5.1f}" for j in cols])
        print(f"    i={i}  {row_vals}")
    print(f"    i = goles {home_team}, j = goles {away_team} (6x6)")

    # Probabilidades
    print(f"\n  📊  PROBABILIDADES DEL PARTIDO")
    prob_data = {
        "Resultado": [f"Victoria {home_team}", "Empate", f"Victoria {away_team}",
                       "Over 2.5 Goles", "Ambos Marcan (BTTS)"],
        "Probabilidad": [f"{prediction.prob_home*100:.1f}%", f"{prediction.prob_draw*100:.1f}%",
                          f"{prediction.prob_away*100:.1f}%", f"{prediction.prob_over_25*100:.1f}%",
                          f"{prediction.prob_btts*100:.1f}%"],
        "Barra": [_bar(prediction.prob_home), _bar(prediction.prob_draw),
                   _bar(prediction.prob_away), _bar(prediction.prob_over_25),
                   _bar(prediction.prob_btts)],
    }
    print(pd.DataFrame(prob_data).to_string(index=False))
    return prediction, lines


# =========================================================================
# FASE 4: Preview del output final
# =========================================================================
def phase4_output_preview(prediction, key_players_table):
    lines = []
    print(f"\n  📊  TOP 5 MARCADORES MAS PROBABLES")
    scores_data = {
        "#": list(range(1, len(prediction.top_scores) + 1)),
        "Marcador": [s[0] for s in prediction.top_scores],
        "Probabilidad": [f"{s[1] * 100:.1f}%" for s in prediction.top_scores],
    }
    print(pd.DataFrame(scores_data).to_string(index=False))
    print(f"\n  📊  JUGADORES CLAVE A SEGUIR (Top 6)")
    if not key_players_table.empty:
        display = key_players_table.copy()
        for col in ["xG/90", "xA/90", "xGI/90"]:
            if col in display.columns:
                display[col] = display[col].apply(
                    lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
        print(display.to_string(index=False))
    else:
        print("    (sin datos)")
    n_key = len(key_players_table)
    if n_key >= 6:
        lines.append(f"  {CHECK_OK} Jugadores clave: {n_key} (OK)")
    else:
        lines.append(f"  {CHECK_WARN} Jugadores clave: solo {n_key}")
    return lines



# =========================================================================
# FASE 5: Resumen de hallazgos
# =========================================================================
def phase5_summary(all_phase_lines):
    _section("📋  FASE 5: RESUMEN DE HALLAZGOS")
    total_ok = sum(1 for lines in all_phase_lines.values()
                   for l in lines if CHECK_OK in l)
    total_warn = sum(1 for lines in all_phase_lines.values()
                     for l in lines if CHECK_WARN in l)
    total_err = sum(1 for lines in all_phase_lines.values()
                    for l in lines if CHECK_ERR in l)

    for phase_name, lines in all_phase_lines.items():
        print(f"\n  ┌─ {phase_name}")
        for line in lines:
            print(f"  │ {line}")
        print(f"  └─")

    print(f"\n  {'═'*50}")
    print(f"  🏁  SCORECARD FINAL")
    print(f"  {'═'*50}")
    print(f"    {CHECK_OK}  Checks OK:     {total_ok}")
    print(f"    {CHECK_WARN}  Warnings:      {total_warn}")
    print(f"    {CHECK_ERR}  Errores:       {total_err}")

    if total_err == 0:
        print(f"\n  ✅ PIPELINE VALIDO — paso todos los checks criticos.")
    else:
        print(f"\n  ❌ PIPELINE CON ERRORES — revisar checks bloqueantes.")
    if total_warn > 0:
        print(f"  🟡 Hay {total_warn} advertencia(s).")

    print(f"\n  📝  Recomendaciones:")
    if total_err > 0:
        print(f"     1. Corregir errores bloqueantes primero.")
    if total_warn > 0:
        print(f"     2. Revisar advertencias — posibles bugs conceptuales.")
    print(f"     3. Si λ > {LAMBDA_WARN_THRESHOLD}, revisar formula en model_poisson.py.")
    print(f"     4. Verificar datos de fallback actualizados a temporada correcta.")



# =========================================================================
# Pipeline principal
# =========================================================================
def run_validation(league=DEFAULT_LEAGUE, season=DEFAULT_SEASON,
                   home_team=DEFAULT_HOME_TEAM, away_team=DEFAULT_AWAY_TEAM):
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*understat.*")
    warnings.filterwarnings("ignore", message=".*xGI_per90.*")
    all_reports = {}

    _section("🔍  VALIDACION DEL PIPELINE FUTFOX")
    print(f"  Partido:   {home_team} vs {away_team}")
    print(f"  Liga:      {league} | Temporada: {season}/{season+1}")

    try:
        _subsection("📥  FASE 0: VALIDACION DE ENTRADA")
        ok, lines = validate_inputs(league, season, home_team, away_team)
        all_reports["FASE 0: Entrada"] = lines
        if not ok:
            print(f"\n  {CHECK_ERR} Errores de entrada. Abortando.")
            phase5_summary(all_reports)
            return

        _subsection("📥  FASE 1: DATOS RECOLECCIONADOS")
        ls, hp, ap, lavgs, is_wc, lines = phase1_data_collection(
            league, season, home_team, away_team)
        all_reports["FASE 1: Datos"] = lines

        _subsection("⭐  FASE 2: IMPACTO DE JUGADORES")
        ah, aa, kt, lines = phase2_player_impact(hp, ap, ls)
        all_reports["FASE 2: Jugadores"] = lines

        _subsection("🧮  FASE 3: MODELO POISSON")
        pred, lines = phase3_model(home_team, away_team, ls, lavgs, ah, aa, is_wc)
        all_reports["FASE 3: Modelo Poisson"] = lines

        _subsection("📊  FASE 4: PREVIEW OUTPUT FINAL")
        lines = phase4_output_preview(pred, kt)
        all_reports["FASE 4: Output Preview"] = lines

        phase5_summary(all_reports)

    except ValueError as e:
        print(f"\n  {CHECK_ERR} ERROR: {e}")
        all_reports["ERROR"] = [f"  {CHECK_ERR} {e}"]
        phase5_summary(all_reports)
    except Exception as e:
        print(f"\n  {CHECK_ERR} ERROR INESPERADO: {e}")
        traceback.print_exc()
        all_reports["ERROR"] = [f"  {CHECK_ERR} {e}"]
        phase5_summary(all_reports)


def main():
    if len(sys.argv) >= 5:
        league, season = sys.argv[1], int(sys.argv[2])
        home_team, away_team = sys.argv[3], sys.argv[4]
    elif len(sys.argv) >= 3:
        league, season = sys.argv[1], int(sys.argv[2])
        home_team, away_team = DEFAULT_HOME_TEAM, DEFAULT_AWAY_TEAM
        print(f"\n  {CHECK_INFO} Equipos por defecto: {home_team} vs {away_team}")
    else:
        league, season = DEFAULT_LEAGUE, DEFAULT_SEASON
        home_team, away_team = DEFAULT_HOME_TEAM, DEFAULT_AWAY_TEAM
        print(f"\n  {CHECK_INFO} Configuracion por defecto: {league} | {season}/{season+1}")
        print(f"  💡  Uso: python3 validate_data.py <liga> <temporada> <local> <visitante>")

    run_validation(league, season, home_team, away_team)


if __name__ == "__main__":
    main()

