#!/usr/bin/env python3
"""
mcp_server.py — MCP Server para FutFox Prediction Engine.

Expone el motor de prediccion FutFox como herramientas para agentes AI
via el protocolo MCP (Model Context Protocol) usando JSON-RPC sobre stdio.

Tools expuestas:
  - predict_match: Predice resultado de un partido usando modelo Poisson
  - get_live_matches: Lista partidos en vivo con predicciones
  - get_market_odds: Obten cuotas del mercado mexicano para un partido
  - get_team_news: Noticias recientes de una seleccion

Uso:
  python3 mcp_server.py
  (conecta via stdio JSON-RPC)

Autor: FutFox Prediction Engine
"""

import sys
import json
import traceback

# === MCP JSON-RPC Handler ===

def handle_request(request: dict) -> dict:
    """Procesa una solicitud JSON-RPC y retorna la respuesta."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "futfox-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": _get_tools()}}

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = _call_tool(tool_name, arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)}
            }

    elif method == "notifications/initialized":
        return None  # No response needed for notifications

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }


def _get_tools() -> list:
    return [
        {
            "name": "predict_match",
            "description": "Predice el resultado de un partido de futbol usando el modelo Poisson compuesto de FutFox con metricas xG. Retorna probabilidades de local/empate/visitante, over 2.5, BTTS, marcador mas probable y top 5 marcadores.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "home_team": {"type": "string", "description": "Equipo local (ej: 'Argentina', 'Brasil')"},
                    "away_team": {"type": "string", "description": "Equipo visitante (ej: 'Alemania', 'Francia')"},
                    "league": {"type": "string", "description": "Liga: 'WC' para Mundial 2026, 'EPL' para Premier League"},
                    "season": {"type": "integer", "description": "Temporada (ej: 2026 para Mundial)"}
                },
                "required": ["home_team", "away_team"]
            }
        },
        {
            "name": "get_live_matches",
            "description": "Obtiene la lista de partidos en vivo del Mundial 2026 con sus probabilidades FutFox y cuotas del mercado mexicano.",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_market_odds",
            "description": "Obten las cuotas de casa de apuestas mexicana (Money Line 90 min) para un partido del Mundial 2026, incluyendo probabilidades implicitas sin margen.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "home_team": {"type": "string", "description": "Equipo local"},
                    "away_team": {"type": "string", "description": "Equipo visitante"}
                },
                "required": ["home_team", "away_team"]
            }
        },
        {
            "name": "get_team_news",
            "description": "Obten noticias recientes y contexto de una seleccion del Mundial 2026.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Nombre de la seleccion"}
                },
                "required": ["team"]
            }
        },
    ]


def _call_tool(tool_name: str, args: dict) -> dict:
    # Suprimir prints de los modulos durante la ejecucion de tools
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        if tool_name == "predict_match":
            return _tool_predict_match(args)
        elif tool_name == "get_live_matches":
            return _tool_get_live_matches()
        elif tool_name == "get_market_odds":
            return _tool_get_market_odds(args)
        elif tool_name == "get_team_news":
            return _tool_get_team_news(args)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    finally:
        sys.stdout = old_stdout


def _tool_predict_match(args: dict) -> dict:
    home = args.get("home_team", "")
    away = args.get("away_team", "")
    league = args.get("league", "WC")
    season = args.get("season", 2026)

    from data_collection import run_collection
    from model_poisson import predict_match
    from player_impact import analyze_player_impact

    ls, hp, ap, lavgs, is_wc = run_collection(
        league=league, season=season, home_team=home, away_team=away)
    impact = analyze_player_impact(hp, ap, ls, verbose=False)
    pred = predict_match(
        home_team=home, away_team=away,
        league_stats=ls, league_averages=lavgs,
        player_adjustment_home=impact["alpha_home"],
        player_adjustment_away=impact["alpha_away"])

    return {
        "content": [{"type": "text", "text": json.dumps({
            "home_team": home,
            "away_team": away,
            "league": league,
            "season": f"{season}/{season+1}",
            "prob_home_pct": round(pred.prob_home * 100, 1),
            "prob_draw_pct": round(pred.prob_draw * 100, 1),
            "prob_away_pct": round(pred.prob_away * 100, 1),
            "prob_over_25_pct": round(pred.prob_over_25 * 100, 1),
            "prob_btts_pct": round(pred.prob_btts * 100, 1),
            "most_likely_score": pred.most_likely_score,
            "most_likely_score_prob_pct": round(pred.most_likely_score_prob * 100, 1),
            "lambda_home": round(pred.lambda_home, 4),
            "lambda_away": round(pred.lambda_away, 4),
            "expected_goals": round(pred.expected_goals, 2),
            "top_3_scores": [
                {"score": s[0], "prob_pct": round(s[1] * 100, 1)}
                for s in pred.top_scores[:3]
            ],
        }, ensure_ascii=False)}]
    }


def _tool_get_live_matches() -> dict:
    from worldcup_schedule import get_all_matches, get_countdown
    matches = get_all_matches()
    live_and_upcoming = [m for m in matches if m["status"] in ("live", "upcoming")]

    result = []
    for m in live_and_upcoming[:10]:
        entry = {
            "home": m["home"],
            "away": m["away"],
            "cst": m["cst"],
            "countdown": get_countdown(m.get("datetime", "")),
            "status": m["status"],
            "group": m["group"],
            "stadium": m["stadium"],
            "city": m["city"],
        }
        if m["status"] == "live":
            entry["score"] = f"{m.get('score_home', 0)}-{m.get('score_away', 0)}"
            entry["minute"] = m.get("minute", 0)

        # Intentar obtener cuotas mexicanas
        try:
            from odds_mexico import get_mexico_odds
            odds = get_mexico_odds(m["home"], m["away"])
            if odds:
                entry["odds_mexico"] = {
                    "home": odds["home_odds"],
                    "draw": odds["draw_odds"],
                    "away": odds["away_odds"],
                    "prob_home_pct": round(odds["prob_home"] * 100, 1),
                    "prob_draw_pct": round(odds["prob_draw"] * 100, 1),
                    "prob_away_pct": round(odds["prob_away"] * 100, 1),
                }
        except Exception:
            pass

        result.append(entry)

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


def _tool_get_market_odds(args: dict) -> dict:
    home = args.get("home_team", "")
    away = args.get("away_team", "")

    try:
        from odds_mexico import get_mexico_odds, odds_to_probabilities
        odds = get_mexico_odds(home, away)
        if odds:
            return {"content": [{"type": "text", "text": json.dumps({
                "home_team": home,
                "away_team": away,
                "bookmaker": "Caliente (Mexico)",
                "home_odds": odds["home_odds"],
                "draw_odds": odds["draw_odds"],
                "away_odds": odds["away_odds"],
                "prob_home_pct": round(odds["prob_home"] * 100, 1),
                "prob_draw_pct": round(odds["prob_draw"] * 100, 1),
                "prob_away_pct": round(odds["prob_away"] * 100, 1),
                "overround_pct": odds["overround_pct"],
            }, ensure_ascii=False)}]}
    except Exception as e:
        pass

    return {"content": [{"type": "text", "text": json.dumps({
        "error": f"No hay cuotas mexicanas para {home} vs {away}",
        "available_matches": "Usa get_live_matches para ver partidos disponibles"
    }, ensure_ascii=False)}]}


def _tool_get_team_news(args: dict) -> dict:
    team = args.get("team", "")
    try:
        from news_feed import get_team_news
        news = get_team_news(team)
        return {"content": [{"type": "text", "text": json.dumps({
            "team": team,
            "news": news
        }, ensure_ascii=False)}]}
    except Exception:
        return {"content": [{"type": "text", "text": json.dumps({
            "team": team,
            "news": ["Sin noticias disponibles"]
        }, ensure_ascii=False)}]}


# === Main loop ===
def main():
    """Loop principal: lee JSON-RPC de stdin, responde por stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            pass
        except Exception:
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
