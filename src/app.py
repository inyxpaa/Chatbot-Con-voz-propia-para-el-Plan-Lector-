"""
==============================================================
  app.py — Interfaz de Pruebas con Gradio
==============================================================
  Proyecto : Chatbot Plan Lector (RAG)
  Autor    : Equipo de Desarrollo
  Uso      : python src/app.py   (desde la raíz del proyecto)
             Luego abre en el navegador: http://127.0.0.1:7860

  Qué hace este script:
    - Carga el índice FAISS generado por ingesta.py
    - Carga el modelo de embeddings
    - Expone una interfaz web donde puedes escribir una pregunta
      y ver los fragmentos del corpus más relevantes recuperados
==============================================================
"""

import os
import json
import numpy as np
import gradio as gr
from sentence_transformers import SentenceTransformer
import faiss

# ------------------------------------------------------------------
# CONFIGURACIÓN — Debe coincidir con ingesta.py
# ------------------------------------------------------------------
# Rutas relativas a la RAÍZ del proyecto (ejecutar desde ProyectoFinal/)
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR      = os.path.join(BASE_DIR, "data", "db")
INDEX_FILE  = os.path.join(DB_DIR, "index.faiss")
META_FILE   = os.path.join(DB_DIR, "metadata.json")
MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K       = 5   # Número de fragmentos a recuperar por consulta
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# CARGA DE RECURSOS (se ejecuta una sola vez al arrancar la app)
# ------------------------------------------------------------------
def cargar_recursos():
    """Carga el modelo, el índice FAISS y los metadatos en memoria."""
    if not os.path.exists(INDEX_FILE):
        raise FileNotFoundError(
            f"No se encontró el índice en '{INDEX_FILE}'.\n"
            "Ejecuta primero: python src/ingesta.py"
        )

    print(f"Cargando modelo de embeddings: {MODEL_NAME}...")
    modelo = SentenceTransformer(MODEL_NAME)

    print(f"Cargando indice FAISS desde: {INDEX_FILE}")
    index = faiss.read_index(INDEX_FILE)

    print(f"Cargando metadatos desde: {META_FILE}")
    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    total = index.ntotal
    print(f"Recursos cargados. Chunks indexados: {total}")
    return modelo, index, metadata


# Carga global (una vez al iniciar)
try:
    MODELO, INDEX, METADATA = cargar_recursos()
    RECURSOS_OK = True
except FileNotFoundError as e:
    RECURSOS_OK = False
    ERROR_MSG = str(e)


# ------------------------------------------------------------------
# LÓGICA DE BÚSQUEDA
# ------------------------------------------------------------------
def buscar(consulta: str, top_k: int = TOP_K) -> str:
    """
    Convierte la consulta a embedding y recupera los chunks más similares.

    Args:
        consulta : Pregunta o texto libre del usuario.
        top_k    : Cuántos fragmentos retornar.

    Returns:
        Texto formateado con los resultados.
    """
    if not RECURSOS_OK:
        return f"Error: {ERROR_MSG}"

    if not consulta or not consulta.strip():
        return "Por favor, introduzca una pregunta o termino de busqueda."

    # Convertir consulta a embedding normalizado
    query_vec = MODELO.encode(
        [consulta.strip()],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)

    # Buscar los top_k más similares en FAISS
    distancias, indices = INDEX.search(query_vec, top_k)

    # Formatear resultados
    resultados = []
    for rank, (idx, score) in enumerate(zip(indices[0], distancias[0]), start=1):
        if idx == -1:  # FAISS devuelve -1 si no hay suficientes resultados
            continue

        chunk = METADATA[idx]
        bloque = (
            f"**#{rank} — Relevancia: {score:.4f}**\n"
            f"Fuente: `{chunk['source']}`\n"
            f"---\n"
            f"{chunk['text']}\n"
        )
        resultados.append(bloque)

    if not resultados:
        return "No se encontraron fragmentos relevantes para tu consulta."

    cabecera = f"**Consulta:** *{consulta}*\n\n"
    return cabecera + "\n\n".join(resultados)


# ------------------------------------------------------------------
# INTERFAZ GRADIO
# ------------------------------------------------------------------
def construir_interfaz() -> gr.Blocks:
    """Construye y devuelve la interfaz Gradio."""

    with gr.Blocks(
        title="Chatbot Plan Lector — RAG",
        theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
        css="""
            .resultado-box { font-size: 0.95em; line-height: 1.7; }
            footer { display: none !important; }
        """
    ) as demo:

        # --- Cabecera ---
        gr.Markdown(
            """
            # Chatbot Plan Lector — Motor de Busqueda RAG

            Introduzca una pregunta o tema relacionado con el corpus del Plan Lector.
            El sistema recuperara los fragmentos de texto mas relevantes del indice vectorial.
            """
        )

        with gr.Row():
            with gr.Column(scale=3):
                consulta_input = gr.Textbox(
                    label="Pregunta o consulta",
                    placeholder="Ej: ¿De qué trata el libro El Quijote?",
                    lines=2,
                    max_lines=4
                )
            with gr.Column(scale=1):
                top_k_slider = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=TOP_K,
                    step=1,
                    label="Nº de fragmentos a recuperar"
                )

        buscar_btn = gr.Button("Buscar en el corpus", variant="primary", size="lg")

        gr.Markdown("---")

        resultado_output = gr.Markdown(
            value="*Los resultados aparecerán aquí...*",
            elem_classes=["resultado-box"]
        )

        # --- Ejemplos de consulta ---
        gr.Examples(
            examples=[
                ["¿Cuáles son los personajes principales?"],
                ["Resume el argumento del texto"],
                ["¿Qué valores transmite la obra?"],
                ["¿En qué época o lugar se desarrolla la historia?"],
            ],
            inputs=consulta_input,
            label="Ejemplos de consulta"
        )

        # --- Estado del índice ---
        if RECURSOS_OK:
            gr.Markdown(
                f"**Sistema listo.** Chunks indexados en FAISS: `{INDEX.ntotal}` | "
                f"Modelo: `{MODEL_NAME}`",
            )
        else:
            gr.Markdown(f"**Error al cargar recursos:** {ERROR_MSG}")

        # --- Eventos ---
        buscar_btn.click(
            fn=lambda q, k: buscar(q, k),
            inputs=[consulta_input, top_k_slider],
            outputs=resultado_output
        )

        # Permitir buscar también presionando Enter
        consulta_input.submit(
            fn=lambda q, k: buscar(q, k),
            inputs=[consulta_input, top_k_slider],
            outputs=resultado_output
        )

    return demo


# ------------------------------------------------------------------
# PUNTO DE ENTRADA
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  INICIANDO APP -- CHATBOT PLAN LECTOR")
    print("=" * 60)
    demo = construir_interfaz()
    demo.launch(
        server_name="127.0.0.1",  # Accesible desde la red local
        server_port=7860,
        share=False,              # Cambia a True para un link público temporal
        inbrowser=True            # Abre el navegador automáticamente
    )
