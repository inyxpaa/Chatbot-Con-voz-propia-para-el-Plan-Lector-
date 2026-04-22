import React, { useState, useEffect } from "react";
import axios from "axios";
import { ShieldCheck, ArrowLeft, Loader2, Users, MessageCircle, Clock, CheckCircle, AlertOctagon } from "lucide-react";
import { useNavigate } from "react-router-dom";

import translations from "./translations";

const AdminPanel = ({ token, user, language = "es" }) => {
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const t = translations[language];

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const backendUrl = import.meta.env.VITE_BACKEND_URL || window.location.origin;
      const response = await axios.get(`${backendUrl.replace(/\/$/, "")}/admin/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setQueries(response.data);
      setLoading(false);
    } catch (err) {
      setError(err.response?.data?.detail || "Sin permisos.");
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="chatbot-app" style={{justifyContent: 'center', alignItems: 'center'}}>
      <div style={{textAlign: 'center'}}>
        <Loader2 className="spinner" size={48} style={{color: 'var(--primary)', marginBottom: '1rem'}} />
        <p style={{color: 'var(--text-muted)', fontWeight: 600}}>Cargando Observabilidad...</p>
      </div>
    </div>
  );

  return (
    <div className="chatbot-app" style={{flexDirection: 'column', overflowY: 'auto'}}>
      <header className="chatbot-header" style={{position: 'sticky', top: 0, zIndex: 100, width: '100%'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
          <ShieldCheck size={28} style={{color: 'var(--primary)'}} />
          <div>
            <h1 className="chatbot-title" style={{fontSize: '1.2rem'}}>{t.admin_panel}</h1>
            <p style={{fontSize: '0.7rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em'}}>
              {language === 'es' ? `Sistema de Observabilidad · ${queries.length} registros` : `Observability System · ${queries.length} logs`}
            </p>
          </div>
        </div>
        <button onClick={() => navigate("/")} className="icon-btn" style={{display: 'flex', gap: '0.5rem', padding: '0.6rem 1rem'}}>
          <ArrowLeft size={18} /> {t.back}
        </button>
      </header>

      <main className="admin-main" style={{padding: '1.5rem', maxWidth: '1400px', margin: '0 auto', width: '100%'}}>
        <div className="stats-cards" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem'}}>
          <div className="stat-card" style={{background: 'rgba(255,255,255,0.03)', border: '1px solid var(--glass-border)', padding: '1.25rem', borderRadius: '1rem'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
              <span style={{fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase'}}>{language === 'es' ? 'Interacciones' : 'Interactions'}</span>
              <MessageCircle size={18} color="var(--primary)" />
            </div>
            <span style={{fontSize: '1.5rem', fontWeight: 800}}>{queries.length}</span>
          </div>
          
          <div className="stat-card" style={{background: 'rgba(255,255,255,0.03)', border: '1px solid var(--glass-border)', padding: '1.25rem', borderRadius: '1rem'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
              <span style={{fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase'}}>{language === 'es' ? 'Usuarios' : 'Users'}</span>
              <Users size={18} color="var(--primary)" />
            </div>
            <span style={{fontSize: '1.5rem', fontWeight: 800}}>{new Set(queries.map(q => q.user_email)).size}</span>
          </div>

          <div className="stat-card" style={{background: 'rgba(255,255,255,0.03)', border: '1px solid var(--glass-border)', padding: '1.25rem', borderRadius: '1rem'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
              <span style={{fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase'}}>{language === 'es' ? 'Latencia Media' : 'Avg Latency'}</span>
              <Clock size={18} color="#10b981" />
            </div>
            <span style={{fontSize: '1.5rem', fontWeight: 800}}>
              {Math.round(queries.reduce((acc, q) => acc + (q.tiempo_respuesta_ms || 0), 0) / (queries.length || 1))}ms
            </span>
          </div>
        </div>

        <div className="table-wrapper" style={{background: 'rgba(255,255,255,0.02)', border: '1px solid var(--glass-border)', borderRadius: '1.25rem', overflowX: 'auto'}}>
          <table className="queries-table" style={{width: '100%', borderCollapse: 'collapse', textAlign: 'left'}}>
            <thead>
              <tr style={{background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--glass-border)'}}>
                <th style={{padding: '1rem', fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase'}}>Timestamp</th>
                <th style={{padding: '1rem', fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase'}}>Status</th>
                <th style={{padding: '1rem', fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase'}}>User Hash</th>
                <th style={{padding: '1rem', fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase'}}>Query / Response</th>
                <th style={{padding: '1rem', fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase'}}>Time</th>
              </tr>
            </thead>
            <tbody>
              {queries.map((q) => (
                <tr key={q.id} style={{borderBottom: '1px solid var(--glass-border)'}}>
                  <td data-label="Timestamp" style={{padding: '1rem', fontSize: '0.8rem', color: '#94a3b8'}}>
                    {new Date(q.creada_en).toLocaleString(language === 'es' ? 'es-ES' : 'en-US', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'})}
                  </td>
                  <td data-label="Status" style={{padding: '1rem'}}>
                    {q.bloqueada ? (
                      <span style={{color: '#f87171', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.7rem', fontWeight: 700}}>
                        <AlertOctagon size={12} /> BLOCKED
                      </span>
                    ) : (
                      <span style={{color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.7rem', fontWeight: 700}}>
                        <CheckCircle size={12} /> OK
                      </span>
                    )}
                  </td>
                  <td data-label="User Hash" style={{padding: '1rem', fontSize: '0.75rem', color: 'var(--primary)', fontFamily: 'monospace'}}>
                    {q.user_email?.substring(0, 8)}...
                  </td>
                  <td data-label="Query / Response" style={{padding: '1rem'}}>
                    <div style={{fontSize: '0.85rem', color: '#f8fafc', marginBottom: '0.2rem', fontWeight: 600}}>Q: {q.pregunta}</div>
                    <div style={{fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic', maxWidth: '600px'}}>A: {q.respuesta?.substring(0, 100)}{q.respuesta?.length > 100 ? '...' : ''}</div>
                  </td>
                  <td data-label="Time" style={{padding: '1rem', fontSize: '0.8rem', fontWeight: 700, color: (q.tiempo_respuesta_ms > 2000 ? '#fbbf24' : '#f8fafc')}}>
                    {Math.round(q.tiempo_respuesta_ms)}ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>

    </div>
  );
};

export default AdminPanel;
