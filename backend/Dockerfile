FROM python:3.10-slim

WORKDIR /app

# Build dependencies para chromadb (sqlite3, compiladores C)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python (chromadb ya está en requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el backend al contenedor
COPY . .

# Puerto de la API FastAPI
EXPOSE 8000

# Arrancar con uvicorn
# En producción AWS añade --workers 2 si la instancia tiene >=2 vCPUs
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
