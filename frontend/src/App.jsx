import React, { useEffect, useMemo, useRef, useState } from "react";
import { Routes, Route, Navigate, useNavigate, Link } from "react-router-dom";
import { LogOut, Shield, MessageSquare, Loader2 } from "lucide-react";
import LoginPage from "./LoginPage";
import AdminPanel from "./AdminPanel";

const CLAVE_STORAGE_SESION = "chat_session_id";
const CLAVE_STORAGE_TOKEN = "google_auth_token";
const CLAVE_STORAGE_USER = "google_auth_user";

// --- Helpers ---
function asegurarIdSesion() {
  let idSesion = sessionStorage.getItem(CLAVE_STORAGE_SESION);
  if (idSesion) return idSesion;
  idSesion = crypto.randomUUID?.() || Math.random().toString(36).substring(2);
  sessionStorage.setItem(CLAVE_STORAGE_SESION, idSesion);
  return idSesion;
}

function urlEndpoint(path = "/chat") {
  const apiBase = import.meta.env.VITE_BACKEND_URL || window.location.origin;
  return `${apiBase.replace(/\/$/, "")}${path}`;
}

function formatearHora(d = new Date()) {
  return new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" }).format(d);
}

// --- Componente Chat Principal ---
const Chat = ({ token, user, onLogout }) => {
  const idSesion = useMemo(() => asegurarIdSesion(), []);
  const [ocupado, setOcupado] = useState(false);
  const [entrada, setEntrada] = useState("");
  const [mensajes, setMensajes] = useState([
    {
      id: "bot-start",
      role: "bot",
      text: `Hola ${user.name.split(' ')[0]}. Dime qué necesitas del Plan Lector.`,
      fuentes: [],
      isError: false,
      time: formatearHora(),
    },
  ]);

  const listaRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (listaRef.current) {
      listaRef.current.scrollTop = listaRef.current.scrollHeight;
    }
  }, [mensajes]);

  const enviarMensaje = async (texto) => {
    const textoLimpio = texto.trim();
    if (!textoLimpio) return;

    setMensajes((prev) => [
      ...prev,
      {
        id: Date.now() + "-u",
        role: "user",
        text: textoLimpio,
        time: formatearHora(),
      },
    ]);

    setOcupado(true);
    setEntrada("");

    try {
      const resp = await fetch(urlEndpoint("/chat"), {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ mensaje: textoLimpio, session_id: idSesion }),
      });

      if (!resp.ok) throw new Error("Error en el servidor. Revisa tu conexión.");

      const data = await resp.json();
      setMensajes((prev) => [
        ...prev,
        {
          id: Date.now() + "-b",
          role: "bot",
          text: data.respuesta,
          fuentes: data.fuentes || [],
          time: formatearHora(),
        },
      ]);
    } catch (e) {
      setMensajes((prev) => [
        ...prev,
        {
          id: Date.now() + "-e",
          role: "bot",
          text: "Hubo un problema. Inténtalo de nuevo.",
          isError: true,
          time: formatearHora(),
        },
      ]);
    } finally {
      setOcupado(false);
    }
  };

  const isAdmin = ["gsoriano@iescomercio.com", "test@example.com"].includes(user.email);

  return (
    <main className="chatbot-app">
      <section className="chatbot-container">
        <header className="chatbot-header">
          <div className="chatbot-header__title">
            <h1 className="chatbot-title">Plan Lector</h1>
            <div className="user-info-mini">
               <img src={user.picture} alt="" className="user-avatar-mini" referrerPolicy="no-referrer" />
               <span>{user.name}</span>
            </div>
          </div>
          <div className="header-actions">
            {isAdmin && (
              <Link to="/admin" className="admin-link-btn" title="Panel Admin" aria-label="Ir al panel de administración">
                <Shield size={20} aria-hidden="true" />
              </Link>
            )}
            <button onClick={onLogout} className="logout-btn" title="Cerrar Sesión" aria-label="Cerrar sesión">
              <LogOut size={20} aria-hidden="true" />
            </button>
          </div>
        </header>

        <section ref={listaRef} className="chatbot-messages" aria-live="polite" aria-label="Conversación con el asistente" role="log">
          {mensajes.map((m) => (
            <div key={m.id} className={`chatbot-message chatbot-message--${m.role}`}>
              <div className="chatbot-bubble">
                <p className={`chatbot-bubble__text${m.isError ? " chatbot-error" : ""}`}>
                  {m.text}
                </p>
                <div className="chatbot-bubble__meta">
                  <span className="chatbot-time">{m.time}</span>
                  {m.role === "bot" && m.fuentes?.length > 0 && (
                    <span className="chatbot-sources">
                      Ref: {m.fuentes.join(", ")}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {ocupado && <div className="typing-indicator">Escuchando...</div>}
        </section>

        <form className="chatbot-form" onSubmit={(e) => { e.preventDefault(); enviarMensaje(entrada); }} autoComplete="off">
          <div className="chatbot-inputRow">
            <input
              className="chatbot-input"
              type="text"
              placeholder="Pregunta algo sobre los libros..."
              required
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              disabled={ocupado}
            />
            <button className="chatbot-send" type="submit" disabled={ocupado} aria-label="Enviar mensaje">
              <MessageSquare size={18} aria-hidden="true" />
            </button>
          </div>
        </form>
      </section>
    </main>
  );
};

// --- App Principal con Rutas ---
export default function App() {
  const [token, setToken] = useState(localStorage.getItem(CLAVE_STORAGE_TOKEN));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem(CLAVE_STORAGE_USER) || "null"));

  const handleLoginSuccess = (response) => {
    const jwtToken = response.credential;
    setToken(jwtToken);
    localStorage.setItem(CLAVE_STORAGE_TOKEN, jwtToken);
    
    // Decodificar el nombre/email del base64 del JWT (simplificado)
    try {
      const payload = JSON.parse(atob(jwtToken.split(".")[1]));
      const userData = {
        email: payload.email,
        name: payload.name,
        picture: payload.picture
      };
      setUser(userData);
      localStorage.setItem(CLAVE_STORAGE_USER, JSON.stringify(userData));
    } catch (e) {
      console.error("Error decoding token", e);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(CLAVE_STORAGE_TOKEN);
    localStorage.removeItem(CLAVE_STORAGE_USER);
  };

  if (!token) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <Routes>
      <Route path="/" element={<Chat token={token} user={user} onLogout={handleLogout} />} />
      <Route path="/admin" element={<AdminPanel token={token} user={user} />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
