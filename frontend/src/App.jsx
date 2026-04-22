import React, { useEffect, useMemo, useRef, useState } from "react";
import { Routes, Route, Navigate, useNavigate, Link } from "react-router-dom";
import { LogOut, Shield, MessageSquare, Loader2, Trash2, Settings, Moon, Sun, Languages, Send, Menu, X } from "lucide-react";
import LoginPage from "./LoginPage";
import AdminPanel from "./AdminPanel";
import translations from "./translations";

const CLAVE_STORAGE_SESION = "chat_session_id";
const CLAVE_STORAGE_TOKEN = "google_auth_token";
const CLAVE_STORAGE_USER = "google_auth_user";
const CLAVE_STORAGE_THEME = "chat_theme";
const CLAVE_STORAGE_LANG = "chat_language";

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

function formatearHora(d = new Date(), lang = "es") {
  return new Intl.DateTimeFormat(lang === "es" ? "es-ES" : "en-US", { hour: "2-digit", minute: "2-digit" }).format(d);
}

// --- Componente Chat Principal ---
const Chat = ({ token, user, onLogout, language, setLanguage, theme, setTheme }) => {
  const [idSesion, setIdSesion] = useState(asegurarIdSesion());
  const [ocupado, setOcupado] = useState(false);
  const [entrada, setEntrada] = useState("");
  const [sesiones, setSesiones] = useState([]);
  const [mensajes, setMensajes] = useState([]);
  const [showSettings, setShowSettings] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);

  const listaRef = useRef(null);
  const navigate = useNavigate();
  const t = translations[language];

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
          { id: m.id + "-q", role: "user", text: m.pregunta, time: formatearHora(new Date(m.creada_en), language) },
          { id: m.id + "-a", role: "bot", text: m.respuesta, fuentes: JSON.parse(m.fuentes || "[]"), time: formatearHora(new Date(m.creada_en), language) }
        ])).flat();
        
        if (msgMapeados.length === 0) {
          setMensajes([{
            id: "welcome", role: "bot", text: t.welcome.replace("{{name}}", user.name.split(' ')[0]), time: formatearHora(new Date(), language)
          }]);
        } else {
          setMensajes(msgMapeados);
        }
      }
    } catch (e) { console.error("Error loading history", e); }
    finally { setOcupado(false); }
  };

  const borrarSesion = async (sid, e) => {
    e.stopPropagation();
    if (!window.confirm(t.confirm_delete)) return;
    try {
      const resp = await fetch(urlEndpoint(`/chat/session/${sid}`), {
        method: 'DELETE',
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (resp.ok) {
        if (sid === idSesion) {
          nuevoChat();
        }
        fetchSesiones();
      }
    } catch (e) { console.error("Error deleting session", e); }
  };

  const nuevoChat = () => {
    const nuevoId = crypto.randomUUID?.() || Math.random().toString(36).substring(2);
    sessionStorage.setItem(CLAVE_STORAGE_SESION, nuevoId);
    setIdSesion(nuevoId);
    setMensajes([{
      id: "welcome-" + Date.now(), role: "bot", text: t.new_conv, time: formatearHora(new Date(), language)
    }]);
  };

  const seleccionarSesion = (sid) => {
    setIdSesion(sid);
    sessionStorage.setItem(CLAVE_STORAGE_SESION, sid);
    cargarHistorial(sid);
    setShowSidebar(false); // Cerrar en móvil al seleccionar
  };

  useEffect(() => {
    if (listaRef.current) {
      listaRef.current.scrollTop = listaRef.current.scrollHeight;
    }
  }, [mensajes]);

  const enviarMensaje = async (texto) => {
    const textoLimpio = texto.trim();
    if (!textoLimpio) return;

    setMensajes((prev) => [...prev, { id: Date.now() + "-u", role: "user", text: textoLimpio, time: formatearHora(new Date(), language) }]);
    setOcupado(true);
    setEntrada("");

    try {
      const resp = await fetch(urlEndpoint("/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ mensaje: textoLimpio, session_id: idSesion, idioma: language }),
      });

      if (!resp.ok) throw new Error("Error en el servidor.");
      
      // Manejo de respuestas JSON (Ej: Bloqueos por toxicidad)
      const contentType = resp.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const data = await resp.json();
        setMensajes((prev) => [...prev, { id: Date.now() + "-b", role: "bot", text: data.respuesta, fuentes: data.fuentes || [], time: formatearHora(new Date(), language) }]);
        fetchSesiones();
        return;
      }

      // Manejo de Streaming (SSE)
      const idBot = Date.now() + "-b";
      setMensajes((prev) => [...prev, { id: idBot, role: "bot", text: "", fuentes: [], time: formatearHora(new Date(), language) }]);
      
      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let botText = "";
      let buffer = "";
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop(); // Keep the incomplete part in the buffer
        
        for (const part of parts) {
            if (part.startsWith("data: ")) {
                try {
                    const data = JSON.parse(part.substring(6));
                    if (data.chunk) {
                        botText += data.chunk;
                        setMensajes(prev => prev.map(m => m.id === idBot ? { ...m, text: botText } : m));
                    }
                    if (data.done) {
                        setMensajes(prev => prev.map(m => m.id === idBot ? { ...m, fuentes: data.fuentes } : m));
                        fetchSesiones();
                    }
                } catch (e) {
                    console.error("Error parsing chunk", e);
                }
            }
        }
      }
    } catch (e) {
      setMensajes((prev) => [...prev, { id: Date.now() + "-e", role: "bot", text: t.error_conn, isError: true, time: formatearHora(new Date(), language) }]);
    } finally { setOcupado(false); }
  };

  const isAdmin = [
    "gsoriano@iescomercio.com", 
    "lentejasricas@gmail.com", 
    "dcastillaa@gmail.com",
    "test@example.com"
  ].includes(user.email);

  return (
    <main className={`chatbot-app ${showSidebar ? "sidebar-open" : ""}`}>
      {showSidebar && <div className="sidebar-overlay" onClick={() => setShowSidebar(false)} />}
      <aside className={`sidebar ${showSidebar ? "active" : ""}`}>
        <div className="sidebar-header">
           <button className="new-chat-btn" onClick={nuevoChat}>
             <MessageSquare size={18} /> {t.new_chat}
           </button>
        </div>
        <div className="history-list">
           <p style={{padding: '0.5rem', fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700}}>{t.recent}</p>
           {sesiones.length === 0 && <p style={{padding: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)'}}>{t.no_sessions}</p>}
           {sesiones.map(s => (
             <div 
               key={s.session_id} 
               className={`history-item ${idSesion === s.session_id ? 'active' : ''}`}
               onClick={() => seleccionarSesion(s.session_id)}
             >
               <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden'}}>
                 <MessageSquare size={14} />
                 <span style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                   {s.titulo || t.session_title}
                 </span>
               </div>
               <button className="delete-btn" onClick={(e) => borrarSesion(s.session_id, e)}>
                 <Trash2 size={14} />
               </button>
             </div>
           ))}
        </div>
        <div className="sidebar-footer">
           <div className="user-info-mini" style={{display: 'flex', alignItems: 'center', gap: '0.8rem'}}>
              <img src={user.picture} alt="" style={{width: 38, height: 38, borderRadius: '50%', border: '2px solid var(--primary)'}} referrerPolicy="no-referrer" />
              <div style={{overflow: 'hidden'}}>
                <p style={{fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis'}}>{user.name}</p>
                <p style={{fontSize: '0.75rem', color: 'var(--text-muted)'}}>{user.email}</p>
              </div>
           </div>
        </div>
      </aside>

      <section className="chatbot-container">
        <header className="chatbot-header">
          <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
            <button className="mobile-toggle" onClick={() => setShowSidebar(!showSidebar)}>
              {showSidebar ? <X size={24} /> : <Menu size={24} />}
            </button>
            <h1 className="chatbot-title">LIA</h1>
          </div>

          <div className="header-actions">
            <button onClick={() => setShowSettings(!showSettings)} className="icon-btn" title={t.settings}>
              <Settings size={20} />
            </button>
            {isAdmin && (
              <button onClick={() => navigate("/admin")} className="icon-btn" title={t.admin_panel}>
                <Shield size={20} />
              </button>
            )}
            <button onClick={onLogout} className="icon-btn" title={t.logout}>
              <LogOut size={20} />
            </button>
          </div>
        </header>

        {showSettings && (
          <div className="settings-menu">
            <div className="settings-group">
              <span className="settings-label">{t.language}</span>
              <div className="toggle-group">
                <button className={`toggle-btn ${language === 'es' ? 'active' : ''}`} onClick={() => setLanguage('es')}>ES</button>
                <button className={`toggle-btn ${language === 'en' ? 'active' : ''}`} onClick={() => setLanguage('en')}>EN</button>
              </div>
            </div>
            <div className="settings-group">
              <span className="settings-label">{t.theme}</span>
              <div className="toggle-group">
                <button className={`toggle-btn ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')}>
                  <Moon size={14} /> {t.dark}
                </button>
                <button className={`toggle-btn ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')}>
                  <Sun size={14} /> {t.light}
                </button>
              </div>
            </div>
            <button className="new-chat-btn" onClick={() => setShowSettings(false)}>{t.back}</button>
          </div>
        )}

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
           {ocupado && <div className="typing-indicator">{t.thinking}</div>}
        </section>

        <form className="chatbot-form" onSubmit={(e) => { e.preventDefault(); enviarMensaje(entrada); }} autoComplete="off">
          <div className="chatbot-inputRow">
             <input
              className="chatbot-input"
              type="text"
              placeholder={t.placeholder}
              required
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              disabled={ocupado}
            />
            <button className="chatbot-send" type="submit" disabled={ocupado}>
              <Send size={20} />
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
  const [theme, setTheme] = useState(localStorage.getItem(CLAVE_STORAGE_THEME) || "dark");
  const [language, setLanguage] = useState(localStorage.getItem(CLAVE_STORAGE_LANG) || "es");

  useEffect(() => {
    if (token && user && (user.name.includes('Ã') || user.name.includes('Â'))) {
      handleLoginSuccess({ credential: token });
    }
  }, [token, user]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);

    localStorage.setItem(CLAVE_STORAGE_THEME, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(CLAVE_STORAGE_LANG, language);
  }, [language]);

  const handleLoginSuccess = (response) => {
    const jwtToken = response.credential;
    setToken(jwtToken);
    localStorage.setItem(CLAVE_STORAGE_TOKEN, jwtToken);
    
    try {
      const base64Url = jwtToken.split(".")[1];
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join("")
      );
      const payload = JSON.parse(jsonPayload);
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
      <Route path="/" element={<Chat 
        token={token} 
        user={user} 
        onLogout={handleLogout} 
        language={language}
        setLanguage={setLanguage}
        theme={theme}
        setTheme={setTheme}
      />} />
      <Route path="/admin" element={<AdminPanel token={token} user={user} />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
