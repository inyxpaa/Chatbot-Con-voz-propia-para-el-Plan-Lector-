# Lia: Chatbot "Con voz propia" - Plan Lector

![Estado](https://img.shields.io/badge/Estado-Sprint_2_Completado-success)
![Versión](https://img.shields.io/badge/Versión-1.0.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)
![AWS](https://img.shields.io/badge/AWS-232F3E?logo=amazon-aws&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

> **Acceso a la plataforma oficial:** [https://buscador-ia.com](https://buscador-ia.com)

**Lia** es un asistente conversacional inteligente cuyo nombre deriva del latín ***legere*** (leer). Basado en la arquitectura **RAG (Retrieval-Augmented Generation)**, su propósito es dinamizar el Plan Lector del centro educativo, permitiendo realizar consultas en lenguaje natural sobre obras, actividades y recomendaciones. La inteligencia de Lia reside en su capacidad para recuperar información de una base documental curada, garantizando respuestas fiables, contextualizadas y sin "alucinaciones".

---

## 🚀 Características Principales

*   **Búsqueda Semántica:** No busca solo por palabras clave, sino por el significado real de las consultas utilizando embeddings vectoriales avanzados.
*   **Privacidad Integrada:** Cumplimiento estricto del RGPD mediante anonimización de datos y niveles de acceso documental granulares.
*   **Despliegue de Alto Rendimiento:** Ejecutado sobre infraestructura AWS con contenedores Docker para asegurar escalabilidad y rapidez.
*   **Interfaz Embebible:** Diseñada para integrarse como un widget dinámico dentro de sitios institucionales como WordPress.

---

## 🛠️ Arquitectura Técnica

El proyecto se divide en capas modulares para facilitar su mantenimiento y evolución:

*   **Datalake y Pipeline IA:** Procesamiento de textos en carpetas `raw` y `processed`. Generación de índices vectoriales en **ChromaDB** para una recuperación inmediata.
*   **Backend (API):** Servidor robusto en **FastAPI** que gestiona la lógica de recuperación, integración con motores locales de IA (**Ollama**) y moderación de contenido.
*   **Frontend (Web):** Interfaz reactiva en **React + Vite** centrada en la experiencia de usuario y la accesibilidad.
*   **DevOps:** Flujo de integración y despliegue continuo (CI/CD) mediante **GitHub Actions** hacia AWS EC2.

---

## ⚖️ Ética y Seguridad (RGPD)

El compromiso con la seguridad de la comunidad educativa es un pilar fundamental en Lia:

1.  **Minimización:** El sistema solo procesa los metadatos necesarios para la analítica, descartando información personal de los usuarios.
2.  **Protección de Menores:** El corpus documental se clasifica para proteger producciones del alumnado, requiriendo validación antes de ser indexado.
3.  **Trazabilidad y Citación:** Cada respuesta incluye referencias documentales, permitiendo al usuario verificar el origen de la información.

---

## 👥 Equipo de Desarrollo

Este proyecto es el fruto del trabajo colaborativo de estudiantes del IES Comercio, donde cada miembro ha liderado un área crítica bajo metodologías ágiles:

*   **Iñigo Del Mazo Monreal** (`inyxpaa`) — **Project Leader & Deployment Leader (DevOps)**
    Responsable de la dirección técnica, gestión del repositorio, flujos de CI/CD en AWS y el diseño inicial del Data Lake y segmentación semántica.
    [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/iñigo-del-mazo-monreal-514a7a367)

*   **Alexander Gavilanez Castro (Alex)** (`xxcastro`) — **Backend Developer**
    Encargado del desarrollo del servidor central con FastAPI, la contenerización con Docker y la integración de modelos de lenguaje locales con Ollama.
    [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alexander-gavilanez-castro-037a8927b/)

*   **Alejandro Bueno Ortiz (Ale)** (`Inaross`) — **Data & AI Developer**
    Especialista en el motor de IA, responsable del entrenamiento de modelos, procesamiento de lenguaje natural y la lógica del motor conversacional RAG.
    [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alejandro-bueno-ortiz-419054240/)

*   **Diego Castilla Abella** (`castilla204`) — **Frontend Developer**
    Diseñador y desarrollador de la interfaz de usuario en React, asegurando una experiencia fluida y la integración del chat como widget embebible.
    [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/diego-castilla-abella-8892a319b/)

---

## ⚙️ Instalación y Despliegue Local

1.  **Clonación:** `git clone https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git`
2.  **Backend:** Acceder a la carpeta `backend`, crear entorno virtual, instalar dependencias (`pip install -r requirements.txt`) y lanzar con `uvicorn main:app`.
3.  **Frontend:** Acceder a la carpeta `frontend`, instalar paquetes con `npm install` e iniciar con `npm run dev`.

---

## 🗺️ Roadmap

- [x] **Sprint 1:** Arquitectura, datalake e ingestión.
- [x] **Sprint 2:** Backend, integración RAG y despliegue cloud.
- [ ] **Sprint 3:** Widget para WordPress y optimización de latencia.
- [ ] **Sprint 4:** Panel de administración, métricas avanzadas y validación final.
