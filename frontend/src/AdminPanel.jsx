import React, { useState, useEffect } from "react";
import axios from "axios";
import { Table, Search, ShieldCheck, ArrowLeft, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

const AdminPanel = ({ token, user }) => {
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const backendUrl = import.meta.env.VITE_BACKEND_URL || window.location.origin;
      const response = await axios.get(`${backendUrl}/admin/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setQueries(response.data);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching history:", err);
      setError(err.response?.data?.detail || "No tienes permiso para ver esta sección.");
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="admin-loading">
      <Loader2 className="spinner" />
      <p>Cargando historial de consultas...</p>
    </div>
  );

  if (error) return (
    <div className="admin-error">
      <ShieldCheck size={48} color="red" />
      <h2>Acceso Denegado</h2>
      <p>{error}</p>
      <button onClick={() => navigate("/")} className="back-btn">
        <ArrowLeft size={16} /> Volver al Chat
      </button>
    </div>
  );

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div className="admin-title">
          <ShieldCheck className="admin-icon" />
          <h1>Panel de Administración</h1>
        </div>
        <button onClick={() => navigate("/")} className="back-btn-pill">
          <ArrowLeft size={16} /> Volver al Chat
        </button>
      </header>

      <main className="admin-content">
        <div className="stats-cards">
          <div className="stat-card">
            <span className="stat-label">Total Consultas</span>
            <span className="stat-value">{queries.length}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Usuarios Únicos</span>
            <span className="stat-value">
              {new Set(queries.map(q => q.user_email)).size}
            </span>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="queries-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Usuario</th>
                <th>Pregunta</th>
                <th>Respuesta</th>
                <th>Tiempo (ms)</th>
              </tr>
            </thead>
            <tbody>
              {queries.map((q) => (
                <tr key={q.id}>
                  <td className="td-date">{new Date(q.creada_en).toLocaleString()}</td>
                  <td className="td-user">{q.user_email}</td>
                  <td className="td-text">{q.pregunta}</td>
                  <td className="td-text">{q.respuesta}</td>
                  <td className="td-time">{Math.round(q.tiempo_respuesta_ms)}</td>
                </tr>
              ))}
              {queries.length === 0 && (
                <tr>
                  <td colSpan="5" className="td-empty">No hay registros de consultas.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};

export default AdminPanel;
