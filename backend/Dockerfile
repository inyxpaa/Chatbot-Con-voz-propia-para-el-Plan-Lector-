FROM python:3.10-slim

WORKDIR /app

# Dependencias del sistema para chromadb y transformers
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

# torch CPU primero (pesado, en capa separada para aprovechar cache de Docker)
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# Resto de dependencias Python
COPY requirements.txt .
# torch ya instalado, excluirlo del requirements para evitar reinstalación
RUN grep -v "^torch" requirements.txt | pip install --no-cache-dir -r /dev/stdin

# Copiar el backend completo
COPY . .

# Puerto de la API FastAPI
EXPOSE 8000

# Arrancar uvicorn con log-level info para ver traces de RAG y modelo en CloudWatch
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
