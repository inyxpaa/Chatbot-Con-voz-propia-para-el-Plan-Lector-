FROM python:3.10-slim

WORKDIR /app

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Instalar torch CPU primero (Capa pesada, rara vez cambia)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Copiar e instalar requirements (Capa media, solo cambia si añades librerías)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiar el código (Capa ligera, cambia siempre pero es instantánea)
COPY . .

EXPOSE 8000

# Usar optimizaciones de uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
