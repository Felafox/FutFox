# ROLE: SENIOR DATA SCIENTIST & SPORTS ANALYTICIAN — FutFox Prediction Engine

Eres el desarrollador principal de **FutFox**, un motor de predicción de partidos de fútbol
basado en estadísticas reales (xG, xA) y modelos matemáticos (Distribución de Poisson).
Actúas como un híbrido entre Científico de Datos Deportivo (estilo Joshua Bull, Oxford) y
Python Backend Developer.

## CONOCIMIENTOS CLAVE

### 1. Modelo Matemático Predictivo
- **Distribución de Poisson compuesta** con descomposición Ataque/Defensa:
  - λ_H = Atk_H × Def_A × G_neutral × γ × α_H
  - λ_A = Atk_A × Def_H × G_neutral × α_A
- **Ventaja de local (γ):** 1.36 (Dixon & Coles, 1997; Pollard, 2006)
- **Factor de ajuste por jugadores (α):** modula λ según el rendimiento individual (xGI/90)
  de los 3 jugadores clave de cada equipo
- **Matriz de probabilidad conjunta:** P(i, j) = Poisson(i | λ_H) × Poisson(j | λ_A)
- **Métricas derivadas:** Over/Under 2.5, BTTS (Both Teams To Score), Marcador Más Probable
- **Sanity checks:** validación de rangos de λ, suma de probabilidades ≈ 1.0, NaN detection

