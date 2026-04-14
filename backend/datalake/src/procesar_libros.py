import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import re
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
raw_dir   = base_dir / "raw"
processed_dir = base_dir / "processed"
processed_dir.mkdir(parents=True, exist_ok=True)

NUEVOS_RAW = [
    raw_dir / "plan_lector_raw.txt",
    raw_dir / "resumenes_libros_raw.txt",
]

output_file = processed_dir / "convozpropia_chunks.txt"

FRASES_POR_CHUNK = 4
OVERLAP = 1


def chunkar_articulo(fuente: str, url: str, texto: str) -> list[str]:
    texto_limpio = re.sub(r'\s+', ' ', texto).strip()
    frases = re.split(r'\.\s+', texto_limpio)
    frases = [f.strip() + "." for f in frases if f.strip() and len(f.strip()) > 5]

    if not frases:
        return []

    chunks = []
    i = 0
    while i < len(frases):
        grupo = frases[i: i + FRASES_POR_CHUNK]
        texto_chunk = " ".join(grupo)
        chunk_final = f"[FUENTE: {fuente}]\n[URL: {url}]\n{texto_chunk}"
        chunks.append(chunk_final)
        i += FRASES_POR_CHUNK - OVERLAP
        if i + FRASES_POR_CHUNK > len(frases) and i < len(frases):
            grupo = frases[i:]
            texto_chunk = " ".join(grupo)
            chunk_final = f"[FUENTE: {fuente}]\n[URL: {url}]\n{texto_chunk}"
            chunks.append(chunk_final)
            break

    return chunks


def procesar_fichero_plano(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        contenido = f.read().strip()

    fuente = path.stem
    url = "documento_interno"
    lineas = contenido.split("\n")
    texto_lineas = []
    for linea in lineas:
        if linea.startswith("FUENTE:"):
            fuente = linea.replace("FUENTE:", "").strip()
        elif linea.startswith("URL:"):
            url = linea.replace("URL:", "").strip()
        else:
            texto_lineas.append(linea)

    texto = " ".join(texto_lineas)
    return chunkar_articulo(fuente, url, texto)


def procesar_fichero_multi(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        contenido = f.read()

    articulos = contenido.split("\n\n==================================\n\n")
    todos_los_chunks = []

    for articulo in articulos:
        articulo = articulo.strip()
        if not articulo:
            continue

        lineas = articulo.split("\n")
        fuente = path.stem
        url = "documento_interno"
        texto_lineas = []

        for linea in lineas:
            if linea.startswith("FUENTE:"):
                fuente = linea.replace("FUENTE:", "").strip()
            elif linea.startswith("URL:"):
                url = linea.replace("URL:", "").strip()
            elif linea.startswith("AUTOR:") or linea.startswith("CURSO/DEPARTAMENTO:"):
                texto_lineas.append(linea)
            else:
                texto_lineas.append(linea)

        texto = " ".join(texto_lineas)
        chunks = chunkar_articulo(fuente, url, texto)
        todos_los_chunks.extend(chunks)

    return todos_los_chunks


nuevos_chunks = []

for raw_path in NUEVOS_RAW:
    if not raw_path.exists():
        print(f"AVISO: No encontrado: {raw_path}. Saltando...")
        continue

    print(f"Procesando: {raw_path.name}")

    if "resumenes" in raw_path.name:
        chunks = procesar_fichero_multi(raw_path)
    else:
        chunks = procesar_fichero_plano(raw_path)

    print(f"  {len(chunks)} chunks generados")
    nuevos_chunks.extend(chunks)

with open(output_file, "a", encoding="utf-8") as f:
    for chunk in nuevos_chunks:
        f.write(chunk + "\n---\n")

print(f"Anadidos {len(nuevos_chunks)} nuevos chunks a: {output_file}")
