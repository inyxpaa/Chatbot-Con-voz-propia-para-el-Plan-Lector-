# Chatbot "Con voz propia" - Plan Lector

Asistente conversacional con tecnología RAG (Retrieval-Augmented Generation) diseñado para el Plan Lector del centro educativo.

## Descripción del Proyecto

El objetivo es difundir, consultar y dinamizar los contenidos del proyecto lector mediante una interfaz web publicable. El sistema permite responder preguntas, recuperar contenido y ofrecer recomendaciones lectoras basándose exclusivamente en una base documental curada.

## Arquitectura

El proyecto se divide en diferentes capas de procesamiento:

* **Fuentes Documentales (raw):** Almacenamiento de textos originales, reseñas y materiales didácticos.
* **Ingesta y Preparación (processed):** Scripts de limpieza, extracción de texto y segmentación (chunking).
* **Indexación Vectorial (artifacts):** Generación de embeddings y almacenamiento en base de datos vectorial ChromaDB.

## Estructura del Repositorio

- `creacion datalake/`: Scripts de preparación de datos y generación de embeddings.
- `backend/`: API desarrollada con FastAPI para gestionar las consultas.
- `frontend/`: Interfaz de usuario desarrollada con React/Vite.

## Tecnologías Utilizadas

* **Lenguaje:** Python, JavaScript
* **Backend:** FastAPI
* **Base de Datos Vectorial:** ChromaDB
* **Embeddings:** Sentence-Transformers
* **Frontend:** React, Vite, HTML, CSS

## Instalación y Ejecución (Entorno Local)

1. Clonar el repositorio.
2. Navegar a la carpeta del proyecto.
3. Crear un entorno virtual.
4. Instalar las dependencias.

```bash
git clone [https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git](https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git)
cd Chatbot-Con-voz-propia-para-el-Plan-Lector-
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
