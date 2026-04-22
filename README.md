![Versión](https://img.shields.io/badge/Versión-1.0.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

Asistente conversacional inteligente basado en tecnología RAG (Retrieval-Augmented Generation), diseñado para difundir, consultar y dinamizar los contenidos del proyecto lector del IES Comercio.
Acceso a la aplicación: http://ec2-44-218-99-64.compute-1.amazonaws.com/

Este sistema permite a los estudiantes, profesores y familias realizar consultas en lenguaje natural sobre obras, actividades, reseñas y recomendaciones, obteniendo respuestas basadas única y exclusivamente en la base documental curada y validada por el centro.
Este proyecto es un asistente conversacional basado en tecnología RAG (Retrieval-Augmented Generation). Su función es facilitar la consulta de contenidos del Plan Lector del centro educativo de forma segura y fiable. El sistema responde basándose únicamente en la base documental validada.

---

## Arquitectura del Sistema
## Estructura del Repositorio

El proyecto sigue una arquitectura desacoplada en distintas capas funcionales:
El proyecto está organizado en las siguientes carpetas principales:

### 1. Data Lake (Capa de Datos)
El almacenamiento y procesamiento de la información sigue una estructura estandarizada de Big Data:
* **raw/ (Fuentes Documentales):** Almacenamiento inmutable de textos originales, reseñas, publicaciones de la web del instituto y materiales didácticos.
* **processed/ (Ingesta y Preparación):** Textos limpios, normalizados y divididos en fragmentos (chunks) semánticos mediante scripts de Python.
* **artifacts/ (Indexación Vectorial):** Base de datos vectorial (ChromaDB) que almacena los embeddings generados a partir de los fragmentos, permitiendo búsquedas por similitud matemática.

### 2. Backend (API REST)
Desarrollado con FastAPI, expone los endpoints necesarios para recibir las consultas, conectar con ChromaDB para recuperar el contexto (RAG) y comunicarse con el modelo de lenguaje (LLM) para generar la respuesta final.

### 3. Frontend (Interfaz Web)
Interfaz ligera construida con HTML/CSS/JS (React/Vite), diseñada para ser responsive y fácilmente embebible como widget en el WordPress institucional del centro.
* **backend/:** Contiene la lógica del servidor desarrollada con FastAPI, la conexión con la base de datos vectorial ChromaDB y la integración del modelo de lenguaje.
* **frontend/:** Contiene la interfaz de usuario desarrollada con React y Vite, diseñada para ser embebible en el WordPress institucional.

---

## Flujo de Trabajo en Git (Branching Strategy)
## Tecnologías Utilizadas

Para garantizar la estabilidad del código, el equipo sigue una estrategia de ramas estricta basada en Git Flow:

* **master (Main):** Rama de producción. Está protegida mediante reglas de repositorio. Solo acepta código funcional, testado y revisado a través de Pull Requests.
* **dev (Development):** Rama de integración. Aquí se unen todas las nuevas características antes de pasar a producción. Es el entorno de pruebas principal.
* **feature-branches (ej. datalake):** Ramas de trabajo efímeras creadas a partir de dev para desarrollar funcionalidades específicas (como la creación del datalake, la integración de IA o el diseño web). Una vez completadas, se fusionan (merge) en dev.
* **Backend:** Python, FastAPI.
* **Base de datos vectorial:** ChromaDB.
* **Procesamiento de texto:** Sentence-Transformers.
* **Frontend:** JavaScript, React, Vite, Tailwind CSS.
* **Infraestructura:** AWS (EC2).

---

## Ética, Privacidad y Cumplimiento RGPD
## Ética y Privacidad (RGPD)

El sistema está diseñado bajo el principio de "Privacidad desde el Diseño", cumpliendo con los requisitos de protección a menores:
El diseño del chatbot sigue principios de privacidad estricta:

1.  **Minimización de Datos:** El sistema no almacena nombres de menores en el corpus ni registra datos personales en los logs de interacción.
2.  **Clasificación de Corpus:** Los documentos se catalogan en 3 niveles de privacidad:
    * Nivel A: Producciones de alumnado (requiere consentimiento y anonimización).
    * Nivel B: Materiales derivados del equipo (reutilizables sin identificación).
    * Nivel C: Textos institucionales o de dominio público (uso libre).
3.  **Trazabilidad:** Las respuestas generadas por el asistente priorizan la citación documental para evitar "alucinaciones" de la IA y respetar el juicio docente.
1. **Minimización:** No se almacenan nombres de usuarios ni datos personales en los registros de conversación.
2. **Clasificación del corpus:** Los documentos se dividen en niveles de acceso para proteger producciones del alumnado.
3. **Trazabilidad:** El sistema intenta citar la fuente de la información en cada respuesta para evitar errores y desinformación.

---

## Instrucciones de Instalación (Entorno Local)

### Prerrequisitos
* Python 3.10+
* Git
## Instalación en local

### Pasos de despliegue
Si deseas ejecutar el proyecto en tu propio equipo, sigue estos pasos:

1. Clonar el repositorio:
   ```bash
