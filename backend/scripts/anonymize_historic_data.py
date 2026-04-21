import sys
import os
import hashlib
import re

# Añadir el directorio backend al sys.path para poder importar database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import SessionLocal, Busqueda
except ImportError as e:
    print(f"Error al importar database: {e}")
    print("Asegúrate de ejecutar este script desde el directorio raíz del proyecto o desde backend/scripts.")
    sys.exit(1)

def hash_email(email: str) -> str:
    """Retorna un hash SHA-256 del email para anonimización."""
    if not email:
        return "anonymous"
    # Si ya parece un hash (64 hex chars), no lo re-hasheamos
    if len(email) == 64 and all(c in "0123456789abcdef" for c in email.lower()):
        return email
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()

def scrub_pii(text: str) -> str:
    """Ofusca emails y números de teléfono en el texto."""
    if not text:
        return ""
    # Regex para emails
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    # Regex para teléfonos (formato básico internacional y local)
    text = re.sub(r'\+?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{0,4}', '[TELÉFONO]', text)
    return text

def anonymize_data():
    db = SessionLocal()
    try:
        registros = db.query(Busqueda).all()
        print(f"Encontrados {len(registros)} registros en la tabla 'busquedas'.")
        
        count = 0
        for reg in registros:
            # 1. Anonimizar email
            original_email = reg.user_email
            reg.user_email = hash_email(original_email)
            
            # 2. Limpiar PII en pregunta y respuesta
            reg.pregunta = scrub_pii(reg.pregunta)
            reg.respuesta = scrub_pii(reg.respuesta)
            
            count += 1
            if count % 50 == 0:
                db.commit()
                print(f"Procesados {count} registros...")
        
        db.commit()
        print(f"¡Éxito! Se han anonimizado {count} registros correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error durante la migración: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    anonymize_data()
