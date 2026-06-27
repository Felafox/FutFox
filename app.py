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

# ── Configuración de la página ──────────────────────────────────────────
st.set_page_config(
    page_title="FutFox — Copa del Mundo 2026",
    page_icon="🏆",
    layout="wide",
)

# ── Imports del motor FutFox ────────────────────────────────────────────
from constants import HOME_ADVANTAGE, WORLD_CUP_HOME_ADVANTAGE, BETA, ENSEMBLE_WEIGHT, THE_ODDS_API_KEY
from data_collection import run_collection
from model_poisson import predict_match
from player_impact import analyze_player_impact
from worldcup_schedule import get_live_matches, get_upcoming_matches
from player_context import calculate_context_adjustment, get_context_notes
from odds_fetcher import get_market_odds, ensemble_probability
from match_history import get_team_form
from news_feed import get_team_news

# ── Caché de predicciones ───────────────────────────────────────────────
if "predictions_cache" not in st.session_state:
    st.session_state.predictions_cache = {}


def predict_single_match(match: dict) -> dict:
    """Ejecuta el pipeline completo para un partido, con caché."""
    match_id = match["id"]
    if match_id in st.session_state.predictions_cache:
        return st.session_state.predictions_cache[match_id]

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
        st.session_state.predictions_cache[match_id] = result
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
    st.header("⚙️ Estado")
    if THE_ODDS_API_KEY:
        st.success("🔑 The Odds API: Configurada")
        st.caption("Usando cuotas reales de Pinnacle, Bet365")
    else:
        st.warning("⚠️ Sin API key de The Odds API")
        st.caption("Usando cuotas sintéticas basadas en FutFox")
        st.caption("Registrate gratis en the-odds-api.com")
    st.caption(f"Ensemble: {ENSEMBLE_WEIGHT:.0%} modelo / {(1-ENSEMBLE_WEIGHT):.0%} mercado")
    st.caption(f"γ mundial = {WORLD_CUP_HOME_ADVANTAGE}")

# ══════════════════════════════════════════════════════════════════════════
# PARTIDOS EN VIVO
# ══════════════════════════════════════════════════════════════════════════

live_matches = get_live_matches()
if live_matches:
    st.header("🔴 PARTIDOS EN VIVO")

    for match in live_matches:
        result = predict_single_match(match)
        if "error" in result:
            st.error(f"Error: {result['error']}")
            continue

        pred = result["pred"]
        mkt = result["market"]

        with st.container(border=True):
            # Cabecera
            col_h, col_mid, col_a = st.columns([2, 1, 2])
            with col_h:
                st.markdown(f"### {match['home']}")
            with col_mid:
                score = f"{match['score_home']} - {match['score_away']}"
                st.markdown(f"## {score}")
                st.caption(f"{match['minute']}' · {match['city']}")
            with col_a:
                st.markdown(f"### {match['away']}")

            # Predicción + Marcador probable
            st.markdown(
                f"⭐ **{pred.most_likely_score}** "
                f"({pred.most_likely_score_prob*100:.1f}%) | "
                f"⚽ Goles esperados: {pred.expected_goals:.2f} | "
                f"Over 2.5: {pred.prob_over_25*100:.1f}% | "
                f"BTTS: {pred.prob_btts*100:.1f}%"
            )

            # ── Tabla comparativa FutFox vs Mercado vs Ensemble ─────
            st.markdown("---")
            st.markdown("### 📊 Comparativa de Probabilidades")

            t1, t2, t3, t4, t5 = st.columns([2, 3, 3, 3, 2])
            with t1:
                st.markdown("**Resultado**")
                st.markdown(f"🏠 {match['home']}")
                st.markdown("🤝 Empate")
                st.markdown(f"🚩 {match['away']}")
            with t2:
                st.markdown("**FutFox**")
                st.markdown(
                    f"<span style='color:#3b82f6'>{pred.prob_home*100:.1f}%</span> "
                    f"`{_prob_bar(pred.prob_home)}`",
                    unsafe_allow_html=True,
                )
                st.markdown(f"{pred.prob_draw*100:.1f}% `{_prob_bar(pred.prob_draw)}`")
                st.markdown(
                    f"<span style='color:#ef4444'>{pred.prob_away*100:.1f}%</span> "
                    f"`{_prob_bar(pred.prob_away)}`",
                    unsafe_allow_html=True,
                )
            with t3:
                source_label = "Mercado" if mkt["source"] == "api" else "Mercado*"
                st.markdown(f"**{source_label}**")
                d_h = _delta_arrow(pred.prob_home, mkt["prob_home"])
                d_d = _delta_arrow(pred.prob_draw, mkt["prob_draw"])
                d_a = _delta_arrow(pred.prob_away, mkt["prob_away"])
                st.markdown(
                    f"<span style='color:#3b82f6'>{mkt['prob_home']*100:.1f}%</span> "
                    f"`{_prob_bar(mkt['prob_home'])}` {d_h}",
                    unsafe_allow_html=True,
                )
                st.markdown(f"{mkt['prob_draw']*100:.1f}% `{_prob_bar(mkt['prob_draw'])}` {d_d}")
                st.markdown(
                    f"<span style='color:#ef4444'>{mkt['prob_away']*100:.1f}%</span> "
                    f"`{_prob_bar(mkt['prob_away'])}` {d_a}",
                    unsafe_allow_html=True,
                )
            with t4:
                st.markdown("**Ensemble**")
                st.markdown(
                    f"<span style='color:#16a34a'>{result['ens_home']*100:.1f}%</span> "
                    f"`{_prob_bar(result['ens_home'])}`",
                    unsafe_allow_html=True,
                )
                st.markdown(f"{result['ens_draw']*100:.1f}% `{_prob_bar(result['ens_draw'])}`")
                st.markdown(
                    f"<span style='color:#16a34a'>{result['ens_away']*100:.1f}%</span> "
                    f"`{_prob_bar(result['ens_away'])}`",
                    unsafe_allow_html=True,
                )
            with t5:
                st.caption("🔼 Modelo + optimista\n🔽 Mercado + optimista")
                st.caption(
                    f"Fuente: {', '.join(mkt.get('bookmakers', ['N/A']))[:40]}"
                )
                if mkt.get("overround"):
                    st.caption(f"Margen: {mkt['overround']:.1f}%")

            with st.expander("🧠 Factores Contextuales"):
                cx1, cx2 = st.columns(2)
                with cx1:
                    st.markdown(f"**{match['home']}** (φ={result['ctx_home']:.3f})")
                    for note in result["notes_home"][:4]:
                        st.caption(note)
                with cx2:
                    st.markdown(f"**{match['away']}** (φ={result['ctx_away']:.3f})")
                    for note in result["notes_away"][:4]:
                        st.caption(note)

            # ── Rendimiento en el Mundial & Noticias ────────────────
            with st.expander("📈 Rendimiento en el Mundial & Noticias"):
                form_home = get_team_form(match["home"])
                form_away = get_team_form(match["away"])
                news_home = get_team_news(match["home"])
                news_away = get_team_news(match["away"])

                fx1, fx2 = st.columns(2)
                with fx1:
                    st.markdown(f"**{match['home']}** — Récord: {form_home['record']} | GF:{form_home['gf']} GA:{form_home['ga']} | Racha: {form_home['streak']}")
                    for m in form_home["matches"]:
                        st.caption(f"{m['status']} vs {m['opponent']} {m['score']}")
                    st.markdown("---")
                    for n in news_home[:3]:
                        st.caption(n)
                with fx2:
                    st.markdown(f"**{match['away']}** — Récord: {form_away['record']} | GF:{form_away['gf']} GA:{form_away['ga']} | Racha: {form_away['streak']}")
                    for m in form_away["matches"]:
                        st.caption(f"{m['status']} vs {m['opponent']} {m['score']}")
                    st.markdown("---")
                    for n in news_away[:3]:
                        st.caption(n)

        st.markdown("")  # espacio entre partidos

    st.divider()

