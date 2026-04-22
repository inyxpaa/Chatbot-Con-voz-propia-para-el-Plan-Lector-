import React, { useState, useEffect } from "react";
import axios from "axios";
import { Table, Search, ShieldCheck, ArrowLeft, Loader2, Users, MessageCircle } from "lucide-react";
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
    <div className="login-container">
      <div className="admin-loading" style={{textAlign: 'center'}}>
        <Loader2 className="spinner" size={48} style={{color: '#6366f1', marginBottom: '1rem'}} />
        <p>Cargando auditoría...</p>
      </div>
    </div>
  );

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
          <ShieldCheck size={32} style={{color: 'var(--primary)'}} />
          <div>
            <h1 style={{fontSize: '1.5rem', fontWeight: 800}}>{t.admin_panel}</h1>
            <p style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>
              {language === 'es' ? `Monitorizando ${queries.length} interacciones` : `Monitoring ${queries.length} interactions`}
            </p>
          </div>
        </div>
        <button onClick={() => navigate("/")} className="new-chat-btn" style={{width: 'auto', padding: '0.5rem 1rem'}}>
          <ArrowLeft size={16} /> {t.back}
        </button>
      </header>

      <main>
        <div className="stats-cards">
          <div className="stat-card">
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
              <span className="stat-label">{language === 'es' ? 'Consultas Totales' : 'Total Queries'}</span>
              <MessageCircle size={16} color="var(--primary)" />
            </div>
            <span className="stat-value">{queries.length}</span>
          </div>
          <div className="stat-card">
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
              <span className="stat-label">{language === 'es' ? 'Usuarios Activos' : 'Active Users'}</span>
              <Users size={16} color="var(--primary)" />
            </div>
            <span className="stat-value">{new Set(queries.map(q => q.user_email)).size}</span>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="queries-table">
            <thead>
              <tr>
                <th>{language === 'es' ? 'Fecha' : 'Date'}</th>
                <th>{language === 'es' ? 'Usuario' : 'User'}</th>
                <th>{language === 'es' ? 'Pregunta' : 'Question'}</th>
                <th>{language === 'es' ? 'Respuesta' : 'Answer'}</th>
                <th>{language === 'es' ? 'Tiempo' : 'Time'}</th>
              </tr>
            </thead>
            <tbody>
              {queries.map((q) => (
                <tr key={q.id}>
                  <td className="td-date">{new Date(q.creada_en).toLocaleDateString(language === 'es' ? 'es-ES' : 'en-US')}</td>
                  <td className="td-user" style={{fontSize: '0.8rem', color: 'var(--primary)'}}>{q.user_email}</td>
                  <td className="td-text" title={q.pregunta}>{q.pregunta}</td>
                  <td className="td-text" title={q.respuesta}>{q.respuesta}</td>
                  <td className="td-time">{Math.round(q.tiempo_respuesta_ms)}ms</td>
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
