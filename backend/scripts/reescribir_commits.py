#!/usr/bin/env python3
"""Reescribe mensajes de commit en inglés a español usando git filter-branch."""
import subprocess

# Mapa de traducciones: mensaje_original -> mensaje_en_español
TRADUCCIONES = {
    "feat: integrate RDS PostgreSQL and MongoDB Atlas for backend persistence":
        "funcionalidad: integrar RDS PostgreSQL y MongoDB para persistencia del backend",
    "fix: add chroma vector files so collection [quijote] is available in docker":
        "corrección: añadir ficheros vectoriales de chroma para que la colección [quijote] esté disponible en docker",
    "fix: include chroma_db in repository for backend deployment":
        "corrección: incluir chroma_db en el repositorio para el despliegue del backend",
    "fix: resolve sqlite and chroma db paths inside docker container":
        "corrección: resolver rutas de sqlite y chroma_db dentro del contenedor docker",
    "fix: resolve relative import bug in docker container":
        "corrección: resolver error de importación relativa dentro del contenedor docker",
    "fix: resolve CORS issue for frontend connections":
        "corrección: resolver el problema de CORS para las conexiones del frontend",
    "fix: frontend api connection, install docker on ec2":
        "corrección: conexión de api del frontend e instalación de docker en ec2",
    "fix: copy frontend production build from /backend/static instead of /app/dist":
        "corrección: copiar la build de producción del frontend desde /backend/static en vez de /app/dist",
    "ci: include dev branch in workflow triggers":
        "ci: incluir la rama dev en los disparadores del flujo de trabajo",
    "ci: trigger deployment with new EC2 IPs":
        "ci: activar despliegue con las nuevas IPs de EC2",
    "ci: add dockerfiles and github actions workflows for deployment":
        "ci: añadir dockerfiles y flujos de trabajo de github actions para el despliegue",
    "chore: add debugging logs out and ignore chroma_db files":
        "tarea: añadir logs de depuración e ignorar ficheros de chroma_db",
    "fix: resolve path bugs in datalake preprocessing and automate DB creation":
        "corrección: resolver errores de rutas en el preprocesado del datalake y automatizar la creación de la BD",
    "feat: unified installer and startup script":
        "funcionalidad: instalador unificado y script de arranque",
    "refactor: mover src/ a modelo/src/ y agregar requirements.txt":
        "refactorización: mover src/ a modelo/src/ y añadir requirements.txt",
    "merge: integrar origin/dev antes de subir cambios del datalake":
        "fusión: integrar origin/dev antes de subir cambios del datalake",
    "feat(ingesta): leer datos desde Data Lake en lugar de directorio local":
        "funcionalidad(ingesta): leer datos desde el Data Lake en lugar del directorio local",
    "Update README with project details and setup instructions":
        "documentación: actualizar README con detalles del proyecto e instrucciones de configuración",
    "Delete src directory":
        "tarea: eliminar el directorio src",
}

def reescribir_commits():
    # Construimos el script de sed para git filter-branch
    sed_parts = []
    for original, traduccion in TRADUCCIONES.items():
        # Escapar caracteres especiales para sed
        orig_esc = original.replace("'", "'\\''").replace("/", r"\/").replace("[", r"\[").replace("]", r"\]")
        trad_esc = traduccion.replace("'", "'\\''").replace("/", r"\/").replace("[", r"\[").replace("]", r"\]")
        sed_parts.append(f"s/^{orig_esc}/{trad_esc}/")

    sed_script = "; ".join(sed_parts)
    
    cmd = [
        "git", "filter-branch", "-f", "--msg-filter",
        f"sed -e '{sed_script}'",
        "--", "--all"
    ]
    
    print("Reescribiendo historial de commits...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("Hecho.")

if __name__ == "__main__":
    reescribir_commits()
