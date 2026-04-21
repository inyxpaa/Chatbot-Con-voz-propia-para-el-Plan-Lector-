import React, { useState, useEffect, useCallback } from "react";
import { ShieldCheck, ArrowLeft, Loader2, BarChart2, List, Monitor, Users, Download, RefreshCw, Search, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";

const API = () => import.meta.env.VITE_BACKEND_URL || window.location.origin;

// ── Helpers ────────────────────────────────────────────────────────────────

function fmt(isoStr) {
  if (!isoStr) return "—";
  return new Date(isoStr).toLocaleString("es-ES", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function ms(val) {
  if (val == null) return "—";
  return `${Math.round(val)} ms`;
}

// ── Gráfico de barras SVG puro ─────────────────────────────────────────────

function BarChart({ data }) {
  if (!data || data.length === 0) return null;
  const maxVal = Math.max(...data.map(d => d.total), 1);
  const BAR_W  = 36;
  const GAP    = 10;
  const H      = 100;
  const WIDTH  = data.length * (BAR_W + GAP);

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${WIDTH} ${H + 36}`}
      aria-label="Consultas por día"
      style={{ overflow: "visible" }}
    >
      {data.map((d, i) => {
        const barH = Math.max(4, (d.total / maxVal) * H);
        const x    = i * (BAR_W + GAP);
        const y    = H - barH;
        return (
          <g key={i}>
            <rect
              x={x} y={y} width={BAR_W} height={barH}
              rx="5" fill="#1db954" fillOpacity="0.85"
            />
            {d.total > 0 && (
              <text
                x={x + BAR_W / 2} y={y - 5}
                textAnchor="middle" fontSize="10" fill="#1db954" fontWeight="700"
              >
                {d.total}
              </text>
            )}
            <text
              x={x + BAR_W / 2} y={H + 18}
              textAnchor="middle" fontSize="10" fill="#888"
            >
              {d.etiqueta}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ── Tarjetas KPI ───────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, accent }) {
  return (
    <div className="stat-card" style={accent ? { borderTop: `3px solid ${accent}` } : {}}>
      <span className="stat-label">{label}</span>
      <span className="stat-value" style={accent ? { color: accent } : {}}>{value}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

// ── Badge de estado ────────────────────────────────────────────────────────

function StatusBadge({ ok, yes = "Activo", no = "Error" }) {
  return (
    <span className={`status-badge ${ok ? "status-ok" : "status-err"}`}>
      {ok ? `✓ ${yes}` : `✗ ${no}`}
    </span>
  );
}

// ── Panel principal ────────────────────────────────────────────────────────

const AdminPanel = ({ token, user }) => {
  const navigate = useNavigate();
  const [tab, setTab]       = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError]    = useState(null);

  // Estado por sección
  const [stats, setStats]   = useState(null);
  const [health, setHealth] = useState(null);
  const [users, setUsers]   = useState([]);

  // Historial
  const [history, setHistory]   = useState({ data: [], total: 0, page: 1, pages: 1 });
  const [search, setSearch]     = useState("");
  const [soloBloq, setSoloBloq] = useState(false);
  const [page, setPage]         = useState(1);
  const [exporting, setExporting] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };
  const base    = () => import.meta.env.VITE_BACKEND_URL || window.location.origin;

  // ── Fetch functions ──────────────────────────────────────────────────────

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${base()}/admin/stats`, { headers });
      if (!r.ok) throw new Error(r.status === 403 ? "Sin permisos" : "Error del servidor");
      setStats(await r.json());
      setError(null);
    } catch (e) { setError(e.message); }
  }, [token]);

  const fetchHealth = useCallback(async () => {
    try {
      const r = await fetch(`${base()}/admin/health`, { headers });
      if (!r.ok) throw new Error("Error del servidor");
      setHealth(await r.json());
    } catch (e) { setError(e.message); }
  }, [token]);

  const fetchUsers = useCallback(async () => {
    try {
      const r = await fetch(`${base()}/admin/users`, { headers });
      if (!r.ok) throw new Error("Error del servidor");
      setUsers(await r.json());
    } catch (e) { setError(e.message); }
  }, [token]);

  const fetchHistory = useCallback(async (pg = 1, q = search, bloq = soloBloq) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: pg, limit: 50, search: q, solo_bloqueadas: bloq,
      });
      const r = await fetch(`${base()}/admin/history?${params}`, { headers });
      if (!r.ok) throw new Error("Error del servidor");
      const data = await r.json();
      setHistory(data);
      setPage(pg);
      setError(null);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [token, search, soloBloq]);

  // ── Carga inicial por tab ────────────────────────────────────────────────

  useEffect(() => {
    if (tab === "dashboard") fetchStats();
    if (tab === "historial") fetchHistory(1);
    if (tab === "sistema") fetchHealth();
    if (tab === "usuarios") fetchUsers();
  }, [tab]);

  // Auto-refresco sistema cada 30s
  useEffect(() => {
    if (tab !== "sistema") return;
    const id = setInterval(fetchHealth, 30000);
    return () => clearInterval(id);
  }, [tab, fetchHealth]);

  // ── Export CSV ───────────────────────────────────────────────────────────

  const handleExport = async () => {
    setExporting(true);
    try {
      const r = await fetch(`${base()}/admin/export`, { headers });
      const blob = await r.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href = url;
      a.download = "historial_chatbot.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert("Error al exportar: " + e.message); }
    finally { setExporting(false); }
  };

  // ── Error global ─────────────────────────────────────────────────────────

  if (error && !stats && !health && users.length === 0 && history.data.length === 0) {
    return (
      <div className="admin-error">
        <AlertTriangle size={48} color="#e53e3e" />
        <h2>Error de acceso</h2>
        <p>{error}</p>
        <button onClick={() => navigate("/")} className="back-btn-pill">
          <ArrowLeft size={16} /> Volver al Chat
        </button>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const TABS = [
    { id: "dashboard", label: "Dashboard",   icon: <BarChart2 size={16} /> },
    { id: "historial", label: "Historial",   icon: <List      size={16} /> },
    { id: "sistema",   label: "Sistema",     icon: <Monitor   size={16} /> },
    { id: "usuarios",  label: "Usuarios",    icon: <Users     size={16} /> },
  ];

  return (
    <div className="admin-container">
      {/* Header */}
      <header className="admin-header">
        <div className="admin-title">
          <ShieldCheck className="admin-icon" />
          <h1>Panel de Administración</h1>
        </div>
        <button onClick={() => navigate("/")} className="back-btn-pill">
          <ArrowLeft size={16} /> Volver al Chat
        </button>
      </header>

      {/* Tabs */}
      <nav className="admin-tabs" role="tablist">
        {TABS.map(t => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={`admin-tab ${tab === t.id ? "admin-tab--active" : ""}`}
            onClick={() => setTab(t.id)}
            id={`tab-${t.id}`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </nav>

      <main className="admin-content" role="tabpanel" aria-labelledby={`tab-${tab}`}>

        {/* ─── DASHBOARD ─────────────────────────────────────────────── */}
        {tab === "dashboard" && (
          <div className="tab-pane">
            {!stats ? (
              <div className="admin-loading"><Loader2 className="spinner" size={32} /><p>Cargando métricas...</p></div>
            ) : (
              <>
                <div className="stats-cards">
                  <KpiCard label="Total Consultas"   value={stats.total_consultas}    />
                  <KpiCard label="Usuarios Únicos"   value={stats.usuarios_unicos}    />
                  <KpiCard label="Bloqueadas"         value={stats.consultas_bloqueadas} accent="#e53e3e"
                    sub={`${stats.tasa_bloqueo_pct}% del total`} />
                  <KpiCard label="Latencia media"    value={ms(stats.latencia_media_ms)} accent="#1db954" />
                </div>

                <div className="chart-card">
                  <h2 className="section-title">Consultas — últimos 7 días</h2>
                  <div className="chart-wrap">
                    <BarChart data={stats.consultas_por_dia} />
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* ─── HISTORIAL ─────────────────────────────────────────────── */}
        {tab === "historial" && (
          <div className="tab-pane">
            <div className="hist-toolbar">
              <div className="search-wrap">
                <Search size={15} className="search-icon-inner" />
                <input
                  id="historial-search"
                  className="hist-search"
                  placeholder="Buscar en preguntas y respuestas…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && fetchHistory(1, search, soloBloq)}
                />
                <button className="btn-sm" onClick={() => fetchHistory(1, search, soloBloq)}>Buscar</button>
              </div>
              <label className="toggle-label">
                <input
                  type="checkbox"
                  id="filtro-bloqueadas"
                  checked={soloBloq}
                  onChange={e => { setSoloBloq(e.target.checked); fetchHistory(1, search, e.target.checked); }}
                />
                Solo bloqueadas
              </label>
              <button className="btn-sm btn-export" id="btn-export-csv" onClick={handleExport} disabled={exporting}>
                <Download size={14} /> {exporting ? "Exportando…" : "Exportar CSV"}
              </button>
            </div>

            {loading ? (
              <div className="admin-loading" style={{ minHeight: 200 }}>
                <Loader2 className="spinner" size={28} />
              </div>
            ) : (
              <>
                <p className="hist-count">{history.total} registros · página {history.page} de {history.pages}</p>
                <div className="table-wrapper">
                  <table className="queries-table">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Usuario</th>
                        <th>Pregunta</th>
                        <th>Respuesta</th>
                        <th>Estado</th>
                        <th>Tiempo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.data.length === 0 && (
                        <tr><td colSpan="6" className="td-empty">No hay registros.</td></tr>
                      )}
                      {history.data.map(q => (
                        <tr key={q.id} className={q.bloqueada ? "row-blocked" : ""}>
                          <td className="td-date">{fmt(q.creada_en)}</td>
                          <td className="td-user">
                            <code className="hash-code">{q.user_email?.slice(0, 10)}…</code>
                          </td>
                          <td className="td-text">{q.pregunta}</td>
                          <td className="td-text">{q.respuesta}</td>
                          <td>
                            {q.bloqueada
                              ? <span className="badge-blocked">Bloqueada</span>
                              : <span className="badge-ok">OK</span>
                            }
                          </td>
                          <td className="td-time">{ms(q.tiempo_respuesta_ms)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Paginación */}
                {history.pages > 1 && (
                  <div className="pagination">
                    <button
                      className="page-btn" id="btn-prev-page"
                      disabled={page <= 1}
                      onClick={() => fetchHistory(page - 1)}
                    >← Anterior</button>
                    <span className="page-info">{page} / {history.pages}</span>
                    <button
                      className="page-btn" id="btn-next-page"
                      disabled={page >= history.pages}
                      onClick={() => fetchHistory(page + 1)}
                    >Siguiente →</button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ─── SISTEMA ───────────────────────────────────────────────── */}
        {tab === "sistema" && (
          <div className="tab-pane">
            <div className="section-header">
              <h2 className="section-title">Estado del sistema</h2>
              <button className="btn-sm" id="btn-refresh-health" onClick={fetchHealth}>
                <RefreshCw size={14} /> Refrescar
              </button>
            </div>

            {!health ? (
              <div className="admin-loading" style={{ minHeight: 200 }}>
                <Loader2 className="spinner" size={28} />
              </div>
            ) : (
              <div className="health-grid">
                {/* Modelo */}
                <div className="health-card">
                  <h3 className="health-title">🤖 Modelo</h3>
                  <div className="health-row">
                    <span>Estado</span>
                    <StatusBadge ok={health.modelo.cargado} yes="Cargado en memoria" no="No disponible" />
                  </div>
                  <div className="health-row">
                    <span>Proveedor</span>
                    <code>{health.modelo.provider}</code>
                  </div>
                  <div className="health-row">
                    <span>Ruta / URL</span>
                    <code className="path-code">{health.modelo.ruta}</code>
                  </div>
                </div>

                {/* ChromaDB */}
                <div className="health-card">
                  <h3 className="health-title">🗄 ChromaDB</h3>
                  <div className="health-row">
                    <span>Estado</span>
                    <StatusBadge ok={health.chromadb.ok} yes="Conectado" no="Sin conexión" />
                  </div>
                  <div className="health-row">
                    <span>Colección</span>
                    <code>{health.chromadb.coleccion}</code>
                  </div>
                  <div className="health-row">
                    <span>Chunks indexados</span>
                    <strong>{health.chromadb.chunks.toLocaleString("es-ES")}</strong>
                  </div>
                  <div className="health-row">
                    <span>Ruta</span>
                    <code className="path-code">{health.chromadb.ruta}</code>
                  </div>
                </div>

                {/* PostgreSQL */}
                <div className="health-card">
                  <h3 className="health-title">🐘 PostgreSQL</h3>
                  <div className="health-row">
                    <span>Conexión</span>
                    <StatusBadge ok={health.postgres.ok} yes="Activa" no="Error" />
                  </div>
                  <div className="health-row">
                    <span>Total registros</span>
                    <strong>{health.postgres.total_registros.toLocaleString("es-ES")}</strong>
                  </div>
                </div>
              </div>
            )}
            <p className="refresh-note">Se refresca automáticamente cada 30 segundos.</p>
          </div>
        )}

        {/* ─── USUARIOS ──────────────────────────────────────────────── */}
        {tab === "usuarios" && (
          <div className="tab-pane">
            <h2 className="section-title">Usuarios únicos</h2>
            <div className="table-wrapper">
              <table className="queries-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Hash usuario (SHA-256)</th>
                    <th>Consultas</th>
                    <th>Último acceso</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 && (
                    <tr><td colSpan="4" className="td-empty">No hay datos de usuarios.</td></tr>
                  )}
                  {users.map((u, i) => (
                    <tr key={u.user_email}>
                      <td className="td-date">{i + 1}</td>
                      <td><code className="hash-code">{u.user_email}</code></td>
                      <td><strong>{u.total_consultas}</strong></td>
                      <td className="td-date">{fmt(u.ultimo_acceso)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="refresh-note">
              Los emails se muestran como hash SHA-256 (anonimización Tarea 1).
            </p>
          </div>
        )}

      </main>
    </div>
  );
};

export default AdminPanel;
