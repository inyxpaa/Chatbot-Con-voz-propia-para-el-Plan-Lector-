import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal, Busqueda

def verify_anonymization():
    db = SessionLocal()
    try:
        registros = db.query(Busqueda).all()
        print(f"Verificando {len(registros)} registros...")
        
        all_passed = True
        for reg in registros:
            # Check if email contains '@' or doesn't look like a hash
            if "@" in reg.user_email:
                print(f"FALLO: Registro {reg.id} tiene un email no anonimizado: {reg.user_email}")
                all_passed = False
            
            if "[EMAIL]" in reg.pregunta or "[TELÉFONO]" in reg.pregunta:
                print(f"OK: Registro {reg.id} tiene PII ofuscada en la pregunta.")
            
            # Simple check for hash length
            if len(reg.user_email) != 64 and reg.user_email != "anonymous":
                print(f"FALLO: Registro {reg.id} tiene un user_email que no parece un hash SHA-256: {reg.user_email}")
                all_passed = False
        
        if all_passed:
            print("VERIFICACIÓN COMPLETADA: Todos los registros parecen estar anonimizados correctamente.")
    except Exception as e:
        print(f"Error durante la verificación: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_anonymization()
