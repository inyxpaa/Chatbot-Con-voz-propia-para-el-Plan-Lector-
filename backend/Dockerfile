FROM python:3.10-slim

WORKDIR /app

# Only install essential build tools if really needed, but try to avoid them to save space
# We use psycopg2-binary so we don't need libpq-dev/build-essential for it.
# chromadb might need build-essential, but let's see if we can live without it 
# or install it and then remove it in the same layer.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
