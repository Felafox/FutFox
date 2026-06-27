"""
app.py — FutFox Copa del Mundo 2026

Interfaz web con Streamlit enfocada en la Copa del Mundo.
Muestra partidos en vivo con predicciones, próximos partidos, y
comparación con cuotas de casas de apuestas (The Odds API o sintético).

Ejecutar:
    streamlit run app.py

Autor: FutFox Prediction Engine
"""

import pandas as pd
import streamlit as st
from datetime import datetime

# ── Configuración de la página ──────────────────────────────────────────
st.set_page_config(
    page_title="FutFox — Copa del Mundo 2026",
    page_icon="🏆",
    layout="wide",
)

# ── Auto-refresh: recargar la página cada AUTO_REFRESH_SECONDS ──────────
from constants import AUTO_REFRESH_SECONDS
st.markdown(
    f"""
    <script>
        setTimeout(function() {{
            window.location.reload();
        }}, {AUTO_REFRESH_SECONDS * 1000});
    </script>
    """,
    unsafe_allow_html=True,
)

# ── Imports del motor FutFox ────────────────────────────────────────────
import live_api
from constants import HOME_ADVANTAGE, WORLD_CUP_HOME_ADVANTAGE, BETA, ENSEMBLE_WEIGHT, THE_ODDS_API_KEY
from data_collection import run_collection
from model_poisson import predict_match, predict_match_live
from player_impact import analyze_player_impact
from worldcup_schedule import get_live_matches, get_upcoming_matches, get_match_status, get_countdown
from player_context import calculate_context_adjustment, get_context_notes
from odds_fetcher import get_market_odds, ensemble_probability
from match_history import get_team_form
from news_feed import get_team_news

# ── Caché de predicciones ───────────────────────────────────────────────
if "predictions_cache" not in st.session_state:
    st.session_state.predictions_cache = {}


def _render_analysis_expander(match: dict, result: dict) -> None:
    """Expander unificado con todo el análisis del partido."""
    pred = result["pred"]
    mkt = result["market"]

    with st.expander(f"🔍 Análisis Completo — {match['home']} vs {match['away']}"):

        # ── 📊 Comparativa de Probabilidades ──────────────────────
        st.markdown("### 📊 Comparativa de Probabilidades")
        t1, t2, t3, t4, t5 = st.columns([2, 3, 3, 3, 2])
        with t1:
            st.markdown("**Resultado**")
            st.markdown(f"🏠 {match['home']}")
            st.markdown("🤝 Empate")
            st.markdown(f"🚩 {match['away']}")
        with t2:
            st.markdown("**FutFox**")
            st.markdown(f"<span style='color:#3b82f6'>{pred.prob_home*100:.1f}%</span> `{_prob_bar(pred.prob_home)}`", unsafe_allow_html=True)
            st.markdown(f"{pred.prob_draw*100:.1f}% `{_prob_bar(pred.prob_draw)}`")
            st.markdown(f"<span style='color:#ef4444'>{pred.prob_away*100:.1f}%</span> `{_prob_bar(pred.prob_away)}`", unsafe_allow_html=True)
        with t3:
            source_label = "Mercado" if mkt.get("source") == "api" else "Mercado*"
            st.markdown(f"**{source_label}**")
            st.markdown(f"<span style='color:#3b82f6'>{mkt['prob_home']*100:.1f}%</span> `{_prob_bar(mkt['prob_home'])}` {_delta_arrow(pred.prob_home, mkt['prob_home'])}", unsafe_allow_html=True)
            st.markdown(f"{mkt['prob_draw']*100:.1f}% `{_prob_bar(mkt['prob_draw'])}` {_delta_arrow(pred.prob_draw, mkt['prob_draw'])}")
            st.markdown(f"<span style='color:#ef4444'>{mkt['prob_away']*100:.1f}%</span> `{_prob_bar(mkt['prob_away'])}` {_delta_arrow(pred.prob_away, mkt['prob_away'])}", unsafe_allow_html=True)
        with t4:
            st.markdown("**Ensemble**")
            st.markdown(f"<span style='color:#16a34a'>{result['ens_home']*100:.1f}%</span> `{_prob_bar(result['ens_home'])}`", unsafe_allow_html=True)
            st.markdown(f"{result['ens_draw']*100:.1f}% `{_prob_bar(result['ens_draw'])}`")
            st.markdown(f"<span style='color:#16a34a'>{result['ens_away']*100:.1f}%</span> `{_prob_bar(result['ens_away'])}`", unsafe_allow_html=True)
        with t5:
            st.caption(f"Fuente: {', '.join(mkt.get('bookmakers', ['N/A']))[:40]}")
            if mkt.get("overround"):
                st.caption(f"Margen: {mkt['overround']:.1f}%")
            st.caption(f"λ: {pred.lambda_home:.2f} / {pred.lambda_away:.2f}")

        st.divider()

        # ── ⭐ Jugadores Clave ──────────────────────────────────────
        st.markdown("### ⭐ Jugadores Clave")
        key_table = result.get("key_table", pd.DataFrame())
        if not key_table.empty:
            st.dataframe(key_table, hide_index=True, use_container_width=True)
        else:
            st.caption("Sin datos de jugadores disponibles.")

        st.divider()

        # ── 📈 Rendimiento en el Mundial ────────────────────────────
        st.markdown("### 📈 Rendimiento en el Mundial")
        form_home = get_team_form(match["home"])
        form_away = get_team_form(match["away"])
        fx1, fx2 = st.columns(2)
        with fx1:
            st.markdown(f"**{match['home']}** — {form_home['record']} | GF:{form_home['gf']} GA:{form_home['ga']} | Racha: {form_home['streak']}")
            for mf in form_home["matches"]:
                st.caption(f"{mf['status']} vs {mf['opponent']} {mf['score']}")
        with fx2:
            st.markdown(f"**{match['away']}** — {form_away['record']} | GF:{form_away['gf']} GA:{form_away['ga']} | Racha: {form_away['streak']}")
            for mf in form_away["matches"]:
                st.caption(f"{mf['status']} vs {mf['opponent']} {mf['score']}")

        st.divider()

        # ── 🧠 Contexto ─────────────────────────────────────────────
        st.markdown("### 🧠 Factores Contextuales")
        cx1, cx2 = st.columns(2)
        with cx1:
            st.markdown(f"**{match['home']}** (φ={result['ctx_home']:.3f})")
            for note in result["notes_home"][:4]:
                st.caption(note)
        with cx2:
            st.markdown(f"**{match['away']}** (φ={result['ctx_away']:.3f})")
            for note in result["notes_away"][:4]:
                st.caption(note)

        st.divider()

        # ── 📰 Noticias ─────────────────────────────────────────────
        st.markdown("### 📰 Noticias")
        news_home = get_team_news(match["home"])
        news_away = get_team_news(match["away"])
        nx1, nx2 = st.columns(2)
        with nx1:
            for n in news_home[:3]:
                st.caption(n)
        with nx2:
            for n in news_away[:3]:
                st.caption(n)


