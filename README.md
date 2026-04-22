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

Este sistema es un asistente conversacional inteligente basado en la técnica de Fine-Tuning (Ajuste Fino). Su propósito es dinamizar el Plan Lector del centro educativo mediante un modelo de lenguaje que ha sido entrenado específicamente con los contenidos, obras y actividades del instituto. A diferencia de los sistemas genéricos, este modelo posee un conocimiento especializado y adaptado al contexto pedagógico del centro.

---

## Características Principales

* **Modelo Especializado:** El asistente utiliza pesos optimizados mediante entrenamiento supervisado con el corpus del Plan Lector para ofrecer respuestas coherentes y contextualizadas.
* **Privacidad Integrada:** Cumplimiento estricto del RGPD mediante el tratamiento seguro de los datos de entrenamiento y la anonimización de las interacciones.
* **Despliegue de Alto Rendimiento:** Ejecutado sobre infraestructura AWS (instancias m5.large) con contenedores Docker para asegurar una inferencia ágil y estable.
* **Interfaz Embebible:** Diseñada para integrarse perfectamente como un widget dentro de sitios institucionales como WordPress.

---

## Arquitectura Técnica

El proyecto se estructura en capas enfocadas en la optimización del modelo:

* **Dataset y Entrenamiento:** Preparación de datos estructurados para el proceso de Fine-Tuning. Selección, limpieza y formateo de textos para el reentrenamiento de las capas del modelo.
* **Backend (API):** Servidor robusto en FastAPI que gestiona la lógica de inferencia, la comunicación con el motor de IA local y el filtrado de contenido.
* **Frontend (Web):** Interfaz reactiva en React + Vite centrada en la experiencia de usuario y la accesibilidad.
* **DevOps:** Flujo de integración y despliegue continuo (CI/CD) mediante GitHub Actions hacia AWS EC2 para la actualización del modelo y la API.

---

## Ética y Seguridad (RGPD)

El compromiso con la seguridad de la comunidad educativa es un pilar fundamental:

1. **Minimización:** El sistema solo procesa los metadatos necesarios para la analítica, descartando información personal de los usuarios durante la inferencia.
2. **Protección de Menores:** Los datos utilizados para el Fine-Tuning pasan por un proceso de revisión y anonimización para proteger la autoría y privacidad del alumnado.
3. **Integridad de Respuesta:** El ajuste fino permite controlar el tono y el dominio del conocimiento del chatbot, reduciendo el riesgo de contenido inapropiado o fuera de contexto.

---

## Equipo de Desarrollo

Proyecto desarrollado bajo metodologías ágiles por el equipo de ingeniería de software del IES Comercio:

* **Iñigo Del Mazo Monreal** (inyxpaa) - Data & AI Developer. Líder de la capa de datos. Responsable del diseño del dataset de entrenamiento, la limpieza de textos y la configuración de los hiperparámetros para el Fine-Tuning.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/iñigo-del-mazo-monreal-514a7a367)

* **Alexander Gavilanez Castro** (xxcastro) - Junior Full Stack Developer. Especialista en integración. Encargado del desarrollo del backend (FastAPI), configuración del entorno Docker, despliegue del modelo ajustado y flujos CI/CD.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alexander-gavilanez-castro-037a8927b/)

* **Diego Castilla Abella** (castilla204) - Backend & Cloud Operations. Aportación en la arquitectura del servidor, gestión de la infraestructura en la nube (AWS), seguridad y soporte en la persistencia operativa.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/diego-castilla-abella-8892a319b/)

* **Alejandro Bueno Ortiz** (Inaross) - Frontend Web Developer. Responsable de la interfaz de usuario. Diseño y desarrollo de la arquitectura React/Vite, asegurando la accesibilidad web y la integración del chatbot.  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alejandro-bueno-ortiz-419054240/)

---

## Instalación y Despliegue Local

1. **Clonación:** `git clone https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git`
2. **Backend:** Acceder a la carpeta backend, crear entorno virtual, instalar dependencias (pip install -r requirements.txt) y lanzar con uvicorn main:app.
3. **Frontend:** Acceder a la carpeta frontend, instalar paquetes con npm install e iniciar con npm run dev.

---

## Roadmap

- [x] Sprint 1: Arquitectura, selección de datos y preparación de dataset.
- [x] Sprint 2: Proceso de Fine-Tuning, desarrollo de API y despliegue cloud.
- [ ] Sprint 3: Widget para WordPress y optimización de tiempos de inferencia.
- [ ] Sprint 4: Panel de administración, métricas de entrenamiento y validación final.
