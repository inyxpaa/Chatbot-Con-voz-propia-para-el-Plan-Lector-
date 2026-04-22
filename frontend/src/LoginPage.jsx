import React from "react";
import { GoogleLogin } from "@react-oauth/google";
import { BookOpen, Sparkles, Brain, Users } from "lucide-react";

const LoginPage = ({ onLoginSuccess }) => {
  return (
    <div className="login-page">
      {/* Fondo animado */}
      <div className="login-bg-orb login-bg-orb--1" />
      <div className="login-bg-orb login-bg-orb--2" />
      <div className="login-bg-orb login-bg-orb--3" />

      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <img src="/android-chrome-192x192.png" alt="LIA" className="login-logo-img" />
        </div>

        {/* Cabecera */}
        <header className="login-header">
          <h1 className="login-title">
            Plan Lector <span className="login-title-accent">AI</span>
          </h1>
          <p className="login-subtitle">Tu asistente inteligente de lectura</p>
        </header>

        {/* Features */}
        <div className="login-features">
          <div className="login-feature">
            <div className="login-feature-icon">
              <Brain size={18} />
            </div>
            <span>IA entrenada con los libros del Plan Lector</span>
          </div>
          <div className="login-feature">
            <div className="login-feature-icon">
              <BookOpen size={18} />
            </div>
            <span>Respuestas personalizadas sobre cada lectura</span>
          </div>
          <div className="login-feature">
            <div className="login-feature-icon">
              <Users size={18} />
            </div>
            <span>Acceso exclusivo para alumnos del IES Comercio</span>
          </div>
        </div>

        {/* Botón Google */}
        <div className="login-google-wrapper">
          <p className="login-cta">Inicia sesión para continuar</p>
          <div className="login-google-btn">
            <GoogleLogin
              onSuccess={onLoginSuccess}
              onError={() => alert("Error al conectar con Google")}
              useOneTap
              shape="pill"
              size="large"
              text="signin_with"
              logo_alignment="center"
            />
          </div>
        </div>

        {/* Footer */}
        <footer className="login-footer">
          <Sparkles size={13} />
          <span>Fomentando la lectura activa · IES Comercio Logroño</span>
        </footer>
      </div>
    </div>
  );
};

export default LoginPage;
