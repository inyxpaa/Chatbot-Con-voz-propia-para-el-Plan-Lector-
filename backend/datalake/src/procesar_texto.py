import re
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
raw_dir = base_dir / "raw"
processed_dir = base_dir / "processed"

raw_dir.mkdir(parents=True, exist_ok=True)
processed_dir.mkdir(parents=True, exist_ok=True)

input_file = raw_dir / "convozpropia_raw.txt"
output_file = processed_dir / "convozpropia_chunks.txt"

def procesar():
    if not input_file.exists():
        print(f"No se encontró {input_file}. Ejecuta scrapear_web.py primero.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        texto = f.read()

    # Dividir el texto en los diferentes artículos/páginas
    articulos = texto.split("\n==================================\n")
    
    chunks_finales = []
    
    # Parámetros para agrupar frases y mantener contexto local
    FRASES_POR_CHUNK = 4 # Grupos de 4 frases
    OVERLAP = 1 # Solapamiento de 1 frase entre chunks

    for articulo in articulos:
        articulo = articulo.strip()
        if not articulo:
            continue
            
        # Extraer meta información
        lineas = articulo.split("\n")
        fuente = ""
        url = ""
        contenido = []
        for linea in lineas:
            if linea.startswith("FUENTE:"):
                fuente = linea.replace("FUENTE:", "").strip()
            elif linea.startswith("URL:"):
                url = linea.replace("URL:", "").strip()
            else:
                contenido.append(linea)
                
        texto_limpio = " ".join(contenido).strip()
        # Normalizar espacios
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
        
        # Dividir por puntos
        # Consideramos '.' seguido de espacio o final de string para evitar partir números o abreviaturas simples
        frases = re.split(r'\.\s*', texto_limpio)
        frases = [f.strip() + "." for f in frases if f.strip() and len(f.strip()) > 5] # Frases válidas
        
        # Agrupar las frases en chunks con overlap
        if not frases:
            continue
            
        for i in range(0, len(frases), FRASES_POR_CHUNK - OVERLAP):
            grupo = frases[i : i + FRASES_POR_CHUNK]
            texto_chunk = " ".join(grupo)
            
            # Formatear el chunk con sus metadatos
            chunk_final = f"[FUENTE: {fuente}]\n[URL: {url}]\n{texto_chunk}"
            chunks_finales.append(chunk_final)
            
            if i + FRASES_POR_CHUNK >= len(frases):
                break

    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in chunks_finales:
            f.write(chunk + "\n---\n")

    print(f"Procesamiento completado. Total de chunks generados: {len(chunks_finales)}")
    print(f"Guardado en {output_file}")

if __name__ == "__main__":
    procesar()