# ══════════════════════════════════════════════════════════════════════════
# PRÓXIMOS PARTIDOS
# ══════════════════════════════════════════════════════════════════════════

upcoming = get_upcoming_matches()
if upcoming:
    st.header("🟡 PRÓXIMOS PARTIDOS")

    for i in range(0, len(upcoming), 2):
        cols = st.columns(2)
        for j, match in enumerate(upcoming[i:i+2]):
            with cols[j]:
                result = predict_single_match(match)
                if "error" in result:
                    st.warning(f"{match['home']} vs {match['away']}: sin datos")
                    continue

                pred = result["pred"]
                mkt = result["market"]

                with st.container(border=True):
                    st.markdown(
                        f"**{match['home']} vs {match['away']}** · {match['cst']}"
                    )
                    st.caption(
                        f"Grupo {match['group']} · {match['stadium']}, {match['city']}"
                    )

                    # KPIs compactos
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

                    # Comparativa compacta
                    with st.expander("📊 Comparativa con Mercado"):
                        comp_data = pd.DataFrame({
                            "Resultado": [
                                f"🏠 {match['home']}",
                                "🤝 Empate",
                                f"🚩 {match['away']}",
                            ],
                            "FutFox": [
                                f"{pred.prob_home*100:.1f}%",
                                f"{pred.prob_draw*100:.1f}%",
                                f"{pred.prob_away*100:.1f}%",
                            ],
                            "Mercado": [
                                f"{mkt['prob_home']*100:.1f}%",
                                f"{mkt['prob_draw']*100:.1f}%",
                                f"{mkt['prob_away']*100:.1f}%",
                            ],
                            "Ensemble": [
                                f"{result['ens_home']*100:.1f}%",
                                f"{result['ens_draw']*100:.1f}%",
                                f"{result['ens_away']*100:.1f}%",
                            ],
                        })
                        st.dataframe(comp_data, hide_index=True, use_container_width=True)
                        source_label = "Real" if mkt["source"] == "api" else "Sintético"
                        st.caption(
                            f"Fuente mercado: {source_label} | "
                            f"Bookmakers: {', '.join(mkt.get('bookmakers', ['N/A']))[:50]}"
                        )

                    with st.expander("🧠 Contexto"):
                        cx1, cx2 = st.columns(2)
                        with cx1:
                            st.caption(f"**{match['home']}** φ={result['ctx_home']:.3f}")
                            for note in result["notes_home"][:2]:
                                st.caption(note)
                        with cx2:
                            st.caption(f"**{match['away']}** φ={result['ctx_away']:.3f}")
                            for note in result["notes_away"][:2]:
                                st.caption(note)

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