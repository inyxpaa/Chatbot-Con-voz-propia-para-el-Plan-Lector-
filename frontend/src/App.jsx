import React, { useEffect, useMemo, useRef, useState } from "react";

const CLAVE_STORAGE = "chat_session_id";

function asegurarIdSesion() {
  let idSesion = sessionStorage.getItem(CLAVE_STORAGE);
  if (idSesion) return idSesion;

  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    idSesion = window.crypto.randomUUID();
  } else {
    const bytes =
      window.crypto && window.crypto.getRandomValues
        ? window.crypto.getRandomValues(new Uint8Array(16))
        : new Uint8Array(Array.from({ length: 16 }, () => Math.floor(Math.random() * 256)));

    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    idSesion = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  sessionStorage.setItem(CLAVE_STORAGE, idSesion);
  return idSesion;
}

function urlEndpoint() {
  const apiBase = import.meta.env.VITE_BACKEND_URL;
  if (apiBase) {
    return new URL("/chat", apiBase).toString();
  }
  try {
    return new URL("/chat", window.location.origin).toString();
  } catch {
    return "/chat";
  }
}

function formatearHora(d = new Date()) {
  try {
    return new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" }).format(d);
  } catch {
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }
}

export default function App() {
  const idSesion = useMemo(() => asegurarIdSesion(), []);
  const [ocupado, setOcupado] = useState(false);
  const [entrada, setEntrada] = useState("");
  const [mensajes, setMensajes] = useState(() => [
    {
      id: crypto?.randomUUID?.() ?? String(Date.now()),
      role: "bot",
      text: "Hola. Dime qué necesitas del Plan Lector.",
      fuentes: [],
      isError: false,
      time: formatearHora(),
    },
  ]);

  const listaRef = useRef(null);

  useEffect(() => {
    const el = listaRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [mensajes.length]);

  async function enviarMensaje(texto) {
    const textoLimpio = texto.trim();
    if (!textoLimpio) return;

    setMensajes((prev) => [
      ...prev,
      {
        id: (crypto?.randomUUID?.() ?? `${Date.now()}-u`),
        role: "user",
        text: textoLimpio,
        fuentes: null,
        isError: false,
        time: formatearHora(),
      },
    ]);

    setOcupado(true);
    setEntrada("");

    try {
      const resp = await fetch(urlEndpoint(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensaje: textoLimpio, session_id: idSesion }),
      });

      if (!resp.ok) {
        if (resp.status === 400) {
          throw new Error("No puedo procesar ese mensaje. Prueba a reformularlo.");
        }
        throw new Error("Ahora mismo no puedo responder. Inténtalo de nuevo en un momento.");
      }

      const data = await resp.json();
      const respuesta = typeof data?.respuesta === "string" ? data.respuesta : "No he podido generar una respuesta.";
      const fuentes = Array.isArray(data?.fuentes) ? data.fuentes : [];

      setMensajes((prev) => [
        ...prev,
        {
          id: (crypto?.randomUUID?.() ?? `${Date.now()}-b`),
          role: "bot",
          text: respuesta,
          fuentes,
          isError: false,
          time: formatearHora(),
        },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error de red. Revisa tu conexión e inténtalo de nuevo.";
      setMensajes((prev) => [
        ...prev,
        {
          id: (crypto?.randomUUID?.() ?? `${Date.now()}-e`),
          role: "bot",
          text: msg,
          fuentes: [],
          isError: true,
          time: formatearHora(),
        },
      ]);
    } finally {
      setOcupado(false);
    }
  }

  function alEnviar(e) {
    e.preventDefault();
    void enviarMensaje(entrada);
  }

  return (
    <main className="chatbot-app">
      <section className="chatbot-container" aria-label="Chat del Plan Lector">
        <header className="chatbot-header">
          <div className="chatbot-header__title">
            <h1 className="chatbot-title">Plan Lector</h1>
            <p className="chatbot-subtitle">Ayuda y consultas</p>
          </div>
          <div className="chatbot-header__meta">
            {ocupado ? <span className="chatbot-typing">Escribiendo…</span> : null}
          </div>
        </header>

        <section
          ref={listaRef}
          className="chatbot-messages"
          role="log"
          aria-live="polite"
          aria-relevant="additions"
        >
          {mensajes.map((m) => (
            <div key={m.id} className={`chatbot-message chatbot-message--${m.role}`}>
              <div className="chatbot-bubble">
                <p className={`chatbot-bubble__text${m.isError ? " chatbot-error" : ""}`}>
                  {m.text}
                </p>
                <div className="chatbot-bubble__meta">
                  <span className="chatbot-time">{m.time}</span>
                  {m.role === "bot" && Array.isArray(m.fuentes) && m.fuentes.length > 0 ? (
                    <span className="chatbot-sources">
                      <span className="chatbot-sources__label">Referencias:</span> {m.fuentes.join(", ")}
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </section>

        <form className="chatbot-form" onSubmit={alEnviar} autoComplete="off">
          <label className="chatbot-label" htmlFor="chatbot-input">Mensaje</label>
          <div className="chatbot-inputRow">
            <input
              id="chatbot-input"
              className="chatbot-input"
              type="text"
              inputMode="text"
              placeholder="Escribe aquí…"
              maxLength={2000}
              required
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              disabled={ocupado}
            />
            <button className="chatbot-send" type="submit" disabled={ocupado}>
              Enviar
            </button>
          </div>
          <p className="chatbot-hint">Pulsa Enter para enviar.</p>
        </form>
      </section>
    </main>
  );
}