def predict_single_match(match: dict) -> dict:
    """Ejecuta el pipeline completo para un partido, con caché dinámica por estado del partido."""
    match_id = match["id"]
    minute = match.get("minute", 0)
    score_home = match.get("score_home", 0)
    score_away = match.get("score_away", 0)
    cache_key = f"{match_id}_{minute}_{score_home}_{score_away}"

    if cache_key in st.session_state.predictions_cache:
        return st.session_state.predictions_cache[cache_key]

    try:
        league_stats, home_players, away_players, league_avgs, _ = run_collection(
            league="WC", season=2026,
            home_team=match["home"], away_team=match["away"],
        )

        impact = analyze_player_impact(
            home_players=home_players, away_players=away_players,
            league_stats=league_stats, verbose=False,
        )

        ctx_home = calculate_context_adjustment(match["home"], match)
        ctx_away = calculate_context_adjustment(match["away"], match)

        is_live = match.get("status") == "live"
        current_minute = match.get("minute", 0)
        current_score_h = match.get("score_home") or 0
        current_score_a = match.get("score_away") or 0

        if is_live and current_minute > 0:
            # ── Predicción en vivo: λ ajustado por tiempo restante ──
            from model_poisson import calculate_strengths, calculate_lambda
            from constants import HOME_ADVANTAGE
            g_neutral = league_avgs["avg_goals_per_game"] / 2.0
            att_h, def_h = calculate_strengths(match["home"], league_stats)
            att_a, def_a = calculate_strengths(match["away"], league_stats)
            lam_h = calculate_lambda(att_h, def_a, g_neutral, is_home=True,
                                     player_adjustment=impact["alpha_home"] * ctx_home)
            lam_a = calculate_lambda(att_a, def_h, g_neutral, is_home=False,
                                     player_adjustment=impact["alpha_away"] * ctx_away)
            pred = predict_match_live(
                home_team=match["home"], away_team=match["away"],
                current_minute=current_minute,
                current_score_home=current_score_h,
                current_score_away=current_score_a,
                lambda_home=lam_h, lambda_away=lam_a,
                attack_strength_home=att_h, defense_strength_home=def_h,
                attack_strength_away=att_a, defense_strength_away=def_a,
            )
        else:
            # ── Predicción pre-partido normal ────────────────────────
            pred = predict_match(
                home_team=match["home"], away_team=match["away"],
                league_stats=league_stats, league_averages=league_avgs,
                player_adjustment_home=impact["alpha_home"] * ctx_home,
                player_adjustment_away=impact["alpha_away"] * ctx_away,
            )

        # ── Market Odds ───────────────────────────────────────────────
        model_probs = {
            "prob_home": pred.prob_home,
            "prob_draw": pred.prob_draw,
            "prob_away": pred.prob_away,
        }
        market = get_market_odds(match["home"], match["away"], model_probs)

        # Ensemble (combinar modelo + mercado)
        ens_home = ensemble_probability(pred.prob_home, market["prob_home"])
        ens_draw = ensemble_probability(pred.prob_draw, market["prob_draw"])
        ens_away = ensemble_probability(pred.prob_away, market["prob_away"])

        notes_home = get_context_notes(match["home"], match)
        notes_away = get_context_notes(match["away"], match)

        result = {
            "pred": pred, "key_table": impact["key_players_table"],
            "ctx_home": ctx_home, "ctx_away": ctx_away,
            "notes_home": notes_home, "notes_away": notes_away,
            "market": market,
            "ens_home": ens_home, "ens_draw": ens_draw, "ens_away": ens_away,
        }
        st.session_state.predictions_cache[cache_key] = result
        return result
    except Exception as e:
        return {"error": str(e)}


