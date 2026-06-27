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

### 2. Fuentes de Datos
| Fuente | Propósito | Estado |
|---|---|---|
| **Understat API** | xG, xA, tiros, resultados de ligas europeas | Primario (asíncrono, 3 reintentos) |
| **Fallback local** | Datos hardcodeados de Premier League 2023/24 (20 equipos, 5 jugadores c/u) | Respaldo automático |
| **Caché local** | `data/cache/` para respuestas de Understat | Planificado (constantes definidas) |

### 3. Métricas Avanzadas Utilizadas
- **xG (Expected Goals):** Probabilidad de que un disparo resulte en gol
- **xA (Expected Assists):** Probabilidad de que un pase resulte en asistencia
- **xGI (Expected Goal Involvements):** xG + xA por 90 minutos
- **Fuerza de Ataque:** GF_per_game / avg(GF_liga)
- **Fuerza de Defensa:** GA_per_game / avg(GA_liga)

### 4. Stack Técnico
| Capa | Tecnología |
|---|---|
| **Datos** | `understat` (async), fallback hardcodeado |
| **Modelo** | `scipy.stats.poisson`, `numpy` |
| **Datos** | `pandas` (DataFrames para todo el output) |
| **Display** | `tabulate` (tablas fancy_grid), barras ASCII |
| **Lenguaje** | Python 3.13 |

## ARQUITECTURA DEL PROYECTO

```
FutFox/
├── AGENTS.md                   ← Este archivo — instrucciones para el agente
├── requirements.txt            ← Dependencias (pandas, numpy, scipy, understat, tabulate)
├── constants.py                ← Todas las constantes centralizadas (parámetros del modelo)
├── data_collection.py          ← Extracción de datos de Understat + fallback local
├── model_poisson.py            ← Modelo matemático Poisson completo + sanity checks
├── player_impact.py            ← Análisis xGI/90 + ajuste α por jugadores clave
├── main.py                     ← Orquestador CLI + output profesional en consola
├── app.py                      ← Interfaz web con Streamlit (mismo pipeline, UI interactiva)
└── data/                       ← Directorio de caché (creado automáticamente)
    └── cache/                  ← Caché de respuestas de Understat
```

### Flujo de Datos

```
Understat API (async)
    │
    ▼
data_collection.py (3 reintentos + fallback local)
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
| `HOME_GOAL_SHARE` | 0.58 | % histórico de goles del local en EPL |
| `MAX_GOALS` | 10 | Máximo de goles en la matriz de probabilidad |
| `MIN_LAMBDA` | 0.01 | Mínimo λ permitido |
| `MAX_LAMBDA` | 8.0 | Máximo λ permitido (sanity check) |
| `BETA` | 0.15 | Sensibilidad del ajuste α por jugadores |
| `MIN_MINUTES` | 450 | Minutos mínimos para jugador "clave" (~5 partidos) |
| `ALPHA_MIN` | 0.80 | Mínimo ajuste α por jugadores |
| `ALPHA_MAX` | 1.20 | Máximo ajuste α por jugadores |
| `MAX_RETRIES` | 3 | Reintentos de conexión a Understat |
| `RETRY_DELAY` | 2 | Segundos entre reintentos |

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
- `_sanity_check_prediction()` se llama automáticamente en cada predicción
- λ se clampan a [MIN_LAMBDA, MAX_LAMBDA] con warning
- La matriz de probabilidad P(i,j) usa `scipy.stats.poisson.pmf()`

### `player_impact.py`
- xGI/90 = (xG + xA) / (minutes / 90)
- NaN se rellenan con mediana del equipo (no con 0)
- Jugadores con xGI/90 > 2.5 se clampan (sanity check)
- α se limita a [ALPHA_MIN, ALPHA_MAX]

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
