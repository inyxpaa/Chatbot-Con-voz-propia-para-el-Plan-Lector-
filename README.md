# Chatbot "Con voz propia" - Plan Lector

![Estado](https://img.shields.io/badge/Estado-Sprint_2_Completado-success)
![Versión](https://img.shields.io/badge/Versión-1.0.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)
![AWS](https://img.shields.io/badge/AWS-232F3E?logo=amazon-aws&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

> **Acceso a la plataforma oficial:** [https://buscador-ia.com](https://buscador-ia.com)

Este sistema es un asistente conversacional inteligente basado en la arquitectura **RAG (Retrieval-Augmented Generation)**. Su propósito es dinamizar el Plan Lector del centro educativo, permitiendo realizar consultas en lenguaje natural sobre obras, actividades y recomendaciones. La inteligencia del sistema reside en su capacidad para recuperar información de una base documental curada, garantizando respuestas fiables y sin "alucinaciones".

---

## Características Principales

* **Búsqueda Semántica:** No busca solo por palabras clave, sino por el significado real de las consultas utilizando embeddings vectoriales.
* **Privacidad Integrada:** Cumplimiento estricto del RGPD mediante anonimización de datos y niveles de acceso documental.
* **Despliegue de Alto Rendimiento:** Ejecutado sobre infraestructura AWS (instancias m5.large) con contenedores Docker para asegurar escalabilidad y rapidez.
* **Interfaz Embebible:** Diseñada para integrarse perfectamente como un widget dentro de sitios institucionales como WordPress.

---

## Arquitectura Técnica

El proyecto se divide en capas modulares para facilitar su mantenimiento:

* **Datalake y Pipeline IA:** Procesamiento de textos en carpetas `raw` y `processed`. Generación de índices vectoriales en **ChromaDB** para una recuperación inmediata.
* **Backend (API):** Servidor robusto en **FastAPI** que gestiona la lógica de recuperación, integración con motores locales de IA (**Ollama**) y moderación de contenido.
* **Frontend (Web):** Interfaz reactiva en **React + Vite** centrada en la experiencia de usuario y la accesibilidad.
* **DevOps:** Flujo de integración y despliegue continuo (CI/CD) mediante **GitHub Actions** hacia AWS EC2.

---

## Ética y Seguridad (RGPD)

El compromiso con la seguridad de la comunidad educativa es un pilar fundamental:

1.  **Minimización:** El sistema solo procesa los metadatos necesarios para la analítica, descartando información personal de los usuarios.
2.  **Protección de Menores:** El corpus documental se clasifica para proteger producciones del alumnado, requiriendo validación antes de ser indexado.
3.  **Trazabilidad y Citación:** Cada respuesta incluye referencias documentales, permitiendo al usuario verificar el origen de la información.

---

## Equipo de Desarrollo

Proyecto desarrollado bajo metodologías ágiles por el equipo de ingeniería de software del IES Comercio:

* **Iñigo Del Mazo Monreal** (`inyxpaa`) - *Data & AI Developer* Líder de la capa de datos. Responsable del diseño del Data Lake, la extracción documental, limpieza de textos, chunking semántico y la indexación vectorial persistente mediante ChromaDB.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/iñigo-del-mazo-monreal-514a7a367)

* **Alexander Gavilanez Castro** (`xxcastro`) - *Junior Full Stack Developer* Especialista en integración. Encargado del desarrollo del backend (FastAPI), configuración del entorno Docker, despliegue de modelos de lenguaje local (Ollama) y flujos CI/CD.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alexander-gavilanez-castro-037a8927b/)

* **Diego Castilla Abella** (`castilla204`) - *Backend & Cloud Operations* Aportación en la arquitectura del servidor, gestión de la infraestructura en la nube (AWS), seguridad, soporte en el backend y persistencia operativa.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/diego-castilla-abella-8892a319b/)

* **Alejandro Bueno Ortiz** (`Inaross`) - *Frontend Web Developer* Responsable de la interfaz de usuario. Diseño y desarrollo de la arquitectura React/Vite, asegurando la accesibilidad web y la correcta integración del chatbot como widget.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alejandro-bueno-ortiz-419054240/)

---

## Instalación y Despliegue Local

1.  **Clonación:** `git clone https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git`
2.  **Backend:** Acceder a la carpeta `backend`, crear entorno virtual, instalar dependencias (`pip install -r requirements.txt`) y lanzar con `uvicorn main:app`.
3.  **Frontend:** Acceder a la carpeta `frontend`, instalar paquetes con `npm install` e iniciar con `npm run dev`.

---

## Roadmap

- [x] **Sprint 1:** Arquitectura, datalake e ingestión.
- [x] **Sprint 2:** Backend, integración RAG y despliegue cloud.
- [ ] **Sprint 3:** Widget para WordPress y optimización de latencia.
- [ ] **Sprint 4:** Panel de administración, métricas avanzadas y validación final.
