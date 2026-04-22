# Chatbot "Con voz propia" - Plan Lector

![Estado](https://img.shields.io/badge/Estado-Sprint_1_Completado-success)
![Versión](https://img.shields.io/badge/Versión-1.0.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

Asistente conversacional inteligente basado en tecnología RAG (Retrieval-Augmented Generation), diseñado para difundir, consultar y dinamizar los contenidos del proyecto lector del IES Comercio.

Este sistema permite a los estudiantes, profesores y familias realizar consultas en lenguaje natural sobre obras, actividades, reseñas y recomendaciones, obteniendo respuestas basadas única y exclusivamente en la base documental curada y validada por el centro.

---

## Arquitectura del Sistema

El proyecto sigue una arquitectura desacoplada en distintas capas funcionales:

### 1. Data Lake (Capa de Datos)
El almacenamiento y procesamiento de la información sigue una estructura estandarizada de Big Data:
* **raw/ (Fuentes Documentales):** Almacenamiento inmutable de textos originales, reseñas, publicaciones de la web del instituto y materiales didácticos.
* **processed/ (Ingesta y Preparación):** Textos limpios, normalizados y divididos en fragmentos (chunks) semánticos mediante scripts de Python.
* **artifacts/ (Indexación Vectorial):** Base de datos vectorial (ChromaDB) que almacena los embeddings generados a partir de los fragmentos, permitiendo búsquedas por similitud matemática.

### 2. Backend (API REST)
Desarrollado con FastAPI, expone los endpoints necesarios para recibir las consultas, conectar con ChromaDB para recuperar el contexto (RAG) y comunicarse con el modelo de lenguaje (LLM) para generar la respuesta final.

### 3. Frontend (Interfaz Web)
Interfaz ligera construida con HTML/CSS/JS (React/Vite), diseñada para ser responsive y fácilmente embebible como widget en el WordPress institucional del centro.

---

## Flujo de Trabajo en Git (Branching Strategy)

Para garantizar la estabilidad del código, el equipo sigue una estrategia de ramas estricta basada en Git Flow:

* **master (Main):** Rama de producción. Está protegida mediante reglas de repositorio. Solo acepta código funcional, testado y revisado a través de Pull Requests.
* **dev (Development):** Rama de integración. Aquí se unen todas las nuevas características antes de pasar a producción. Es el entorno de pruebas principal.
* **feature-branches (ej. datalake):** Ramas de trabajo efímeras creadas a partir de dev para desarrollar funcionalidades específicas (como la creación del datalake, la integración de IA o el diseño web). Una vez completadas, se fusionan (merge) en dev.

---

## Ética, Privacidad y Cumplimiento RGPD

El sistema está diseñado bajo el principio de "Privacidad desde el Diseño", cumpliendo con los requisitos de protección a menores:

1.  **Minimización de Datos:** El sistema no almacena nombres de menores en el corpus ni registra datos personales en los logs de interacción.
2.  **Clasificación de Corpus:** Los documentos se catalogan en 3 niveles de privacidad:
    * Nivel A: Producciones de alumnado (requiere consentimiento y anonimización).
    * Nivel B: Materiales derivados del equipo (reutilizables sin identificación).
    * Nivel C: Textos institucionales o de dominio público (uso libre).
3.  **Trazabilidad:** Las respuestas generadas por el asistente priorizan la citación documental para evitar "alucinaciones" de la IA y respetar el juicio docente.

---

## Instrucciones de Instalación (Entorno Local)

### Prerrequisitos
* Python 3.10+
* Git

### Pasos de despliegue

1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git](https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git)
   cd Chatbot-Con-voz-propia-para-el-Plan-Lector-
