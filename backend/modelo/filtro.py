"""
==============================================================
  filtro.py — Filtro de Contenido Inapropiado
==============================================================
  Proyecto : Chatbot Plan Lector (RAG)
  Autor    : Equipo de Desarrollo

  Qué hace este módulo:
    - Detecta insultos, palabras malsonantes, lenguaje racista,
      discriminatorio y de odio en consultas de usuario.
    - Normaliza el texto para evitar evasiones con tildes,
      espacios, números sustitutos o separadores.
    - Devuelve un resultado estructurado: aceptado / rechazado
      con categoría del problema detectado.

  Uso desde app.py:
      from filtro import verificar_consulta
      resultado = verificar_consulta(texto_usuario)
      if not resultado["aceptado"]:
          # devolver resultado["mensaje"] al usuario
==============================================================
"""

import re
import unicodedata


# ------------------------------------------------------------------
# NORMALIZACIÓN — Elimina variantes de evasión
# ------------------------------------------------------------------
_SUSTITUCIONES_NUMERICAS = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b", "@": "a",
    "$": "s", "!": "i", "+": "t",
})

def _normalizar(texto: str) -> str:
    """
    Convierte el texto a minúsculas, elimina acentos/diacríticos,
    reemplaza sustituciones numéricas comunes y elimina separadores
    no alfanuméricos para detectar evasiones del filtro.

    Ejemplo: 'p.u.t.a', 'PUT@', 'p3nd3j0' → normalizados correctamente.
    """
    # 1. Minúsculas
    texto = texto.lower()
    # 2. Sustituciones numéricas/simbólicas (l33tspeak)
    texto = texto.translate(_SUSTITUCIONES_NUMERICAS)
    # 3. Eliminar acentos y diacríticos
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    # 4. Eliminar separadores internos (p.u.t.a → puta, p_u_t_a → puta)
    texto_sin_sep = re.sub(r"[^a-z0-9\s]", "", texto)
    # Devolvemos ambas versiones concatenadas para máxima cobertura
    return texto + " " + texto_sin_sep


# ------------------------------------------------------------------
# LISTAS DE PATRONES POR CATEGORÍA
# Cada entrada puede ser:
#   - str : palabra exacta (se busca como token completo)
#   - tuple("regex", patrón) : expresión regular directa
# ------------------------------------------------------------------

# Insultos y palabras malsonantes en español
_INSULTOS_ES = [
    "puta", "puto", "putada", "putoama",
    "mierda", "mierdas",
    "cabrón", "cabron", "cabrona",
    "gilipollas", "gilipolla",
    "imbecil", "imbécil",
    "idiota", "idiotas",
    "estupido", "estupida", "estúpido", "estúpida",
    "pendejo", "pendeja", "pendejos",
    "coño", "cono",
    "hostia", "hostias",
    "joder",
    "capullo", "capulla",
    "mamón", "mamon", "mamona",
    "subnormal",
    "retrasado", "retrasada",
    "maricón", "maricon", "marica",
    "zorra", "zorras",
    "bastardo", "bastarda",
    "culo",
    "pollas", "polla",
    "follar",
    "carajo",
    "chingado", "chingada", "chingar",
    "pinche",
    "culero", "culera",
    "verga",
    "coger",        # en contexto vulgar
    "pene", "vagina",  # solo si va con intención ofensiva → se captura por contexto
    "prostituta", "prostitución",
    "cerdo", "cerda",    # como insulto
    "asco",
    "hdp",          # hijo de puta abreviado
    ("regex", r"\bh\.?d\.?p\.?\b"),
    ("regex", r"\bp\.?u\.?t\.?[ao]\b"),
]

# Insultos en inglés comunes que pueden aparecer
_INSULTOS_EN = [
    "fuck", "fucking", "fucker", "fuckoff",
    "shit", "bullshit",
    "bitch", "bitches",
    "asshole", "ass",
    "bastard",
    "damn", "dammit",
    "crap",
    "dick", "cock",
    "pussy",
    "motherfucker", "motherfucking",
    "whore",
    "slut",
    "idiot", "stupid", "moron",
    ("regex", r"\bf\.?u\.?c\.?k\b"),
]

# Lenguaje racista, xenófobo y discriminatorio
_RACISMO = [
    "negro de mierda",
    "sudaca",
    "moro", "moros",
    "gitano de mierda",
    "panchito",
    "chino de mierda",
    "judío de mierda", "judio de mierda",
    "nazi",
    "hitleriano",
    "raza inferior",
    "raza superior",
    "muerte a los",
    "exterminar",
    "limpieza étnica", "limpieza etnica",
    ("regex", r"\bn\.{0,2}i\.{0,2}g\.{0,2}g\w*\b"),   # slur en inglés y variantes
    ("regex", r"\bsp\.?ic\b"),
    ("regex", r"\bw\.?e\.?t\.?b\.?a\.?c\.?k\b"),
    ("regex", r"\bk\.?i\.?k\.?e\b"),
    "white power",
    "heil hitler",
    "88",            # código neonazi ("Heil Hitler")
    "seig heil", "sieg heil",
]

