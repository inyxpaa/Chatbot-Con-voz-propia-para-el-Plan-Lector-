import React from "react";
import { GoogleLogin } from "@react-oauth/google";
import { LogIn, BookOpen, Sparkles } from "lucide-react";

const LoginPage = ({ onLoginSuccess }) => {
  return (
    <div className="login-container">
      <div className="login-card">
        <header style={{marginBottom: '2rem'}}>
          <div style={{display: 'inline-flex', padding: '1rem', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '1rem', marginBottom: '1rem'}}>
            <BookOpen size={40} style={{color: '#6366f1'}} />
          </div>
          <h1 style={{fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: '0.5rem'}}>
            Plan Lector <span style={{color: '#6366f1'}}>AI</span>
          </h1>
          <p style={{color: '#94a3b8', fontSize: '0.9rem'}}>Asistente virtual con voz propia</p>
        </header>
        
        <div className="login-body" style={{marginBottom: '2.5rem'}}>
          <p style={{fontSize: '0.95rem', lineHeight: 1.6, color: '#f8fafc', marginBottom: '2rem'}}>
            Descubre el universo de tus libros favoritos con nuestra inteligencia artificial personalizada.
          </p>
          
          <div style={{display: 'flex', justifyContent: 'center', background: 'white', padding: '0.5rem', borderRadius: '0.75rem'}}>
            <GoogleLogin
              onSuccess={(credentialResponse) => {
                onLoginSuccess(credentialResponse);
              }}
              onError={() => alert("Error al conectar con Google")}
              useOneTap
            />
          </div>
        </div>
        
        <footer style={{borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1.5rem'}}>
          <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: '#64748b', fontSize: '0.75rem'}}>
            <Sparkles size={14} />
            <span>Fomentando la lectura activa</span>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default LoginPage;
