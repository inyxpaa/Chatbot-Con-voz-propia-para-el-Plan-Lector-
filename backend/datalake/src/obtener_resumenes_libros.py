"""
Obtiene informacion enriquecida de cada libro del Plan Lector:
  - Resumen/Argumento completo (Wikipedia ES + EN)
  - Datos del autor con biografia
  - Personajes principales
  - Contexto historico/literario
  - Fragmento de texto original (Project Gutenberg para obras en dominio publico)
Fuentes: Wikipedia API (100% legal, contenido libre) y Project Gutenberg.
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import time
import re
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
raw_dir = base_dir / "raw"
raw_dir.mkdir(parents=True, exist_ok=True)
output_file = raw_dir / "resumenes_libros_raw.txt"

# ============================================================
# LISTA COMPLETA DE LIBROS DEL PLAN LECTOR
# (titulo, autor, curso_dpto, wiki_es_obra, wiki_en_obra, wiki_es_autor, wiki_en_autor, gutenberg_id)
# ============================================================
LIBROS = [
    # LENGUA 1 ESO
    {
        "titulo": "Drácula",
        "autor": "Bram Stoker",
        "curso": "Lengua 1º ESO",
        "wiki_es_obra": "Drácula_(novela)",
        "wiki_en_obra": "Dracula",
        "wiki_es_autor": "Bram_Stoker",
        "wiki_en_autor": "Bram_Stoker",
        "gutenberg_id": 345,
        "actividad": "Creación de un periódico y murales de personajes de terror."
    },
    {
        "titulo": "Percy Jackson y el ladrón del rayo",
        "autor": "Rick Riordan",
        "curso": "Lengua 1º ESO",
        "wiki_es_obra": "Percy_Jackson_y_el_ladrón_del_rayo",
        "wiki_en_obra": "The_Lightning_Thief",
        "wiki_es_autor": "Rick_Riordan",
        "wiki_en_autor": "Rick_Riordan",
        "gutenberg_id": None,
        "actividad": "Tertulia dialógica."
    },
    {
        "titulo": "Ausencias",
        "autor": "Ramón Rodríguez y Cristina Bueno",
        "curso": "Lengua 1º ESO",
        "wiki_es_obra": None,
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Creación de un cómic."
    },
    # LENGUA 2 ESO
    {
        "titulo": "50 cosas sobre mí",
        "autor": "Care Santos",
        "curso": "Lengua 2º ESO",
        "wiki_es_obra": "Care_Santos",
        "wiki_en_obra": None,
        "wiki_es_autor": "Care_Santos",
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Caja literaria."
    },
    {
        "titulo": "El medallón perdido",
        "autor": "Ana Alcolea",
        "curso": "Lengua 2º ESO",
        "wiki_es_obra": "Ana_Alcolea",
        "wiki_en_obra": None,
        "wiki_es_autor": "Ana_Alcolea",
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lapbook."
    },
    {
        "titulo": "La ratonera",
        "autor": "Agatha Christie",
        "curso": "Lengua 2º ESO",
        "wiki_es_obra": "La_ratonera_(obra_de_teatro)",
        "wiki_en_obra": "The_Mousetrap",
        "wiki_es_autor": "Agatha_Christie",
        "wiki_en_autor": "Agatha_Christie",
        "gutenberg_id": None,
        "actividad": "Cartelera literaria."
    },
    # LENGUA 3 ESO
    {
        "titulo": "Deja en paz a los muertos",
        "autor": "J.R. Barat",
        "curso": "Lengua 3º ESO",
        "wiki_es_obra": None,
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Debate sobre la memoria histórica."
    },
    {
        "titulo": "El diario de Ana Frank",
        "autor": "Ana Frank",
        "curso": "Lengua 3º ESO",
        "wiki_es_obra": "El_diario_de_Ana_Frank",
        "wiki_en_obra": "The_Diary_of_a_Young_Girl",
        "wiki_es_autor": "Ana_Frank",
        "wiki_en_autor": "Anne_Frank",
        "gutenberg_id": None,
        "actividad": "Actividad llamada Cucaña sobre la memoria del Holocausto."
    },
    {
        "titulo": "Lazarillo de Tormes",
        "autor": "Anónimo",
        "curso": "Lengua 3º ESO",
        "wiki_es_obra": "Lazarillo_de_Tormes",
        "wiki_en_obra": "Lazarillo_de_Tormes",
        "wiki_es_autor": "Lazarillo_de_Tormes",
        "wiki_en_autor": "Lazarillo_de_Tormes",
        "gutenberg_id": 73,
        "actividad": "Lectura de clásico adaptado."
    },
    {
        "titulo": "La visita del inspector",
        "autor": "J.B. Priestley",
        "curso": "Lengua 3º ESO",
        "wiki_es_obra": "La_visita_del_inspector",
        "wiki_en_obra": "An_Inspector_Calls",
        "wiki_es_autor": "J._B._Priestley",
        "wiki_en_autor": "J._B._Priestley",
        "gutenberg_id": None,
        "actividad": "Lectura dramática y debate."
    },
    {
        "titulo": "Bala para el recuerdo",
        "autor": "Maite Carranza",
        "curso": "Lengua 3º ESO",
        "wiki_es_obra": "Maite_Carranza",
        "wiki_en_obra": None,
        "wiki_es_autor": "Maite_Carranza",
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura y debate."
    },
    # LENGUA 4 ESO
    {
        "titulo": "Marianela",
        "autor": "Benito Pérez Galdós",
        "curso": "Lengua 4º ESO",
        "wiki_es_obra": "Marianela_(novela)",
        "wiki_en_obra": "Marianela_(novel)",
        "wiki_es_autor": "Benito_Pérez_Galdós",
        "wiki_en_autor": "Benito_Pérez_Galdós",
        "gutenberg_id": 22290,
        "actividad": "Debate y lectura."
    },
    {
        "titulo": "Bodas de sangre",
        "autor": "Federico García Lorca",
        "curso": "Lengua 4º ESO",
        "wiki_es_obra": "Bodas_de_sangre",
        "wiki_en_obra": "Blood_Wedding_(play)",
        "wiki_es_autor": "Federico_García_Lorca",
        "wiki_en_autor": "Federico_García_Lorca",
        "gutenberg_id": None,
        "actividad": "Lectura dramática."
    },
    {
        "titulo": "Caperucita en Manhattan",
        "autor": "Carmen Martín Gaite",
        "curso": "Lengua 4º ESO",
        "wiki_es_obra": "Caperucita_en_Manhattan",
        "wiki_en_obra": None,
        "wiki_es_autor": "Carmen_Martín_Gaite",
        "wiki_en_autor": "Carmen_Martín_Gaite",
        "gutenberg_id": None,
        "actividad": "Lectura y análisis literario."
    },
    {
        "titulo": "Historia de una escalera",
        "autor": "Antonio Buero Vallejo",
        "curso": "Lengua 4º ESO",
        "wiki_es_obra": "Historia_de_una_escalera",
        "wiki_en_obra": None,
        "wiki_es_autor": "Antonio_Buero_Vallejo",
        "wiki_en_autor": "Antonio_Buero_Vallejo",
        "gutenberg_id": None,
        "actividad": "Lectura dramática y análisis."
    },
    {
        "titulo": "La mecánica del corazón",
        "autor": "Mathías Malzieu",
        "curso": "Lengua 4º ESO",
        "wiki_es_obra": "La_mecánica_del_corazón",
        "wiki_en_obra": "The_Boy_with_the_Cuckoo-Clock_Heart",
        "wiki_es_autor": "Mathias_Malzieu",
        "wiki_en_autor": "Mathias_Malzieu",
        "gutenberg_id": None,
        "actividad": "Lectura y comentario."
    },
    {
        "titulo": "Donde surgen las sombras",
        "autor": "David Lozano",
        "curso": "Lengua 4º ESO",
        "wiki_es_obra": "David_Lozano_Garbala",
        "wiki_en_obra": None,
        "wiki_es_autor": "David_Lozano_Garbala",
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura y tertulia."
    },
    # ORIENTACIÓN
    {
        "titulo": "La riqueza que el dinero no puede comprar",
        "autor": "Robin Sharma",
        "curso": "Orientación 3º y 4º ESO Diversificación",
        "wiki_es_obra": "Robin_Sharma",
        "wiki_en_obra": "Robin_Sharma",
        "wiki_es_autor": "Robin_Sharma",
        "wiki_en_autor": "Robin_Sharma",
        "gutenberg_id": None,
        "actividad": "Lectura en clase en voz alta, puesta en común y actividades."
    },
    {
        "titulo": "Cartas desde el desierto",
        "autor": "Manu Carbajo",
        "curso": "Orientación 3º y 4º ESO Diversificación",
        "wiki_es_obra": None,
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura en casa, tertulia en clase y encuentro con el autor."
    },
    # BIOLOGÍA Y GEOLOGÍA
    {
        "titulo": "¿Qué pasa en tu cabeza? El cerebro y la neurociencia",
        "autor": "Sara Capogrossi y Simone Macrì",
        "curso": "Biología y Geología 3º ESO",
        "wiki_es_obra": "Neurociencia",
        "wiki_en_obra": "Neuroscience",
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura por capítulos y videoresumen."
    },
    {
        "titulo": "Memorias ahogadas",
        "autor": "Jairo Marcos Pérez y Mª Ángeles Fernández González",
        "curso": "Biología / Ciencias Aplicadas SAD II",
        "wiki_es_obra": "Embalse",
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura de capítulos sobre pueblos desaparecidos por embalses y debate."
    },
    # CIENCIAS DE LA TIERRA
    {
        "titulo": "Vivir con el río. Gestión del riesgo de inundación",
        "autor": "Rubén Ladrera, Francesc La Roca, Joserra Díez",
        "curso": "Ciencias de la Tierra 2º Bachillerato",
        "wiki_es_obra": "Inundación",
        "wiki_en_obra": "Flood_risk_management",
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura por capítulos y presentaciones de resúmenes."
    },
    # ADMINISTRATIVO
    {
        "titulo": "La Rioja y sus pueblos entre cuentos",
        "autor": "Ainara G. Álava y S.H. López-Pastor",
        "curso": "Administrativo 1º FPGB SAD",
        "wiki_es_obra": "La_Rioja_(España)",
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura individual de cuentos, resumen e investigación."
    },
    # COMERCIO Y MARKETING
    {
        "titulo": "¿Quién se ha llevado mi queso?",
        "autor": "Spencer Johnson",
        "curso": "Comercio y Márketing 1ACO",
        "wiki_es_obra": "¿Quién_se_ha_llevado_mi_queso%3F",
        "wiki_en_obra": "Who_Moved_My_Cheese%3F",
        "wiki_es_autor": "Spencer_Johnson_(escritor)",
        "wiki_en_autor": "Spencer_Johnson",
        "gutenberg_id": None,
        "actividad": "Lectura en clase, reflexión y aplicación a contenidos del módulo."
    },
    # GEOGRAFÍA E HISTORIA
    {
        "titulo": "Siete historias para la infanta Margarita",
        "autor": "Miguel Fernández-Pacheco",
        "curso": "Geografía e Historia 2º-4º ESO y 1º Bach.",
        "wiki_es_obra": "Miguel_Fernández-Pacheco",
        "wiki_en_obra": None,
        "wiki_es_autor": "Miguel_Fernández-Pacheco",
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Tertulia dialógica."
    },
    {
        "titulo": "Endurance, la prisión blanca",
        "autor": "Alfred Lansing",
        "curso": "Geografía e Historia 2º-4º ESO y 1º Bach.",
        "wiki_es_obra": "Expedición_Imperial_Transantártica",
        "wiki_en_obra": "Endurance_(1998_book)",
        "wiki_es_autor": "Alfred_Lansing",
        "wiki_en_autor": "Alfred_Lansing",
        "gutenberg_id": None,
        "actividad": "Tertulia dialógica."
    },
    {
        "titulo": "Maus",
        "autor": "Art Spiegelman",
        "curso": "Geografía e Historia 2º-4º ESO y 1º Bach.",
        "wiki_es_obra": "Maus",
        "wiki_en_obra": "Maus",
        "wiki_es_autor": "Art_Spiegelman",
        "wiki_en_autor": "Art_Spiegelman",
        "gutenberg_id": None,
        "actividad": "Tertulia dialógica."
    },
    {
        "titulo": "Persépolis",
        "autor": "Marjane Satrapi",
        "curso": "Geografía e Historia 2º-4º ESO y 1º Bach.",
        "wiki_es_obra": "Persépolis_(cómic)",
        "wiki_en_obra": "Persepolis_(comics)",
        "wiki_es_autor": "Marjane_Satrapi",
        "wiki_en_autor": "Marjane_Satrapi",
        "gutenberg_id": None,
        "actividad": "Tertulia dialógica."
    },
    # FILOSOFÍA
    {
        "titulo": "El Principito",
        "autor": "Antoine de Saint-Exupéry",
        "curso": "Filosofía 1º Bach. y 1º ESO",
        "wiki_es_obra": "El_principito",
        "wiki_en_obra": "The_Little_Prince",
        "wiki_es_autor": "Antoine_de_Saint-Exupéry",
        "wiki_en_autor": "Antoine_de_Saint-Exupéry",
        "gutenberg_id": None,
        "actividad": "Análisis y comentario por grupos y parejas."
    },
    {
        "titulo": "El escarabajo de oro",
        "autor": "Edgar Allan Poe",
        "curso": "Filosofía 1º Bach.",
        "wiki_es_obra": "El_escarabajo_de_oro",
        "wiki_en_obra": "The_Gold-Bug",
        "wiki_es_autor": "Edgar_Allan_Poe",
        "wiki_en_autor": "Edgar_Allan_Poe",
        "gutenberg_id": 2147,
        "actividad": "Análisis y comentario."
    },
    {
        "titulo": "¿Hay filosofía en tu nevera?",
        "autor": "Enric F. Gel",
        "curso": "Filosofía 1º Bach.",
        "wiki_es_obra": "Filosofía",
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Análisis y comentario por grupos."
    },
    {
        "titulo": "Filosofía en la calle",
        "autor": "Eduardo Infante",
        "curso": "Filosofía 1º Bach.",
        "wiki_es_obra": "Filosofía",
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura, análisis y comentario en clase."
    },
    # INGLÉS
    {
        "titulo": "The Adventures of Tom Sawyer",
        "autor": "Mark Twain",
        "curso": "Inglés 1º ESO",
        "wiki_es_obra": "Las_aventuras_de_Tom_Sawyer",
        "wiki_en_obra": "The_Adventures_of_Tom_Sawyer",
        "wiki_es_autor": "Mark_Twain",
        "wiki_en_autor": "Mark_Twain",
        "gutenberg_id": 74,
        "actividad": "Lectura adaptada con booklet de ilustraciones."
    },
    {
        "titulo": "The Murders in the Rue Morgue",
        "autor": "Edgar Allan Poe",
        "curso": "Inglés 2º ESO",
        "wiki_es_obra": "Los_crímenes_de_la_calle_Morgue",
        "wiki_en_obra": "The_Murders_in_the_Rue_Morgue",
        "wiki_es_autor": "Edgar_Allan_Poe",
        "wiki_en_autor": "Edgar_Allan_Poe",
        "gutenberg_id": 32037,
        "actividad": "Lectura en cómic con asunción de voces de personajes."
    },
    {
        "titulo": "The Indian in the Cupboard",
        "autor": "Lynne Reid Banks",
        "curso": "Inglés 2º ESO",
        "wiki_es_obra": "The_Indian_in_the_Cupboard",
        "wiki_en_obra": "The_Indian_in_the_Cupboard",
        "wiki_es_autor": "Lynne_Reid_Banks",
        "wiki_en_autor": "Lynne_Reid_Banks",
        "gutenberg_id": None,
        "actividad": "Lectura adaptada con booklet final."
    },
    {
        "titulo": "Smile",
        "autor": "Raina Telgemeier",
        "curso": "Inglés 3º ESO",
        "wiki_es_obra": None,
        "wiki_en_obra": "Smile_(Telgemeier_graphic_novel)",
        "wiki_es_autor": "Raina_Telgemeier",
        "wiki_en_autor": "Raina_Telgemeier",
        "gutenberg_id": None,
        "actividad": "Lectura compartida de novela gráfica con cuaderno de lectura."
    },
    {
        "titulo": "The Secret of the Lake",
        "autor": "varios (adaptación)",
        "curso": "Inglés 4º ESO",
        "wiki_es_obra": None,
        "wiki_en_obra": None,
        "wiki_es_autor": None,
        "wiki_en_autor": None,
        "gutenberg_id": None,
        "actividad": "Lectura adaptada con actividades escritas."
    },
    {
        "titulo": "The Great Gatsby",
        "autor": "F. Scott Fitzgerald",
        "curso": "Inglés 1º Bachillerato",
        "wiki_es_obra": "El_gran_Gatsby",
        "wiki_en_obra": "The_Great_Gatsby",
        "wiki_es_autor": "F._Scott_Fitzgerald",
        "wiki_en_autor": "F._Scott_Fitzgerald",
        "gutenberg_id": None,
        "actividad": "Lectura adaptada con resumen, preguntas de comprensión y reflexión."
    },
]

# =====================================================
# FUNCIONES
# =====================================================

HEADERS = {"User-Agent": "PlanLectorBot/2.0 (IES Comercio, contacto educativo)"}

def get_wikipedia_full_text(page_title: str, lang: str = "es", max_chars: int = 6000) -> str:
    """Obtiene el texto completo de una pagina de Wikipedia (extracto largo)."""
    if not page_title:
        return ""
    url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=query&titles={page_title}&prop=extracts"
        f"&explaintext=true&exlimit=1&format=json&redirects=1"
    )
    try:
        resp = requests.get(url, timeout=15, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                # Limpiar encabezados de secciones tipo == Titulo ==
                extract = re.sub(r'==+\s*.*?\s*==+', '', extract)
                # Limpiar lineas vacias multiples
                extract = re.sub(r'\n{3,}', '\n\n', extract)
                # Quitar lineas muy cortas que suelen ser artefactos de navegacion
                lineas = [l for l in extract.split('\n') if len(l.strip()) > 15 or l.strip() == '']
                extract = '\n'.join(lineas).strip()
                return extract[:max_chars]
    except Exception as e:
        print(f"    Error Wikipedia ({lang}) '{page_title}': {e}")
    return ""


def get_gutenberg_excerpt(gutenberg_id: int, max_chars: int = 5000) -> str:
    """Descarga un fragmento del texto original de Project Gutenberg."""
    urls = [
        f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}.txt",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=20, headers=HEADERS)
            if resp.status_code == 200:
                raw = resp.text
                # Saltar cabecera del Proyecto Gutenberg
                markers = ["*** START OF", "***START OF", "CHAPTER I", "CHAPTER 1",
                           "CAPÍTULO I", "CAPÍTULO PRIMERO", "Tratado primero"]
                start_idx = 0
                for marker in markers:
                    idx = raw.find(marker)
                    if idx != -1:
                        start_idx = idx
                        break
                # Saltar la linea del marcador en si
                text = raw[start_idx:]
                first_newline = text.find('\n')
                if first_newline != -1:
                    text = text[first_newline:]
                text = re.sub(r'\r\n', '\n', text)
                text = re.sub(r'\n{3,}', '\n\n', text)
                return text.strip()[:max_chars]
        except Exception:
            pass
    return ""


# =====================================================
# EJECUCION PRINCIPAL
# =====================================================

all_texts = []
sin_info = []

print(f"Procesando {len(LIBROS)} libros del Plan Lector con informacion enriquecida...\n")

for libro in LIBROS:
    titulo    = libro["titulo"]
    autor     = libro["autor"]
    curso     = libro["curso"]
    actividad = libro["actividad"]
    print(f"-> {titulo} ({autor})")

    secciones = []

    # --- 1. INFORMACION DE LA OBRA (Wikipedia ES) ---
    info_obra_es = get_wikipedia_full_text(libro["wiki_es_obra"], "es", max_chars=5000)
    if info_obra_es:
        print(f"   OK Wikipedia ES obra: {len(info_obra_es)} chars")
        secciones.append(f"=== INFORMACION DE LA OBRA (Wikipedia ES) ===\n{info_obra_es}")
    time.sleep(0.5)

    # --- 2. INFORMACION DE LA OBRA (Wikipedia EN) ---
    info_obra_en = get_wikipedia_full_text(libro["wiki_en_obra"], "en", max_chars=5000)
    if info_obra_en:
        print(f"   OK Wikipedia EN obra: {len(info_obra_en)} chars")
        secciones.append(f"=== BOOK INFORMATION (Wikipedia EN) ===\n{info_obra_en}")
    time.sleep(0.5)

    # --- 3. BIOGRAFIA DEL AUTOR (Wikipedia ES) ---
    if libro["wiki_es_autor"] and libro["wiki_es_autor"] != libro["wiki_es_obra"]:
        bio_es = get_wikipedia_full_text(libro["wiki_es_autor"], "es", max_chars=3000)
        if bio_es:
            print(f"   OK Autor Wikipedia ES: {len(bio_es)} chars")
            secciones.append(f"=== BIOGRAFIA DEL AUTOR: {autor} (Wikipedia ES) ===\n{bio_es}")
        time.sleep(0.5)

    # --- 4. BIOGRAFIA DEL AUTOR (Wikipedia EN) ---
    if libro["wiki_en_autor"] and libro["wiki_en_autor"] != libro["wiki_en_obra"]:
        bio_en = get_wikipedia_full_text(libro["wiki_en_autor"], "en", max_chars=3000)
        if bio_en:
            print(f"   OK Autor Wikipedia EN: {len(bio_en)} chars")
            secciones.append(f"=== AUTHOR BIOGRAPHY: {autor} (Wikipedia EN) ===\n{bio_en}")
        time.sleep(0.5)

    # --- 5. FRAGMENTO ORIGINAL de Project Gutenberg (solo dominio publico) ---
    if libro["gutenberg_id"]:
        print(f"   -> Gutenberg ID {libro['gutenberg_id']}...")
        fragmento = get_gutenberg_excerpt(libro["gutenberg_id"])
        if fragmento:
            print(f"   OK Gutenberg: {len(fragmento)} chars")
            secciones.append(f"=== FRAGMENTO DEL TEXTO ORIGINAL (Project Gutenberg) ===\n{fragmento}")
        time.sleep(1)

    if secciones:
        bloque = (
            f"FUENTE: Libro Plan Lector - {titulo}\n"
            f"TITULO: {titulo}\n"
            f"AUTOR: {autor}\n"
            f"CURSO Y DEPARTAMENTO: {curso}\n"
            f"ACTIVIDAD EN CLASE: {actividad}\n"
            f"URL: https://es.wikipedia.org/wiki/{libro['wiki_es_obra'] or ''}\n\n"
            + "\n\n".join(secciones)
        )
        all_texts.append(bloque)
    else:
        sin_info.append(titulo)
        print(f"   AVISO: Sin informacion para: {titulo}")

# Guardar
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n\n==================================\n\n".join(all_texts))

print(f"\nResumenes enriquecidos guardados en: {output_file}")
print(f"Libros con informacion: {len(all_texts)} / {len(LIBROS)}")
if sin_info:
    print(f"Sin informacion: {', '.join(sin_info)}")
