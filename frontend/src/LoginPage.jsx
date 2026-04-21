import React from "react";
import { GoogleLogin } from "@react-oauth/google";
import { BookOpen, ShieldCheck } from "lucide-react";

const LoginPage = ({ onLoginSuccess }) => {
  return (
    <div className="login-widget-container" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      padding: '2rem',
      textAlign: 'center',
      background: 'var(--bg-main)',
      color: 'var(--text-main)'
    }}>
      {/* Icono Principal / Logo */}
      <div style={{
        backgroundColor: 'var(--primary)',
        padding: '15px',
        borderRadius: '50%',
        marginBottom: '1rem',
        boxShadow: '0 4px 10px rgba(0,0,0,0.2)'
      }}>
        <BookOpen size={40} color="white" />
      </div>

      <h2 style={{ fontSize: '1.4rem', marginBottom: '0.5rem', fontWeight: 'bold' }}>
        Plan Lector AI
      </h2>
      
      <p style={{ 
        fontSize: '0.9rem', 
        color: 'var(--text-muted)', 
        marginBottom: '2rem',
        lineHeight: '1.4' 
      }}>
        Inicia sesión con tu cuenta del instituto para resolver tus dudas.
      </p>

      {/* Contenedor del Botón de Google */}
      <div style={{ 
        width: '100%', 
        display: 'flex', 
        justifyContent: 'center',
        padding: '10px'
      }}>
        <GoogleLogin 
          onSuccess={onLoginSuccess} 
          onError={() => console.log("Login Failed")}
          theme="filled_blue"
          shape="pill"
          size="large"
          width="250px"
        />
      </div>

      {/* Pie de página de seguridad */}
      <div style={{ 
        marginTop: 'auto', 
        display: 'flex', 
        alignItems: 'center', 
        gap: '5px', 
        fontSize: '0.75rem', 
        color: 'var(--text-muted)' 
      }}>
        <ShieldCheck size={14} />
        <span>Acceso seguro vía Google Cloud</span>
      </div>
    </div>
  );
};

export default LoginPage;