import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ShieldAlert, Users, MessageSquare, Trash2 } from "lucide-react";

const AdminPanel = ({ token, user }) => {
  const [stats, setStats] = useState({ total_users: 0, total_interactions: 0, total_red_flags: 0 });
  const [redFlags, setRedFlags] = useState([]);
  const navigate = useNavigate();

  // URL del backend (la misma lógica que en App.jsx)
  const apiBase = import.meta.env.VITE_BACKEND_URL || window.location.origin;

  useEffect(() => {
    fetchStats();
    fetchRedFlags();
  }, []);

  const fetchStats = async () => {
    try {
      const resp = await fetch(`${apiBase}/admin/stats`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (resp.ok) setStats(await resp.json());
    } catch (e) { console.error("Error stats", e); }
  };

  const fetchRedFlags = async () => {
    try {
      const resp = await fetch(`${apiBase}/admin/red-flags`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (resp.ok) setRedFlags(await resp.json());
    } catch (e) { console.error("Error flags", e); }
  };

  return (
    <div className="admin-panel-widget" style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: 'var(--bg-main)' }}>
      {/* Header del Panel */}
      <header style={{ padding: '1rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--primary)', color: 'white' }}>
        <button onClick={() => navigate("/")} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
          <ArrowLeft size={20} />
        </button>
        <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Panel de Control</h2>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
        {/* Mini Estadísticas */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '1.5rem' }}>
          <div className="stat-card" style={{ padding: '10px', borderRadius: '8px', background: 'var(--bg-bubble-bot)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--text-muted)', fontSize: '0.7rem' }}><Users size={12}/> USUARIOS</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{stats.total_users}</div>
          </div>
          <div className="stat-card" style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255, 71, 87, 0.1)', border: '1px solid #ff4757' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#ff4757', fontSize: '0.7rem' }}><ShieldAlert size={12}/> ALERTAS</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#ff4757' }}>{stats.total_red_flags}</div>
          </div>
        </div>

        {/* Lista de Alertas (Red Flags) */}
        <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '10px' }}>ALERTAS RECIENTES</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {redFlags.length === 0 && <p style={{ fontSize: '0.8rem', textAlign: 'center', color: 'var(--text-muted)' }}>No hay alertas registradas.</p>}
          {redFlags.map(flag => (
            <div key={flag.id} style={{ padding: '12px', borderRadius: '8px', background: 'var(--bg-bubble-bot)', borderLeft: '4px solid #ff4757', fontSize: '0.85rem' }}>
              <div style={{ fontWeight: 'bold', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{flag.user_email}</div>
              <div style={{ fontStyle: 'italic', color: 'var(--text-main)', marginBottom: '4px' }}>"{flag.content}"</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{new Date(flag.timestamp).toLocaleString()}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;