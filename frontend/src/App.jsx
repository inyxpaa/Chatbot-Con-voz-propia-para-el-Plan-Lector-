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
  const [idSesion, setIdSesion] = useState(asegurarIdSesion());
  const [ocupado, setOcupado] = useState(false);
  const [entrada, setEntrada] = useState("");
  const [sesiones, setSesiones] = useState([]);
  const [mensajes, setMensajes] = useState([]);

  const listaRef = useRef(null);
  const navigate = useNavigate();

  // Cargar sesiones al inicio
  useEffect(() => {
    fetchSesiones();
    cargarHistorial(idSesion);
  }, []);

  const fetchSesiones = async () => {
    try {
      const resp = await fetch(urlEndpoint("/chat/sessions"), {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (resp.ok) {
        const data = await resp.json();
        setSesiones(data);
      }
    } catch (e) { console.error("Error fetching sessions", e); }
  };

  const cargarHistorial = async (sid) => {
    if (!sid) return;
    setOcupado(true);
    try {
      const resp = await fetch(urlEndpoint(`/chat/history/${sid}`), {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (resp.ok) {
        const data = await resp.json();
        const msgMapeados = data.map(m => ([
          { id: m.id + "-q", role: "user", text: m.pregunta, time: formatearHora(new Date(m.creada_en)) },
          { id: m.id + "-a", role: "bot", text: m.respuesta, fuentes: JSON.parse(m.fuentes || "[]"), time: formatearHora(new Date(m.creada_en)) }
        ])).flat();
        
        if (msgMapeados.length === 0) {
          setMensajes([{
            id: "welcome", role: "bot", text: `Hola ${user.name.split(' ')[0]}. ¿En qué puedo ayudarte hoy?`, time: formatearHora()
          }]);
        } else {
          setMensajes(msgMapeados);
        }
      }
    } catch (e) { console.error("Error loading history", e); }
    finally { setOcupado(false); }
  };

  const nuevoChat = () => {
    const nuevoId = crypto.randomUUID?.() || Math.random().toString(36).substring(2);
    sessionStorage.setItem(CLAVE_STORAGE_SESION, nuevoId);
    setIdSesion(nuevoId);
    setMensajes([{
      id: "welcome-" + Date.now(), role: "bot", text: "Nueva conversación iniciada. ¿Qué libro te interesa?", time: formatearHora()
    }]);
  };

  const seleccionarSesion = (sid) => {
    setIdSesion(sid);
    sessionStorage.setItem(CLAVE_STORAGE_SESION, sid);
    cargarHistorial(sid);
  };

  useEffect(() => {
    if (listaRef.current) {
      listaRef.current.scrollTop = listaRef.current.scrollHeight;
    }
  }, [mensajes]);

  const enviarMensaje = async (texto) => {
    const textoLimpio = texto.trim();
    if (!textoLimpio) return;

    setMensajes((prev) => [...prev, { id: Date.now() + "-u", role: "user", text: textoLimpio, time: formatearHora() }]);
    setOcupado(true);
    setEntrada("");

    try {
      const resp = await fetch(urlEndpoint("/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ mensaje: textoLimpio, session_id: idSesion }),
      });

      if (!resp.ok) throw new Error("Error en el servidor.");
      const data = await resp.json();
      setMensajes((prev) => [...prev, { id: Date.now() + "-b", role: "bot", text: data.respuesta, fuentes: data.fuentes || [], time: formatearHora() }]);
      fetchSesiones(); // Actualizar lista lateral
    } catch (e) {
      setMensajes((prev) => [...prev, { id: Date.now() + "-e", role: "bot", text: "Error de conexión. Reintenta.", isError: true, time: formatearHora() }]);
    } finally { setOcupado(false); }
  };

  const isAdmin = [
    "gsoriano@iescomercio.com", 
    "lentejasricas@gmail.com", 
    "dcastillaa@gmail.com",
    "test@example.com"
  ].includes(user.email);

  return (
    <main className="chatbot-app">
      <aside className="sidebar">
        <div className="sidebar-header">
           <button className="new-chat-btn" onClick={nuevoChat}>
             <MessageSquare size={18} /> Nuevo Chat
           </button>
        </div>
        <div className="history-list">
           <p style={{padding: '0.5rem', fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700}}>Recientes</p>
           {sesiones.map(s => (
             <div 
               key={s.session_id} 
               className={`history-item ${idSesion === s.session_id ? 'active' : ''}`}
               onClick={() => seleccionarSesion(s.session_id)}
             >
               <MessageSquare size={14} />
               <span style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                 {s.titulo}
               </span>
             </div>
           ))}
        </div>
        <div className="sidebar-footer">
           <div className="user-info-mini" style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
              <img src={user.picture} alt="" style={{width: 32, height: 32, borderRadius: '50%'}} referrerPolicy="no-referrer" />
              <div style={{overflow: 'hidden'}}>
                <p style={{fontSize: '0.8rem', fontWeight: 600, color: 'white', overflow: 'hidden', textOverflow: 'ellipsis'}}>{user.name}</p>
                <p style={{fontSize: '0.7rem', color: '#94a3b8'}}>{user.email}</p>
              </div>
           </div>
        </div>
      </aside>

      <section className="chatbot-container">
        <header className="chatbot-header">
          <h1 className="chatbot-title">Plan Lector AI</h1>
          <div className="header-actions">
            {isAdmin && (
              <button onClick={() => navigate("/admin")} className="icon-btn" title="Panel Admin">
                <Shield size={20} />
              </button>
            )}
            <button onClick={onLogout} className="icon-btn" title="Cerrar Sesión">
              <LogOut size={20} />
            </button>
          </div>
        </header>

        <section ref={listaRef} className="chatbot-messages">
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
                      Info: {m.fuentes[0]}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {ocupado && <div className="typing-indicator" style={{padding: '1rem', color: '#6366f1'}}>Pensando...</div>}
        </section>

        <form className="chatbot-form" onSubmit={(e) => { e.preventDefault(); enviarMensaje(entrada); }} autoComplete="off">
          <div className="chatbot-inputRow">
            <input
              className="chatbot-input"
              type="text"
              placeholder="Pregunta sobre libros del Plan Lector..."
              required
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              disabled={ocupado}
            />
            <button className="chatbot-send" type="submit" disabled={ocupado}>
              <MessageSquare size={18} />
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
    
    try {
      const payload = JSON.parse(atob(jwtToken.split(".")[1]));
      const userData = { email: payload.email, name: payload.name, picture: payload.picture };
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