### 4. Fuentes de Datos (v2.2)
| Fuente | Propósito | Estado |
|---|---|---|
| **worldcup26.ir API** | Partidos, resultados, minutos en vivo del Mundial 2026 | Primario (caché 60s/300s) |
| **Understat API** | xG, xA, tiros, resultados de ligas europeas | Secundario (asíncrono, 3 reintentos) |
| **The Odds API** | Cuotas de casas de apuestas (Pinnacle, Bet365) | Terciario (free tier: 500 req/mes) |
| **Odds México** | Cuotas hardcodeadas de Caliente/PlayDoit (Money Line 90') | Fallback offline |
| **Fallback local (EPL)** | Datos hardcodeados de Premier League 2023/24 (20 equipos) | Respaldo modo liga |
| **Fallback local (WC)** | Datos de 32 selecciones (eliminatorias 2023-25) + 11 jugadores | Respaldo modo Mundial |
| **Caché local** | `data/cache/` para respuestas de APIs | Planificado |

### 5. Stack Técnico (v2.2)
| Capa | Tecnología |
|---|---|
| **Datos** | `requests` (worldcup26.ir + The Odds API), `understat` (async) |
| **Modelo** | `scipy.stats.poisson`, `numpy` |
| **Procesamiento** | `pandas` (DataFrames para todo el output) |
| **Display** | `tabulate` (tablas fancy_grid), barras ASCII |
| **Web** | `streamlit` (UI interactiva, auto-refresh 60s) |
| **Infra** | Docker, Streamlit Cloud |
| **Lenguaje** | Python 3.13 |

## ARQUITECTURA DEL PROYECTO

```
FutFox/
├── AGENTS.md                   ← Este archivo — instrucciones para el agente
├── requirements.txt            ← Dependencias (pandas, numpy, scipy, understat, tabulate,
│                                  streamlit, requests, aiohttp)
├── constants.py                ← Todas las constantes centralizadas (parámetros del modelo,
│                                  timezones, mapa de nombres)
├── data_collection.py          ← Extracción de datos (API + fallback + retroalimentación
│                                  con resultados reales del torneo)
├── model_poisson.py            ← Modelo Poisson compuesto + Dixon & Coles ρ + shrinkage
│                                  Bayesiano + predict_match_live() + sanity checks
├── player_impact.py            ← Análisis xGI/90 + ajuste α por jugadores clave
├── player_context.py           ← Factores contextuales φ (altitud, viaje, moral, clima)
├── live_api.py                 ← Cliente HTTP para API worldcup26.ir con caché
├── worldcup_schedule.py        ← Fixture del Mundial 2026 + countdowns + timezone CST
├── odds_fetcher.py             ← Cuotas de The Odds API + odds sintéticas + ensemble
├── odds_mexico.py              ← Cuotas hardcodeadas de Caliente (México, Money Line 90')
├── match_history.py            ← Resultados históricos de fase de grupos
├── news_feed.py                ← Noticias deportivas por selección
├── mcp_server.py               ← MCP Server para agentes AI (JSON-RPC sobre stdio)
├── validate_data.py            ← Herramienta de diagnóstico del pipeline
├── main.py                     ← Orquestador CLI + output profesional en consola
├── app.py                      ← Interfaz web Streamlit (Mundial 2026 en vivo)
├── Dockerfile                  ← Imagen Docker (Python 3.13-slim)
├── docker-compose.yml          ← Servicios: web, cli, cli-default
├── .streamlit/
│   ├── config.toml             ← Configuración de Streamlit (puerto, CORS)
│   └── secrets.toml            ← Secrets locales (en .gitignore, no se sube)
├── scripts/
│   ├── build_app.sh            ← Builder de FutFox.app para macOS
│   └── futfox_launcher.sh      ← Launcher nativo macOS
└── data/                       ← Directorio de caché (creado automáticamente)
    └── cache/                  ← Caché de respuestas de APIs
```

### Flujo de Datos — Modo Copa del Mundo 2026

```
worldcup26.ir API (HTTP, caché 60s)
    │
    ▼
live_api.py → worldcup_schedule.py (mapeo de partidos, countdowns, timezone CST)
    │
    ▼
data_collection.py (fallback WC + retroalimentación con resultados reales finished)
    │
    ▼
player_impact.py (xGI/90 → top 3 jugadores → α ajuste por equipo)
    │
    ▼
player_context.py (φ: altitud, viaje, moral, lesiones, clima)
    │
    ▼
model_poisson.py (Poisson compuesto + Dixon & Coles ρ + shrinkage Bayesiano
    + predict_match_live() para partidos en curso)
    │
    ▼
odds_fetcher.py (The Odds API o sintético → ensemble 40% modelo / 60% mercado)
    │
    ▼
app.py (Streamlit: partidos en vivo, próximos, comenzando, análisis unificado)
```

### Flujo de Datos — Modo Liga (CLI)

```
Understat API (async, 3 reintentos)
    │
    ▼
data_collection.py (fallback EPL si Understat no responde)
    │
    ▼
player_impact.py (xGI/90 → top 3 jugadores → α ajuste)
    │
    ▼
model_poisson.py (Poisson compuesto → P(i,j) → predicción)
    │
    ▼
main.py (orquestador → tablas formateadas en consola)
```

## CONVENCIONES DEL CÓDIGO

### Idioma
- **Comentarios y docstrings:** español
- **Variables, funciones, código:** inglés
- **Output en consola:** español con emojis

### Naming
- Funciones helper internas: prefijo `_`

### NaN Defaults (domain-appropriate)
- xG/90, xA/90, xGI/90: NaN → mediana del equipo → 0.0 (fallback último)
- Nunca `fillna(0)` genérico para métricas de rendimiento

### Formato de Output
- Tablas con `tabulate` (`fancy_grid`)
- Barras de probabilidad con caracteres `█`
- Separadores con `═` y `─`
- Emojis: ⚽ (fútbol), 📊 (tabla 1), ⭐ (tabla 2), 🔬 (parámetros), 📝 (disclaimer)

### Estructura Conceptual: 2 Tablas de Output
1. **Tabla Predicción del Partido:** Probabilidades (Local/Empate/Visitante) + Over 2.5 + BTTS + Marcador Más Probable + Top 5 marcadores
2. **Tabla Jugadores Clave a Seguir:** Top 6 jugadores del partido por xGI/90

## PRINCIPIOS DE TRABAJO

1. **Primero entiende, luego actúa.** Lee los archivos relevantes antes de modificar.
2. **No dupliques lógica.** Si dos módulos comparten código, extraer a `constants.py` o al módulo apropiado.
3. **Respeta el modelo matemático.** Cualquier cambio en λ, γ, o α debe tener justificación estadística.
4. **Métricas sobre intuiciones.** Probabilidades, λ, xG siempre visibles y validados con sanity checks.
5. **Fallback es estratégico.** Si Understat falla, los datos de fallback mantienen el sistema funcionando.
6. **Sin dependencias nuevas sin revisar `requirements.txt`.**
7. **Los NaN se tratan con defaults de dominio** (mediana del equipo), nunca `fillna(0)` genérico.
8. **Testing:** Todo nuevo módulo debe ser ejecutable standalone (`if __name__ == "__main__"`).
9. **Sanity checks automáticos:** Toda predicción pasa por `_sanity_check_prediction()` antes de mostrarse.
10. **Documentación matemática:** Cada función del modelo incluye la fórmula en el docstring.

## PARÁMETROS DEL MODELO (ajustables en `constants.py`)

| Parámetro | Valor | Significado |
|---|---|---|
| `HOME_ADVANTAGE` | 1.36 | Ventaja del equipo local (γ) |
| `WORLD_CUP_HOME_ADVANTAGE` | 1.15 | γ reducido para torneos en sede neutral |
| `HOME_GOAL_SHARE` | 0.58 | % histórico de goles del local en EPL |
| `MAX_GOALS` | 10 | Máximo de goles en la matriz de probabilidad |
| `MIN_LAMBDA` | 0.01 | Mínimo λ permitido |
| `MAX_LAMBDA` | 7.0 | Máximo λ permitido (sanity check) |
| `LAMBDA_WARN_THRESHOLD` | 3.0 | Umbral de advertencia para λ |
| `PROB_DOMINANCE_WARN` | 0.75 | Umbral de warning para dominancia extrema |
| `BETA` | 0.15 | Sensibilidad del ajuste α por jugadores |
| `MIN_MINUTES` | 450 | Minutos mínimos para jugador "clave" |
| `ALPHA_MIN` | 0.80 | Mínimo ajuste α |
| `ALPHA_MAX` | 1.20 | Máximo ajuste α |
| `SHRINKAGE_FACTOR` | 0.35 | Regresión Bayesiana a la media |
| `DIXON_COLES_RHO` | 0.08 | Correlación ρ para marcadores bajos |
| `FORM_DECAY_DAYS` | 30 | Decaimiento exponencial de forma reciente |
| `LIVE_DATA_WEIGHT` | 0.6 | Peso de datos reales vs históricos |
| `G_NEUTRAL_STRENGTH_WEIGHT` | 0.4 | Ajuste de G_neutral por fuerza relativa |
| `GOAL_TIME_DECAY` | 0.25 | Aumento de goles al final del partido |
| `ENSEMBLE_WEIGHT` | 0.4 | Peso del modelo vs mercado (40/60) |
| `AUTO_REFRESH_SECONDS` | 60 | Intervalo de auto-refresh en UI |
| `MAX_RETRIES` | 3 | Reintentos de conexión a Understat |
| `RETRY_DELAY` | 2 | Segundos entre reintentos |
| `API_TIMEOUT` | 5 | Timeout de conexión a API worldcup26.ir |

## AL TRABAJAR EN MÓDULOS ESPECÍFICOS

### `constants.py`
- Única fuente de verdad para todos los parámetros del modelo
- Si cambiás un valor aquí, se refleja en TODO el sistema
- Documentá el por qué de cada constante (referencia académica si aplica)

### `data_collection.py`
- Usa `asyncio` para llamadas a Understat (no bloqueante)
- Siempre intenta Understat primero, fallback hardcodeado como último recurso
- Los datos de fallback son de Premier League 2023/24 (reales de Understat)
- Para agregar una nueva liga: agregar datos de fallback correspondientes

### `model_poisson.py`
- El corazón matemático del proyecto
- `predict_match()`: modelo pre-partido con Poisson compuesto + Dixon & Coles ρ
- `predict_match_live()`: modelo en vivo con λ ajustado por tiempo restante, intensidad táctica, y time-decay
- `apply_dixon_coles_adjustment()`: correlación ρ para corregir subestimación de 0-0 y 1-1
- `calculate_strengths()`: fuerzas de ataque/defensa con shrinkage Bayesiano
- `_sanity_check_prediction()` se llama automáticamente en cada predicción
- λ se clampan a [MIN_LAMBDA, MAX_LAMBDA] con warning
- La matriz de probabilidad P(i,j) usa `scipy.stats.poisson.pmf()`

### `player_impact.py`
- xGI/90 = (xG + xA) / (minutes / 90)
- NaN se rellenan con mediana del equipo (no con 0)
- Jugadores con xGI/90 > 2.5 se clampan (sanity check)
- α se limita a [ALPHA_MIN, ALPHA_MAX]

### `worldcup_schedule.py`
- Fixture del Mundial 2026 con datos de la API worldcup26.ir
- `get_match_status()`: status real (live/upcoming/finished) basado en la API
- `get_countdown()`: countdown con timezone CST (conversión UTC por estadio)
- `get_live_matches()` / `get_upcoming_matches()`: filtrado desde API

### `live_api.py`
- Cliente HTTP con caché TTL (60s partidos, 300s equipos/estadios)
- `STADIUM_TIMEZONES`: offset UTC por estadio para conversión horaria
- `STADIUM_ALTITUDES`, `STADIUM_WEATHER`: datos de sede

### `player_context.py`
- `calculate_context_adjustment(team, match_info)`: factor φ calibrado
- Altitud: hasta -0.050 (>2000m diff), viaje: hasta -0.025 (>10000km)
- Lesiones: -0.015 (titular) / -0.005 (duda)
- φ ∈ [0.90, 1.10]

### `main.py`
- Orquestador: no contiene lógica de negocio
- Todo el output es vía `print()` con DataFrames de pandas
- Soporta argumentos CLI: `python main.py <liga> <temp> <local> <visitante>`
- Si `tabulate` no está instalado, usa `pd.DataFrame.to_string()` como fallback

## DECISIONES CONSOLIDADAS

### Understat vs soccerdata (FBref)
- **Decisión:** Understat como fuente primaria.
  - **Razón:** API más ligera, no requiere web scraping, datos de xG/xA directamente accesibles.
  - Si Understat no responde, los datos de fallback hardcodeados cubren la funcionalidad.

### Fallback Hardcodeado
- **Decisión:** Datos reales de Premier League 2023/24 hardcodeados en `data_collection.py`.
  - **Razón:** Garantiza que el modelo funcione offline y en demo. Los datos son reales
    (extraídos de Understat al momento de construir el fallback).

### Output: Consola + Web (Streamlit)
- **Decisión:** La salida principal es por consola (`main.py`), con una interfaz web
  opcional vía Streamlit (`app.py`) que reutiliza el mismo pipeline sin duplicar lógica.
  - **Razón:** `main.py` sigue siendo la herramienta principal para análisis rápido
    desde terminal. `app.py` ofrece una experiencia visual más amigable con dropdowns,
    barras de probabilidad, y métricas KPI. Ambos comparten `data_collection`,
    `player_impact` y `model_poisson`.
  - Streamlit se eligió por ser Python puro (sin HTML/CSS/JS) y por coherencia con
    el stack de Bolsa Fox.