def _prob_bar(prob: float, width: int = 12) -> str:
    filled = int(prob * width)
    return "█" * filled + "░" * (width - filled)


def _delta_arrow(model_p: float, market_p: float) -> str:
    """Muestra flecha indicando si el modelo es más optimista que el mercado."""
    diff = model_p - market_p
    if diff > 0.05:
        return "🔼"
    elif diff < -0.05:
        return "🔽"
    return "➡️"


# ══════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════

st.title("🏆 FutFox — Copa del Mundo 2026")
st.markdown(
    "Predicciones en vivo basadas en **modelo Poisson + xG + contexto** "
    "comparadas con cuotas de casas de apuestas."
)

# ── Status de API ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Estado de Fuentes")
    
    # Estado de la API de partidos
    if live_api.get_api_status():
        st.success("🌐 Datos reales (worldcup26.ir): Conectado")
    else:
        st.error("🔴 Fallback local: Sin conexión a API")
        
    # Estado de The Odds API
    if THE_ODDS_API_KEY:
        st.success("🔑 The Odds API: Configurada")
    else:
        st.warning("⚠️ The Odds API: Cuotas sintéticas")
        st.caption("Registrate gratis en the-odds-api.com")
        
    st.caption(f"Ensemble: {ENSEMBLE_WEIGHT:.0%} modelo / {(1-ENSEMBLE_WEIGHT):.0%} mercado")
    st.caption(f"γ mundial = {WORLD_CUP_HOME_ADVANTAGE}")

    st.divider()
    
    # ── Status de actualización ───────────────────────────────────────
    st.subheader("🕐 Actualización")
    st.caption(f"Última: {datetime.now().strftime('%H:%M:%S')}")
    st.caption(f"Auto-refresh: cada {AUTO_REFRESH_SECONDS}s")
    
    st.subheader("🔄 Sincronización y Caché")
    if st.button("Limpiar Caché y Actualizar"):
        st.session_state.predictions_cache.clear()
        st.rerun()
    st.caption("Los datos se actualizan automáticamente desde la API. Usá este botón para forzar una recarga limpia.")

# ══════════════════════════════════════════════════════════════════════════
# PARTIDOS EN VIVO
# ══════════════════════════════════════════════════════════════════════════

live_matches = get_live_matches()
upcoming_all = get_upcoming_matches()

# ── Separar partidos que empiezan en <60 min ───────────────────────
STARTING_SOON_MINUTES = 60
starting_soon = []
upcoming_rest = []
for m in upcoming_all:
    if m.get("status") == "upcoming":
        cd = get_countdown(m.get("datetime", ""), m.get("utc_offset", -6))
        if cd.startswith("Falta ") and "h" not in cd:
            starting_soon.append(m)
        else:
            upcoming_rest.append(m)
    else:
        upcoming_rest.append(m)

# ══════════════════════════════════════════════════════════════════════════
# PARTIDOS EN VIVO
# ══════════════════════════════════════════════════════════════════════════

