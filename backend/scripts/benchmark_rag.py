"""
==============================================================
  benchmark_rag.py — Medición de rendimiento del Motor RAG
==============================================================
  Tarea 2: Optimización de Latencia y Rendimiento

  Ejecutar desde la raíz del backend:
      python scripts/benchmark_rag.py

  Mide:
    - Latencia de ChromaDB (recuperación de contexto)
    - Número de fragmentos recuperados por consulta
    - Tiempo promedio y peor caso de búsqueda vectorial
==============================================================
"""

import sys
import io
import time
import statistics
from pathlib import Path

# Fix Windows CP1252 encoding issue
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Añadir el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_engine import retrieve_context, _get_collection

# ---------------------------------------------------------------------------
# Preguntas de prueba representativas del Plan Lector
# ---------------------------------------------------------------------------

PREGUNTAS = [
    "¿Quién es el autor del Quijote?",
    "¿De qué trata La Celestina?",
    "¿Cuáles son los libros del Plan Lector?",
    "¿Qué personajes aparecen en el libro?",
    "¿Cuándo fue publicada la obra?",
    "Explícame el argumento principal del libro",
    "¿Qué temas se tratan en la novela?",
]

N_REPETICIONES = 3  # Repeticiones por pregunta para calcular estadísticas


def separador(char="─", n=60):
    print(char * n)


def run_benchmark():
    print()
    separador("═")
    print("  BENCHMARK RAG — Chatbot Plan Lector v2.1")
    separador("═")

    # Verificar que ChromaDB está disponible
    collection = _get_collection()
    if collection is None:
        print("\n❌  ChromaDB no disponible. Verifica que existe el directorio:")
        print(f"    backend/datalake/artifacts/chroma_db/")
        print("\n  Ejecuta primero: python datalake/src/crear_vectores.py")
        sys.exit(1)

    total_chunks = collection.count()
    print(f"\n✅  ChromaDB conectado — {total_chunks} chunks indexados\n")

    # ---------------------------------------------------------------------------
    # Warm-up: primer request siempre es más lento
    # ---------------------------------------------------------------------------
    print("🔥  Warm-up (se descarta)...")
    retrieve_context("prueba de calentamiento", n_results=1)
    print("    Listo.\n")

    separador()
    print(f"  {'Pregunta':<45} {'Avg (ms)':>9} {'Min (ms)':>9} {'Max (ms)':>9} {'Chunks':>7}")
    separador()

    tiempos_globales = []

    for pregunta in PREGUNTAS:
        tiempos = []
        chunks_recuperados = 0

        for _ in range(N_REPETICIONES):
            t0 = time.perf_counter()
            contexto, fuentes = retrieve_context(pregunta)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            tiempos.append(elapsed_ms)
            chunks_recuperados = len(fuentes)

        avg = statistics.mean(tiempos)
        min_ = min(tiempos)
        max_ = max(tiempos)
        tiempos_globales.extend(tiempos)

        etiqueta = pregunta[:44] + ("…" if len(pregunta) > 44 else "")
        print(f"  {etiqueta:<45} {avg:>8.1f}  {min_:>8.1f}  {max_:>8.1f}  {chunks_recuperados:>6}")

    separador()

    # Estadísticas globales
    avg_global = statistics.mean(tiempos_globales)
    p95 = sorted(tiempos_globales)[int(len(tiempos_globales) * 0.95)]
    max_global = max(tiempos_globales)

    print(f"\n  {'ESTADÍSTICAS GLOBALES':}")
    print(f"  ├─ Tiempo promedio : {avg_global:>7.1f} ms")
    print(f"  ├─ Percentil 95    : {p95:>7.1f} ms")
    print(f"  └─ Tiempo máximo   : {max_global:>7.1f} ms")

    # Benchmark por tamaño del corpus
    print(f"\n  CORPUS")
    print(f"  ├─ Total chunks    : {total_chunks:>7,}")
    print(f"  └─ Colección       : convozpropia")

    separador()

    print("\n  🎯 Objetivo: tiempo promedio < 200ms por consulta RAG")
    if avg_global < 200:
        print(f"  ✅  SUPERADO — promedio = {avg_global:.1f}ms\n")
    else:
        print(f"  ⚠️   POR ENCIMA del objetivo — promedio = {avg_global:.1f}ms\n")
        print("  Sugerencias:")
        print("  - Reducir N_RESULTS en rag_engine.py (actualmente 3)")
        print("  - Verificar que chroma_db está en SSD, no en red")
        print("  - Considerar ChromaDB en modo HTTP server para compartir caché\n")


if __name__ == "__main__":
    run_benchmark()
