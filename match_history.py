"""
match_history.py — Resultados de la fase de grupos del Mundial 2026.

Proporciona el historial de partidos completados para cada selección
y funciones para calcular forma reciente (W-D-L, goles, racha).

Autor: FutFox Prediction Engine
"""

# Resultados completados de la fase de grupos (ficticios pero realistas)
# Formato: (local, visitante, goles_local, goles_visitante, grupo)

RESULTS = [
    # ── Grupo A ──────────────────────────────────────────────────────
    ("Cabo Verde", "Nueva Zelanda", 1, 1, "A"),
    ("Arabia Saudita", "Francia", 0, 4, "A"),
    ("Cabo Verde", "Portugal", 0, 3, "A"),
    ("Arabia Saudita", "Nueva Zelanda", 2, 1, "A"),
    # ── Grupo B ──────────────────────────────────────────────────────
    ("Uruguay", "Corea del Sur", 2, 1, "B"),
    ("España", "Costa Rica", 3, 0, "B"),
    ("Uruguay", "Alemania", 0, 2, "B"),
    ("España", "Canadá", 2, 1, "B"),
    # ── Grupo C ──────────────────────────────────────────────────────
    ("Bélgica", "Senegal", 2, 0, "C"),
    ("Nueva Zelanda", "Serbia", 1, 2, "C"),
    ("Bélgica", "Serbia", 3, 1, "C"),
    # ── Grupo D ──────────────────────────────────────────────────────
    ("Egipto", "Perú", 2, 0, "D"),
    ("Irán", "Croacia", 1, 1, "D"),
    ("Egipto", "Croacia", 0, 1, "D"),
    ("Irán", "Perú", 3, 1, "D"),
    # ── Grupo E ──────────────────────────────────────────────────────
    ("México", "Suiza", 2, 1, "E"),
    ("Japón", "Senegal", 2, 0, "E"),
    ("México", "Senegal", 1, 0, "E"),
    ("Japón", "Suiza", 1, 0, "E"),
    # ── Grupo F ──────────────────────────────────────────────────────
    ("Argentina", "Dinamarca", 2, 1, "F"),
    ("Portugal", "Nigeria", 3, 0, "F"),
    ("Argentina", "Nigeria", 4, 1, "F"),
    ("Portugal", "Dinamarca", 1, 1, "F"),
    # ── Grupo G ──────────────────────────────────────────────────────
    ("Brasil", "Italia", 2, 1, "G"),
    ("Alemania", "Camerún", 3, 0, "G"),
    ("Brasil", "Camerún", 3, 0, "G"),
    ("Alemania", "Italia", 1, 1, "G"),
    # ── Grupo H ──────────────────────────────────────────────────────
    ("Inglaterra", "Ghana", 3, 1, "H"),
    ("Croacia", "Estados Unidos", 2, 1, "H"),
    ("Inglaterra", "Estados Unidos", 2, 0, "H"),
    ("Croacia", "Ghana", 1, 0, "H"),
]


def get_team_form(team: str) -> dict:
    """
    Retorna el historial de partidos completados de una selección.
    Intenta obtenerlos de la API real, si no, usa el fallback local.
    """
    import live_api
    api_games = live_api.fetch_games()
    
    matches_list = []
    
    if api_games is not None:
        for g in api_games:
            finished_val = str(g.get("finished", "FALSE")).upper().strip()
            time_elapsed = str(g.get("time_elapsed", "")).strip().lower()
            if finished_val == "TRUE" or time_elapsed == "finished":
                home = g.get("home_team_name_en", "")
                away = g.get("away_team_name_en", "")
                
                try:
                    gf = int(g.get("home_score", 0))
                    ga = int(g.get("away_score", 0))
                except (ValueError, TypeError):
                    continue
                    
                group = g.get("group", "")
                matches_list.append((home, away, gf, ga, group))
    else:
        matches_list = RESULTS

    matches = []
    gf_total = 0
    ga_total = 0
    results_sequence = []

    for home, away, gf, ga, group in matches_list:
        if home == team:
            result = "W" if gf > ga else ("D" if gf == ga else "L")
            matches.append({
                "opponent": away,
                "result": result,
                "gf": gf,
                "ga": ga,
                "score": f"{gf}-{ga}",
                "status": "✅" if result == "W" else ("🤝" if result == "D" else "❌"),
                "group": group,
            })
            gf_total += gf
            ga_total += ga
            results_sequence.append(result)
        elif away == team:
            result = "W" if ga > gf else ("D" if ga == gf else "L")
            matches.append({
                "opponent": home,
                "result": result,
                "gf": ga,
                "ga": gf,
                "score": f"{ga}-{gf}",
                "status": "✅" if result == "W" else ("🤝" if result == "D" else "❌"),
                "group": group,
            })
            gf_total += ga
            ga_total += gf
            results_sequence.append(result)

    w = results_sequence.count("W")
    d = results_sequence.count("D")
    l = results_sequence.count("L")

    # Racha (últimos 3 resultados)
    streak = "-".join(results_sequence[-3:]) if results_sequence else "Sin partidos"

    return {
        "matches": matches,
        "record": f"{w}-{d}-{l}",
        "gf": gf_total,
        "ga": ga_total,
        "streak": streak,
        "played": len(matches),
    }