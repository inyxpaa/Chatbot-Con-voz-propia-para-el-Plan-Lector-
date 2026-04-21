import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
import App from "./App.jsx";
import "./styles.css";

const GOOGLE_CLIENT_ID = "22015513342-rp17v8jccio7gvnhkdma2vpigerrnu44.apps.googleusercontent.com";

// Función para inicializar el chat en cualquier sitio
const initChatbot = () => {
  // Buscamos si ya existe el contenedor, si no, lo creamos
  let container = document.getElementById("chatbot-plan-lector-root");
  
  if (!container) {
    container = document.createElement("div");
    container.id = "chatbot-plan-lector-root";
    document.body.appendChild(container);
  }

  createRoot(container).render(
    <React.StrictMode>
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        {/* Usamos HashRouter en lugar de BrowserRouter para evitar problemas 
            con las rutas de WordPress */}
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </GoogleOAuthProvider>
    </React.StrictMode>
  );
};

// Se ejecuta automáticamente al cargar el script
if (document.readyState === "complete") {
  initChatbot();
} else {
  window.addEventListener("load", initChatbot);
}