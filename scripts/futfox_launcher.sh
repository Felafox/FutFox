#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────
# FutFox Launcher — Compatible con Apple Silicon (M1/M2/M3/M4)
# Detecta Python automáticamente, usa rutas absolutas para Finder.
# ──────────────────────────────────────────────────────────────────────────

# ── Auto-detectar Python (buscar en paths comunes) ──────────────────
find_python() {
    for candidate in \
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" \
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" \
        "/opt/homebrew/bin/python3" \
        "/usr/local/bin/python3" \
        "/usr/bin/python3"
    do
        if [ -f "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

PYTHON=$(find_python)
if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "FutFox no puede iniciar.\n\nNo se encontró Python 3.11+ instalado.\n\nInstalá Python desde python.org o Homebrew:\n  brew install python@3.13" buttons {"OK"} default button "OK" with icon stop' &
    exit 1
fi

# ── Usar python -m streamlit (más portable que el binario directo) ──
STREAMLIT_CMD="$PYTHON -m streamlit"

# ── Verificar que streamlit está instalado ──────────────────────────
if ! $PYTHON -c "import streamlit" 2>/dev/null; then
    osascript -e 'display dialog "FutFox no puede iniciar.\n\nStreamlit no está instalado.\n\nEjecutá en Terminal:\n  pip3 install streamlit" buttons {"OK"} default button "OK" with icon stop' &
    exit 1
fi

# ── Limpiar variables de entorno que interfieren (Finder puede inyectar) ─
unset PYTHONPATH
unset PYTHONHOME
unset PYTHONSTARTUP

# ── Directorio del proyecto ─────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" 2>/dev/null || dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

# ── Verificar que no estamos en un directorio con numpy source ─────
if [ -d "$PROJECT_DIR/numpy" ]; then
    osascript -e "display dialog \"Error: Se detectó un directorio 'numpy' en el proyecto.\n\nEliminalo con:\n  rm -rf $PROJECT_DIR/numpy\" buttons {\"OK\"} default button \"OK\" with icon stop" &
    exit 1
fi

# ── Verificar app.py ────────────────────────────────────────────────
if [ ! -f "app.py" ]; then
    osascript -e "display dialog \"FutFox no puede iniciar.\\n\\nNo se encontró app.py\" buttons {\"OK\"} default button \"OK\" with icon stop" &
    exit 1
fi

# ── Puerto ──────────────────────────────────────────────────────────
PORT="${FUTFOX_PORT:-8501}"

# ── Limpiar puerto si ya está en uso ────────────────────────────────
lsof -ti:"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null

echo "⚽ FutFox — Copa del Mundo 2026"
echo "   Python:   $PYTHON"
echo "   Proyecto: $PROJECT_DIR"
echo "   URL:      http://localhost:$PORT"

# ── Abrir navegador ──────────────────────────────────────────────────
(sleep 3 && open "http://localhost:$PORT") &

# ── Iniciar Streamlit ────────────────────────────────────────────────
exec $STREAMLIT_CMD run app.py \
    --server.port "$PORT" \
    --server.headless true \
    --browser.serverAddress "localhost" \
    --server.enableCORS false \
    --server.enableXsrfProtection false