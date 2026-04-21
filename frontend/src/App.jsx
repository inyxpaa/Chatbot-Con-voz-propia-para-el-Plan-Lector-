import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import {
  LogOut, Shield, MessageSquare, Send, Moon, Sun,
  Settings, Plus, Trash2, X, Loader2,
} from "lucide-react";
import LoginPage from "./LoginPage";
import AdminPanel from "./AdminPanel";
import translations from "./translations";

// ─── Constantes ────────────────────────────────────────────────────
const STORAGE_TOKEN   = "google_auth_token";
const STORAGE_USER    = "google_auth_user";
const STORAGE_THEME   = "chatbot_theme";
const STORAGE_LANG    = "chatbot_lang";
const SESSION_KEY     = "chat_session_id";

// ─── Helpers ───────────────────────────────────────────────────────
function newSessionId() {
  return crypto.randomUUID?.() || Math.random().toString(36).substring(2);
}

function urlEndpoint(path = "/chat") {
  const base = import.meta.env.VITE_BACKEND_URL || window.location.origin;
  return `${base.replace(/\/$/, "")}${path}`;
}

function hora(d = new Date()) {
  return new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" }).format(d);
}

// ─── Componente Chat ───────────────────────────────────────────────
const Chat = ({ token, user, onLogout, language, setLanguage, theme, setTheme, isWidget = false, onClose }) => {
  const t = translations[language] || translations.es;

  const [sessionId, setSessionId]   = useState(() => sessionStorage.getItem(SESSION_KEY) || newSessionId());
  const [ocupado, setOcupado]       = useState(false);
  const [entrada, setEntrada]       = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [sessions, setSessions]     = useState([]);
  const [mensajes, setMensajes]     = useState([
    {
      id: "bot-start",
      role: "bot",
      text: t.welcome.replace("{{name}}", user.name.split(" ")[0]),
      fuentes: [],
      isError: false,
      time: hora(),
    },
  ]);

  const listaRef = useRef(null);
  const navigate = useNavigate();

  // guarda session id en sessionStorage
  useEffect(() => {
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }, [sessionId]);

  // scroll to bottom
  useEffect(() => {
    if (listaRef.current) listaRef.current.scrollTop = listaRef.current.scrollHeight;
  }, [mensajes]);

  // carga historial de sesiones
  const fetchSessions = useCallback(async () => {
    try {
      const r = await fetch(urlEndpoint("/chat/sessions"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) setSessions(await r.json());
    } catch (_) {}
  }, [token]);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  // nueva sesión
  const handleNewChat = () => {
    const id = newSessionId();
    setSessionId(id);
    setMensajes([{
      id: "bot-new",
      role: "bot",
      text: t.new_conv,
      fuentes: [],
      isError: false,
      time: hora(),
    }]);
    fetchSessions();
  };

  // cargar sesión existente
  const handleLoadSession = async (sid) => {
    try {
      const r = await fetch(urlEndpoint(`/chat/history/${sid}`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return;
      const data = await r.json();
      setSessionId(sid);
      setMensajes(data.map(d => ([
        { id: `${d.id}-u`, role: "user",  text: d.pregunta,  time: hora(new Date(d.creada_en)) },
        { id: `${d.id}-b`, role: "bot",   text: d.respuesta, time: hora(new Date(d.creada_en)) },
      ])).flat());
    } catch (_) {}
  };

  // borrar sesión
  const handleDeleteSession = async (e, sid) => {
    e.stopPropagation();
    if (!window.confirm(t.confirm_delete)) return;
    await fetch(urlEndpoint(`/chat/session/${sid}`), {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchSessions();
    if (sid === sessionId) handleNewChat();
  };

  // enviar mensaje
  const enviarMensaje = async (texto) => {
    const textoLimpio = texto.trim();
    if (!textoLimpio) return;
    setMensajes(prev => [...prev, { id: Date.now() + "-u", role: "user", text: textoLimpio, time: hora() }]);
    setOcupado(true);
    setEntrada("");
    try {
      const resp = await fetch(urlEndpoint("/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ mensaje: textoLimpio, session_id: sessionId, idioma: language }),
      });
      if (!resp.ok) throw new Error();
      const data = await resp.json();
      setMensajes(prev => [...prev, {
        id: Date.now() + "-b", role: "bot",
        text: data.respuesta, fuentes: data.fuentes || [], time: hora(),
      }]);
      fetchSessions();
    } catch {
      setMensajes(prev => [...prev, {
        id: Date.now() + "-e", role: "bot",
        text: t.error_conn, isError: true, time: hora(),
      }]);
    } finally {
      setOcupado(false);
    }
  };

  const isAdmin = user?.email ? true : false; // controlled by backend ADMIN_EMAILS

  return (
    <main className="chatbot-app" data-theme={theme}>
      {/* ── Sidebar de sesiones ─────────────────────────────── */}
      <aside className="sidebar" role="navigation" aria-label={t.user_sessions}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={handleNewChat} aria-label={t.new_chat}>
            <Plus size={16} aria-hidden="true" /> {t.new_chat}
          </button>
        </div>

        <div className="history-list" role="list">
          {sessions.length === 0 && (
            <p style={{ padding: "1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>{t.no_sessions}</p>
          )}
          {sessions.map(s => (
            <div
              key={s.session_id}
              role="listitem"
              className={`history-item ${s.session_id === sessionId ? "active" : ""}`}
              onClick={() => handleLoadSession(s.session_id)}
              tabIndex={0}
              onKeyDown={e => e.key === "Enter" && handleLoadSession(s.session_id)}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {s.titulo}
              </span>
              <button
                className="delete-btn"
                onClick={e => handleDeleteSession(e, s.session_id)}
                aria-label={t.delete_chat}
              >
                <Trash2 size={14} aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-info-mini">
            {user.picture && <img src={user.picture} alt="" className="user-avatar-mini" referrerPolicy="no-referrer" />}
            <div style={{ overflow: "hidden" }}>
              <p style={{ fontSize: "0.85rem", fontWeight: 700, margin: 0, overflow: "hidden", textOverflow: "ellipsis" }}>{user.name}</p>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: 0 }}>{user.email}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Chat principal ──────────────────────────────────── */}
      <section className="chatbot-container">
        <header className="chatbot-header">
          <h1 className="chatbot-title">Plan Lector AI</h1>
          <div className="header-actions">
            <button onClick={() => setShowSettings(!showSettings)} className="icon-btn" title={t.settings} aria-label={t.settings}>
              <Settings size={20} aria-hidden="true" />
            </button>
            <button
              onClick={() => navigate("/admin")}
              className="icon-btn"
              title={t.admin_panel}
              aria-label={t.admin_link}
            >
              <Shield size={20} aria-hidden="true" />
            </button>
            <button onClick={onLogout} className="icon-btn" title={t.logout} aria-label={t.logout}>
              <LogOut size={20} aria-hidden="true" />
            </button>
            {isWidget && onClose && (
              <button onClick={onClose} className="icon-btn" aria-label={t.close_chat}>
                <X size={20} aria-hidden="true" />
              </button>
            )}
          </div>
        </header>

        {/* Menú de ajustes */}
        {showSettings && (
          <div className="settings-menu" role="dialog" aria-label={t.settings}>
            <div className="settings-group">
              <span className="settings-label">{t.language}</span>
              <div className="toggle-group">
                <button className={`toggle-btn ${language === "es" ? "active" : ""}`} onClick={() => setLanguage("es")}>ES</button>
                <button className={`toggle-btn ${language === "en" ? "active" : ""}`} onClick={() => setLanguage("en")}>EN</button>
              </div>
            </div>
            <div className="settings-group">
              <span className="settings-label">{t.theme}</span>
              <div className="toggle-group">
                <button className={`toggle-btn ${theme === "dark"  ? "active" : ""}`} onClick={() => setTheme("dark")}>
                  <Moon size={14} aria-hidden="true" /> {t.dark}
                </button>
                <button className={`toggle-btn ${theme === "light" ? "active" : ""}`} onClick={() => setTheme("light")}>
                  <Sun  size={14} aria-hidden="true" /> {t.light}
                </button>
              </div>
            </div>
            <button className="new-chat-btn" onClick={() => setShowSettings(false)}>{t.back}</button>
          </div>
        )}

        {/* Mensajes */}
        <section
          ref={listaRef}
          className="chatbot-messages"
          aria-live="polite"
          aria-label="Conversación con el asistente"
          role="log"
        >
          {mensajes.map(m => (
            <div key={m.id} className={`chatbot-message chatbot-message--${m.role}`}>
              <div className="chatbot-bubble">
                <p className={`chatbot-bubble__text${m.isError ? " chatbot-error" : ""}`}>{m.text}</p>
                <div className="chatbot-bubble__meta">
                  <span className="chatbot-time">{m.time}</span>
                  {m.role === "bot" && m.fuentes?.length > 0 && (
                    <span className="chatbot-sources">Ref: {m.fuentes[0]}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {ocupado && <div className="typing-indicator" aria-live="polite">{t.thinking}</div>}
        </section>

        {/* Input */}
        <form
          className="chatbot-form"
          onSubmit={e => { e.preventDefault(); enviarMensaje(entrada); }}
          autoComplete="off"
        >
          <div className="chatbot-inputRow">
            <input
              className="chatbot-input"
              type="text"
              placeholder={t.placeholder}
              required
              value={entrada}
              onChange={e => setEntrada(e.target.value)}
              disabled={ocupado}
              aria-label={t.placeholder}
            />
            <button className="chatbot-send" type="submit" disabled={ocupado} aria-label={t.send}>
              <Send size={18} aria-hidden="true" />
            </button>
          </div>
        </form>
      </section>
    </main>
  );
};

// ─── App Principal — Modo widget flotante + standalone ──────────────
export default function App() {
  const [token, setToken]       = useState(localStorage.getItem(STORAGE_TOKEN));
  const [user,  setUser]        = useState(JSON.parse(localStorage.getItem(STORAGE_USER)  || "null"));
  const [theme, setTheme]       = useState(localStorage.getItem(STORAGE_THEME) || "light");
  const [language, setLanguage] = useState(localStorage.getItem(STORAGE_LANG)  || "es");
  const [isOpen, setIsOpen]     = useState(false); // modo widget: ¿está abierto?

  const t = translations[language] || translations.es;

  // persiste preferencias
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_THEME, theme);
  }, [theme]);

  useEffect(() => { localStorage.setItem(STORAGE_LANG, language); }, [language]);

  const handleLoginSuccess = response => {
    const jwt = response.credential;
    setToken(jwt);
    localStorage.setItem(STORAGE_TOKEN, jwt);
    try {
      const payload = JSON.parse(atob(jwt.split(".")[1]));
      const u = { email: payload.email, name: payload.name, picture: payload.picture };
      setUser(u);
      localStorage.setItem(STORAGE_USER, JSON.stringify(u));
    } catch (e) { console.error("Token decode error", e); }
  };

  const handleLogout = () => {
    setToken(null); setUser(null);
    localStorage.removeItem(STORAGE_TOKEN);
    localStorage.removeItem(STORAGE_USER);
    setIsOpen(false);
  };

  // ── Detección de modo: es widget (WordPress iframe) o app standalone
  // Si la URL tiene el parámetro ?widget=true o el documento NO es el top-level,
  // se activa el modo widget flotante automáticamente.
  const isWidgetMode = useMemo(() => {
    try {
      return (
        window.self !== window.top                          // dentro de iframe
        || new URLSearchParams(window.location.search).get("widget") === "true"
      );
    } catch {
      return true; // si falla cross-origin, es iframe
    }
  }, []);

  const chatProps = { token, user, onLogout: handleLogout, language, setLanguage, theme, setTheme };

  // ═══════════════════════════════════════
  //  MODO STANDALONE (app normal en AWS)
  // ═══════════════════════════════════════
  if (!isWidgetMode) {
    if (!token || !user) return <LoginPage onLoginSuccess={handleLoginSuccess} />;
    return (
      <div data-theme={theme}>
        <Routes>
          <Route path="/"      element={<Chat {...chatProps} />} />
          <Route path="/admin" element={<AdminPanel token={token} user={user} />} />
          <Route path="*"      element={<Navigate to="/" />} />
        </Routes>
      </div>
    );
  }

  // ═══════════════════════════════════════
  //  MODO WIDGET FLOTANTE (WordPress)
  // ═══════════════════════════════════════

  // Botón flotante — chat cerrado
  if (!isOpen) {
    return (
      <button
        className="chatbot-launcher-btn"
        onClick={() => setIsOpen(true)}
        aria-label={t.open_chat}
        title={t.open_chat}
      >
        <MessageSquare size={28} aria-hidden="true" />
      </button>
    );
  }

  // Burbuja widget — chat abierto
  return (
    <div className="chatbot-widget-container" data-theme={theme}>
      {/* Login dentro del widget */}
      {!token || !user ? (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      ) : (
        <Routes>
          <Route
            path="/"
            element={
              <Chat
                {...chatProps}
                isWidget={true}
                onClose={() => setIsOpen(false)}
              />
            }
          />
          <Route path="/admin" element={<AdminPanel token={token} user={user} />} />
          <Route path="*"      element={<Navigate to="/" />} />
        </Routes>
      )}
    </div>
  );
}
