import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
Script para obtener resumenes legales de todos los libros del Plan Lector.
Fuentes utilizadas:
  - Wikipedia en español (API REST - dominio público legal)
  - Wikipedia en inglés (para libros en inglés)
  - Project Gutenberg (textos completos de obras en dominio público)
"""

import requests
import time
import re
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
raw_dir = base_dir / "raw"
raw_dir.mkdir(parents=True, exist_ok=True)
output_file = raw_dir / "resumenes_libros_raw.txt"

# ============================================================
# LISTA DE LIBROS DEL PLAN LECTOR
# Formato: (título, autor, curso_departamento, búsqueda_wikipedia_ES, búsqueda_wikipedia_EN, gutenberg_id)
# gutenberg_id = None si el libro NO está en dominio público
# ============================================================
LIBROS = [
    # LENGUA 1º ESO
    ("Drácula", "Bram Stoker", "Lengua 1º ESO", "Drácula_(novela)", "Dracula", 345),
    ("Percy Jackson y el ladrón del rayo", "Rick Riordan", "Lengua 1º ESO", "Percy_Jackson_y_el_ladrón_del_rayo", "The_Lightning_Thief", None),
    ("Ausencias", "Ramón Rodríguez y Cristina Bueno", "Lengua 1º ESO", "Ausencias_(novela_gráfica)", None, None),

    # LENGUA 2º ESO
    ("50 cosas sobre mí", "Care Santos", "Lengua 2º ESO", "Care_Santos", None, None),
    ("El medallón perdido", "Ana Alcolea", "Lengua 2º ESO", "Ana_Alcolea", None, None),
    ("La ratonera", "Agatha Christie", "Lengua 2º ESO", "La_ratonera_(obra_de_teatro)", "The_Mousetrap", None),

    # LENGUA 3º ESO
    ("Ana Frank, la memoria del Holocausto", "Eduardo Lozano", "Lengua 3º ESO", "El_diario_de_Ana_Frank", "The_Diary_of_a_Young_Girl", None),
    ("Lazarillo de Tormes", "Anónimo", "Lengua 3º ESO", "Lazarillo_de_Tormes", "Lazarillo_de_Tormes", 73),
    ("La visita del inspector", "J.B. Priestley", "Lengua 3º ESO", "La_visita_del_inspector", "An_Inspector_Calls", None),
    ("Bala para el recuerdo", "Maite Carranza", "Lengua 3º ESO", "Maite_Carranza", None, None),

    # LENGUA 4º ESO
    ("Marianela", "Benito Pérez Galdós", "Lengua 4º ESO", "Marianela_(novela)", "Marianela_(novel)", 22290),
    ("Bodas de sangre", "Federico García Lorca", "Lengua 4º ESO", "Bodas_de_sangre", "Blood_Wedding_(play)", None),
    ("Caperucita en Manhattan", "Carmen Martín Gaite", "Lengua 4º ESO", "Caperucita_en_Manhattan", None, None),
    ("Historia de una escalera", "Antonio Buero Vallejo", "Lengua 4º ESO", "Historia_de_una_escalera", None, None),
    ("La mecánica del corazón", "Mathías Malzieu", "Lengua 4º ESO", "La_mecánica_del_corazón", "The_Boy_with_the_Cuckoo-Clock_Heart", None),
    ("Donde surgen las sombras", "David Lozano", "Lengua 4º ESO", "David_Lozano_Garbala", None, None),

    # ORIENTACIÓN
    ("La riqueza que el dinero no puede comprar", "Robin Sharma", "Orientación 3º y 4º ESO Diver", "Robin_Sharma", None, None),
    ("Cartas desde el desierto", "Manu Carbajo", "Orientación 3º y 4º ESO Diver", "Manu_Carbajo", None, None),

    # BIOLOGÍA Y GEOLOGÍA
    ("¿Qué pasa en tu cabeza? El cerebro y la neurociencia", "Sara Capogrossi y Simone Macrì", "Biología y Geología 3º ESO", "Neurociencia", "Neuroscience", None),
    ("Memorias ahogadas", "Jairo Marcos Pérez", "Biología y Geología / Ciencias Aplicadas", "Embalse", None, None),

    # CIENCIAS DE LA TIERRA
    ("Vivir con el río. Gestión del riesgo de inundación", "Rubén Ladrera, Francesc La Roca, Joserra Díez", "Ciencias de la Tierra 2º Bach.", "Gestión_del_riesgo_de_inundación", "Flood_risk_management", None),

    # ADMINISTRATIVO
    ("La Rioja y sus pueblos entre cuentos", "Ainara G. Álava, S.H. López-Pastor", "Administrativo 1º FPGB SAD", "La_Rioja", None, None),

    # COMERCIO Y MÁRKETING
    ("¿Quién se ha llevado mi queso?", "Spencer Johnson", "Comercio y Márketing 1 ACO", "¿Quién_se_ha_llevado_mi_queso%3F", "Who_Moved_My_Cheese%3F", None),

    # GEOGRAFÍA E HISTORIA
    ("Endurance, la prisión blanca", "Alfred Lansing", "Geografía e Historia", "Expedición_Endurance", "Endurance_(1998_book)", None),
    ("Maus", "Art Spiegelman", "Geografía e Historia", "Maus", "Maus", None),
    ("Persépolis", "Marjane Satrapi", "Geografía e Historia", "Persépolis_(cómic)", "Persepolis_(comics)", None),
    ("Siete historias para la infanta Margarita", "Miguel Fernández-Pacheco", "Geografía e Historia", "Miguel_Fernández-Pacheco", None, None),

    # FILOSOFÍA
    ("El Principito", "Antoine de Saint-Exupéry", "Filosofía 1º Bach.", "El_principito", "The_Little_Prince", None),
    ("El escarabajo de oro", "Edgar Allan Poe", "Filosofía 1º Bach.", "El_escarabajo_de_oro", "The_Gold-Bug", 2147),
    ("¿Hay filosofía en tu nevera?", "Enric F. Gel", "Filosofía 1º Bach.", "Enric_F._Gel", None, None),
    ("Filosofía en la calle", "Eduardo Infante", "Filosofía 1º Bach.", "Eduardo_Infante", None, None),

    # INGLÉS
    ("The Adventures of Tom Sawyer", "Mark Twain", "Inglés 1º ESO", "Las_aventuras_de_Tom_Sawyer", "The_Adventures_of_Tom_Sawyer", 74),
    ("The Murders of the Rue Morgue", "Edgar Allan Poe", "Inglés 2º ESO", "Los_crímenes_de_la_calle_Morgue", "The_Murders_in_the_Rue_Morgue", 32037),
    ("The Indian in the Cupboard", "Lynne Reid Banks", "Inglés 2º ESO", "The_Indian_in_the_Cupboard", "The_Indian_in_the_Cupboard", None),
    ("Smile", "Raina Telgemeier", "Inglés 3º ESO", "Smile_(novela_gráfica)", "Smile_(Telgemeier_graphic_novel)", None),
    ("The Great Gatsby", "F. Scott Fitzgerald", "Inglés 1º Bach.", "El_gran_Gatsby", "The_Great_Gatsby", None),
]

# =============================================
# FUNCIONES DE EXTRACCIÓN
# =============================================

def get_wikipedia_summary(page_title: str, lang: str = "es") -> str:
    """Obtiene el resumen de una página de Wikipedia usando la API REST."""
    if not page_title:
        return ""
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{page_title}"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "PlanLectorBot/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            return extract
    except Exception as e:
        print(f"  Error Wikipedia ({lang}) '{page_title}': {e}")
    return ""


def get_gutenberg_text_excerpt(gutenberg_id: int, max_chars: int = 8000) -> str:
    """Descarga los primeros max_chars caracteres de un texto de Project Gutenberg."""
    urls_to_try = [
        f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}.txt",
    ]
    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "PlanLectorBot/1.0"})
            if resp.status_code == 200:
                raw = resp.text
                # Intentar saltar el encabezado del Proyecto Gutenberg
                start_markers = ["*** START OF", "***START OF", "CHAPTER I", "CAPÍTULO I", "CAPÍTULO PRIMERO"]
                start_idx = 0
                for marker in start_markers:
                    idx = raw.find(marker)
                    if idx != -1:
                        start_idx = idx
                        break
                text = raw[start_idx:start_idx + max_chars]
                # Limpiar caracteres de control y múltiples saltos de línea
                text = re.sub(r'\r\n', '\n', text)
                text = re.sub(r'\n{3,}', '\n\n', text)
                return text.strip()
        except Exception as e:
            pass
    return ""


# =============================================
# EJECUCIÓN PRINCIPAL
# =============================================

all_texts = []

print(f"Procesando {len(LIBROS)} libros del Plan Lector...")

for titulo, autor, curso, wiki_es, wiki_en, gutenberg_id in LIBROS:
    print(f"\n-> {titulo} ({autor})")
    secciones = []

    # 1. Resumen Wikipedia ES
    resumen_es = get_wikipedia_summary(wiki_es, "es") if wiki_es else ""
    if resumen_es:
        print(f"  OK Wikipedia ES: {len(resumen_es)} caracteres")
        secciones.append(f"Resumen en español (Wikipedia): {resumen_es}")
    time.sleep(0.5)

    # 2. Resumen Wikipedia EN (si hay wiki_en definida)
    if wiki_en:
        resumen_en = get_wikipedia_summary(wiki_en, "en")
        if resumen_en:
            print(f"  OK Wikipedia EN: {len(resumen_en)} caracteres")
            secciones.append(f"Summary in English (Wikipedia): {resumen_en}")
        time.sleep(0.5)

    # 3. Fragmento de Project Gutenberg (solo obras en dominio publico)
    if gutenberg_id:
        print(f"  -> Descargando de Project Gutenberg (ID {gutenberg_id})...")
        gutenberg_text = get_gutenberg_text_excerpt(gutenberg_id)
        if gutenberg_text:
            print(f"  OK Gutenberg: {len(gutenberg_text)} caracteres")
            secciones.append(f"Fragmento del texto original (Project Gutenberg):\n{gutenberg_text}")
        time.sleep(1)

    if secciones:
        bloque = (
            f"FUENTE: Libro del Plan Lector - {titulo}\n"
            f"AUTOR: {autor}\n"
            f"CURSO/DEPARTAMENTO: {curso}\n"
            f"URL: https://es.wikipedia.org/wiki/{wiki_es or ''}\n\n"
            + "\n\n".join(secciones)
        )
        all_texts.append(bloque)
    else:
        print(f"  AVISO: No se encontro informacion para: {titulo}")

# Guardar resultado
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n\n==================================\n\n".join(all_texts))

print(f"Resumenes guardados en: {output_file}")
print(f"Total libros con informacion: {len(all_texts)} / {len(LIBROS)}")