if live_matches:
    st.header("🔴 PARTIDOS EN VIVO")
    for match in live_matches:
        result = predict_single_match(match)
        if "error" in result:
            st.error(f"Error: {result['error']}")
            continue
        pred, mkt = result["pred"], result["market"]
        status_str = get_match_status(match)

        with st.container(border=True):
            col_h, col_mid, col_a = st.columns([2, 1, 2])
            with col_h:
                st.markdown(f"### {match['home']}")
            with col_mid:
                sc_h = match.get("score_home") or 0
                sc_a = match.get("score_away") or 0
                st.markdown(f"## {sc_h} - {sc_a}")
                st.caption(status_str)
            with col_a:
                st.markdown(f"### {match['away']}")

            st.markdown(
                f"⭐ **{pred.most_likely_score}** "
                f"({pred.most_likely_score_prob*100:.1f}%) | "
                f"⚽ Goles esperados restantes: {pred.expected_goals:.2f} | "
                f"Over 2.5: {pred.prob_over_25*100:.1f}% | "
                f"BTTS: {pred.prob_btts*100:.1f}%"
            )
            _render_analysis_expander(match, result)

else:
    st.header("🔴 PARTIDOS EN VIVO")
    st.info("No hay partidos en vivo en este momento.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════
# COMENZANDO (próximos <60 min)
# ══════════════════════════════════════════════════════════════════════════

if starting_soon:
    st.header("🟠 COMENZANDO")
    for match in starting_soon:
        result = predict_single_match(match)
        if "error" in result:
            continue
        pred, mkt = result["pred"], result["market"]
        status_str = get_match_status(match)

        with st.container(border=True):
            st.markdown(
                f"**{match['home']} vs {match['away']}** · {status_str}"
            )
            st.caption(f"Grupo {match['group']} · {match['stadium']}, {match['city']}")
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("🏠 Local", f"{pred.prob_home*100:.1f}%")
            with k2:
                st.metric("🤝 Empate", f"{pred.prob_draw*100:.1f}%")
            with k3:
                st.metric("🚩 Visit.", f"{pred.prob_away*100:.1f}%")
            st.markdown(f"⭐ **{pred.most_likely_score}** ({pred.most_likely_score_prob*100:.1f}%)")
            _render_analysis_expander(match, result)

    st.divider()

# ══════════════════════════════════════════════════════════════════════════
# PRÓXIMOS PARTIDOS
# ══════════════════════════════════════════════════════════════════════════

if upcoming_rest:
    st.header("🟡 PRÓXIMOS PARTIDOS")

    for i in range(0, len(upcoming_rest), 2):
        cols = st.columns(2)
        for j, match in enumerate(upcoming_rest[i:i+2]):
            with cols[j]:
                result = predict_single_match(match)
                if "error" in result:
                    st.warning(f"{match['home']} vs {match['away']}: sin datos")
                    continue

                pred = result["pred"]
                mkt = result["market"]
                status_str = get_match_status(match)

                with st.container(border=True):
                    st.markdown(
                        f"**{match['home']} vs {match['away']}** · {status_str}"
                    )
                    st.caption(
                        f"Grupo {match['group']} · {match['stadium']}, {match['city']}"
                    )

                    k1, k2, k3 = st.columns(3)
                    with k1:
                        st.metric("🏠 Local (FutFox)", f"{pred.prob_home*100:.1f}%")
                    with k2:
                        st.metric("🤝 Empate", f"{pred.prob_draw*100:.1f}%")
                    with k3:
                        st.metric("🚩 Visit. (FutFox)", f"{pred.prob_away*100:.1f}%")

                    st.markdown(
                        f"⭐ **{pred.most_likely_score}** "
                        f"({pred.most_likely_score_prob*100:.1f}%)"
                    )

                    _render_analysis_expander(match, result)

    st.divider()

# ══════════════════════════════════════════════════════════════════════════
# LEYENDA DEL MODELO
# ══════════════════════════════════════════════════════════════════════════

with st.expander("🔬 Sobre el Modelo y el Ensemble"):
    st.markdown(f"""
    **Modelo Poisson Compuesto (FutFox):**
    
    λ = Ataque × Defensa\_oponente × Ḡ × γ × α × φ

    - **γ** = {WORLD_CUP_HOME_ADVANTAGE} (ventaja local sede neutral)
    - **α** = ajuste por jugadores clave (xGI/90)
    - **φ** = ajuste contextual (altitud, viaje, lesiones, moral, clima)

    **Ensemble (combinación con mercado):**
    
    P\_ensemble = {ENSEMBLE_WEIGHT:.0%} × P\_FutFox + {(1-ENSEMBLE_WEIGHT):.0%} × P\_Mercado

    **Fuentes del Mercado:** The Odds API (Pinnacle, Bet365) o sintético basado en FutFox.
    Registrate gratis en [the-odds-api.com](https://the-odds-api.com) para datos reales.
    """)

st.divider()
st.caption(
    "🏆 FutFox — Copa del Mundo 2026 | "
    "Poisson + xG + Contexto + Mercado | "
    "📝 Herramienta analítica, no asesoramiento de apuestas"
)