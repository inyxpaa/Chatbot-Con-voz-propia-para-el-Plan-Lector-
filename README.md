# Chatbot "Con voz propia" - Plan Lector

![Estado](https://img.shields.io/badge/Estado-Sprint_2_Completado-success)
![Versión](https://img.shields.io/badge/Versión-1.0.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)
![AWS](https://img.shields.io/badge/AWS-232F3E?logo=amazon-aws&logoColor=white)

> **Acceso a la aplicación en vivo:** [http://ec2-44-218-99-64.compute-1.amazonaws.com/](http://ec2-44-218-99-64.compute-1.amazonaws.com/)

Este proyecto es un asistente conversacional basado en tecnología RAG (Retrieval-Augmented Generation). Facilita la consulta de contenidos del Plan Lector del centro educativo de forma segura. El sistema responde basándose únicamente en la base documental validada.

---

## Arquitectura y Estructura

El proyecto está organizado en las siguientes capas principales:

* **backend/** Contiene la API desarrollada con FastAPI. Gestiona la conexión con la base de datos vectorial ChromaDB y la integración del modelo de lenguaje.
* **frontend/** Contiene la interfaz de usuario desarrollada con React y Vite. Está diseñada para ser embebible en el WordPress institucional.
* **datalake/** Almacena los documentos originales (`raw`), los fragmentos procesados (`processed`) y la base de datos vectorial (`artifacts`).

---

## Ética y Privacidad (RGPD)

El diseño del chatbot sigue principios de privacidad estricta para proteger a los menores:

1. **Minimización:** No almacenamos nombres de usuarios ni datos personales en los registros.
2. **Clasificación del corpus:** Dividimos los documentos en niveles de acceso. Protegemos las producciones del alumnado.
3. **Trazabilidad:** El sistema cita la fuente de la información en sus respuestas. Esto evita desinformación y alucinaciones de la IA.

---

## Equipo de Desarrollo

Proyecto desarrollado por estudiantes del IES Comercio.

* [![LinkedIn](https://img.shields.io/badge/LinkedIn-Alexander_Gavilanez-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/alexander-gavilanez-castro-037a8927b/)
* [![LinkedIn](https://img.shields.io/badge/LinkedIn-Iñigo_Del_Mazo-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/iñigo-del-mazo-monreal-514a7a367)
* [![LinkedIn](https://img.shields.io/badge/LinkedIn-Diego_Castilla-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/diego-castilla-abella-8892a319b/)
* [![LinkedIn](https://img.shields.io/badge/LinkedIn-Alejandro_Bueno-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/alejandro-bueno-ortiz-419054240/)

---

## Instalación en Local

Sigue estos pasos para ejecutar el proyecto en tu propio equipo:

### 1. Clonar el repositorio
```bash
git clone [https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git](https://github.com/inyxpaa/Chatbot-Con-voz-propia-para-el-Plan-Lector-.git)
cd Chatbot-Con-voz-propia-para-el-Plan-Lector-