# Lenguaje de odio y amenazas
_ODIO_AMENAZAS = [
    "te voy a matar",
    "te mato",
    "os mato",
    "voy a matarte",
    "te voy a violar",
    "te violo",
    "muérete", "muérete",
    "ojalá te mueras",
    "go kill yourself",
    "kill yourself",
    "kys",
    "i will kill",
    "i hate",          # Solo si acompañado de grupo → por regex
    ("regex", r"\b(matar|asesinar|violar|destruir|eliminar)\s+(a\s+)?(todos?\s+los?|las?\s+)\w+"),
    ("regex", r"\bod[ií]o\s+(a\s+)?(los?|las?)\s+\w+"),
]

# Agrupación de todas las categorías con su etiqueta
_CATEGORIAS: list[tuple[str, list]] = [
    ("insultos",   _INSULTOS_ES + _INSULTOS_EN),
    ("racismo",    _RACISMO),
    ("odio",       _ODIO_AMENAZAS),
]


# ------------------------------------------------------------------
# COMPILACIÓN DE PATRONES — se hace una sola vez al importar
# ------------------------------------------------------------------
def _compilar_patrones(lista: list) -> list[re.Pattern]:
    """Compila cada entrada en un Pattern de regex listo para buscar."""
    patrones = []
    for entrada in lista:
        if isinstance(entrada, tuple) and entrada[0] == "regex":
            # Expresión regular directa
            patrones.append(re.compile(entrada[1], re.IGNORECASE))
        else:
            # Palabra/frase: búsqueda de token completo
            escapada = re.escape(str(entrada))
            patrones.append(re.compile(rf"\b{escapada}\b", re.IGNORECASE))
    return patrones

_PATRONES_COMPILADOS: dict[str, list[re.Pattern]] = {
    categoria: _compilar_patrones(lista)
    for categoria, lista in _CATEGORIAS
}


# ------------------------------------------------------------------
# FUNCIÓN PÚBLICA PRINCIPAL
# ------------------------------------------------------------------
def verificar_consulta(texto: str) -> dict:
    """
    Analiza una consulta de usuario y determina si es apropiada.

    Proceso:
      1. Normaliza el texto (elimina evasiones comunes).
      2. Busca patrones de cada categoría en el texto normalizado.
      3. Devuelve un dict con el veredicto y, si procede, el motivo.

    Args:
        texto : Consulta del usuario tal cual la introdujo.

    Returns:
        {
            "aceptado" : bool,
            "categoria": str | None,   # 'insultos' | 'racismo' | 'odio'
            "mensaje"  : str           # Respuesta amigable para mostrar al usuario
        }
    """
    if not texto or not texto.strip():
        return {
            "aceptado" : False,
            "categoria": None,
            "mensaje"  : "Por favor, introduce una pregunta válida."
        }

    texto_norm = _normalizar(texto)

    for categoria, patrones in _PATRONES_COMPILADOS.items():
        for patron in patrones:
            if patron.search(texto_norm):
                return {
                    "aceptado" : False,
                    "categoria": categoria,
                    "mensaje"  : _mensaje_rechazo(categoria)
                }

    return {
        "aceptado" : True,
        "categoria": None,
        "mensaje"  : ""
    }


def _mensaje_rechazo(categoria: str) -> str:
    """Devuelve un mensaje de rechazo amigable según la categoría."""
    mensajes = {
        "insultos": (
            "Tu mensaje contiene lenguaje inapropiado. "
            "Por favor, reformula tu pregunta de manera respetuosa."
        ),
        "racismo": (
            "Tu mensaje contiene lenguaje discriminatorio o racista. "
            "Este chatbot promueve el respeto y la igualdad. "
            "Por favor, reformula tu consulta."
        ),
        "odio": (
            "Tu mensaje contiene lenguaje amenazante o de odio. "
            "Por favor, mantén un tono respetuoso."
        ),
    }
    return mensajes.get(
        categoria,
        "Tu mensaje no cumple las normas de uso. Por favor, reformúlalo."
    )


# ------------------------------------------------------------------
# UTILIDAD ADICIONAL — Censurar texto de salida si fuera necesario
# ------------------------------------------------------------------
def censurar_texto(texto: str) -> str:
    """
    Reemplaza palabras marcadas como inapropiadas en un texto de salida
    con asteriscos, manteniendo la longitud visual.

    Útil para sanitizar fragmentos recuperados del corpus que pudieran
    contener lenguaje inadecuado en el texto fuente.

    Args:
        texto : Texto a censurar.

    Returns:
        Texto con palabras inapropiadas reemplazadas por '***'.
    """
    resultado = texto
    for categoria, patrones in _PATRONES_COMPILADOS.items():
        for patron in patrones:
            resultado = patron.sub("***", resultado)
    return resultado
