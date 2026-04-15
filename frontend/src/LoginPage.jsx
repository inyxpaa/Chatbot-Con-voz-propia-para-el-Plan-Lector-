import React from "react";
import { GoogleLogin } from "@react-oauth/google";
import { LogIn, BookOpen } from "lucide-react";

const LoginPage = ({ onLoginSuccess }) => {
  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <BookOpen size={48} className="logo-icon" />
          <h1>Plan Lector</h1>
          <p>Asistente virtual con voz propia</p>
        </div>
        
        <div className="login-body">
          <p className="login-description">
            Inicia sesión para interactuar con la inteligencia artificial del centro y resolver tus dudas sobre las lecturas.
          </p>
          
          <div className="google-btn-wrapper">
            <GoogleLogin
              onSuccess={(credentialResponse) => {
                onLoginSuccess(credentialResponse);
              }}
              onError={() => {
                console.log("Login Failed");
                alert("Error al iniciar sesión con Google");
              }}
              useOneTap
            />
          </div>
        </div>
        
        <div className="login-footer">
          <p>© 2024 IES Comercio | Plan de Fomento de la Lectura</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
