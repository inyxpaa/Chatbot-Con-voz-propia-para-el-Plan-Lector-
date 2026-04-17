# Chatbot "Con voz propia" - Plan Lector

![Estado](https://img.shields.io/badge/Estado-Sprint_1_Completado-success)
![Versión](https://img.shields.io/badge/Versión-1.0.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

Acceso a la aplicación: http://ec2-44-218-99-64.compute-1.amazonaws.com/

Este proyecto es un asistente conversacional basado en tecnología RAG (Retrieval-Augmented Generation). Su función es facilitar la consulta de contenidos del Plan Lector del centro educativo de forma segura y fiable. El sistema responde basándose únicamente en la base documental validada.

---

## Estructura del Repositorio

El proyecto está organizado en las siguientes carpetas principales:

* **backend/:** Contiene la lógica del servidor desarrollada con FastAPI, la conexión con la base de datos vectorial ChromaDB y la integración del modelo de lenguaje.
* **frontend/:** Contiene la interfaz de usuario desarrollada con React y Vite, diseñada para ser embebible en el WordPress institucional.

---

## Tecnologías Utilizadas

* **Backend:** Python, FastAPI.
* **Base de datos vectorial:** ChromaDB.
* **Procesamiento de texto:** Sentence-Transformers.
* **Frontend:** JavaScript, React, Vite, Tailwind CSS.
* **Infraestructura:** AWS (EC2).

---

## Ética y Privacidad (RGPD)

El diseño del chatbot sigue principios de privacidad estricta:

1. **Minimización:** No se almacenan nombres de usuarios ni datos personales en los registros de conversación.
2. **Clasificación del corpus:** Los documentos se dividen en niveles de acceso para proteger producciones del alumnado.
3. **Trazabilidad:** El sistema intenta citar la fuente de la información en cada respuesta para evitar errores y desinformación.

---

## Instalación en local

Si deseas ejecutar el proyecto en tu propio equipo, sigue estos pasos:

1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git](https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git)
   cd Chatbot-Con-voz-propia-para-el-Plan-Lector-
