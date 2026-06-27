# ═══════════════════════════════════════════════════════════════════════════
# FutFox Prediction Engine — Docker Image
# ═══════════════════════════════════════════════════════════════════════════
#
# Modos de uso:
#   Streamlit (web):  docker run -p 8501:8501 futfox
#   CLI (predicción): docker run futfox python main.py EPL 2024 Arsenal Chelsea
#   Bash (debug):     docker run -it futfox bash
#   Streamlit (otro): docker run -e FUTFOX_PORT=8080 -p 8080:8080 futfox
#
# ═══════════════════════════════════════════════════════════════════════════

FROM python:3.13-slim

# ── Metadata ──────────────────────────────────────────────────────────────
LABEL org.opencontainers.image.title="FutFox Prediction Engine"
LABEL org.opencontainers.image.description="Motor de predicción de fútbol basado en Poisson + xG"
LABEL org.opencontainers.image.version="2.0"
LABEL org.opencontainers.image.authors="FutFox Team"

# ── Variables configurables ───────────────────────────────────────────────
ENV FUTFOX_PORT=8501
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ── Capa 1: Dependencias del sistema ──────────────────────────────────────
# curl: healthcheck | build-essential: posibles ruedas
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ── Capa 2: Dependencias Python (aprovecha el cache de Docker) ────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Capa 3: Código de la aplicación ───────────────────────────────────────
# Copiar en orden de frecuencia de cambio (menos frecuente primero)
COPY constants.py .
COPY *.py .
COPY scripts/ scripts/
COPY .streamlit/ .streamlit/

# ── Directorios de runtime ────────────────────────────────────────────────
RUN mkdir -p data/cache

# ── Puerto expuesto ───────────────────────────────────────────────────────
EXPOSE 8501

# ── Healthcheck ───────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:${FUTFOX_PORT}/_stcore/health || exit 1

# ═══════════════════════════════════════════════════════════════════════════
# Entrypoint: se puede sobreescribir para CLI (ver docker-compose)
# ═══════════════════════════════════════════════════════════════════════════
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.serverAddress=0.0.0.0"]