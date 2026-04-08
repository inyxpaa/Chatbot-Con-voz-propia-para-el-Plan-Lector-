from pathlib import Path

base_dir = Path("datalake")
raw_dir = base_dir / "raw"
processed_dir = base_dir / "processed"
artifacts_dir = base_dir / "artifacts"

raw_dir.mkdir(parents=True, exist_ok=True)
processed_dir.mkdir(parents=True, exist_ok=True)
artifacts_dir.mkdir(parents=True, exist_ok=True)

input_file = raw_dir / "EL QUIJOTE.txt"
output_file = processed_dir / "quijote_chunks.txt"

with open(input_file, "r", encoding="utf-8") as f:
    texto = f.read()

texto_limpio = texto.replace("\n", " ").strip()
chunks = [texto_limpio[i:i+1000] for i in range(0, len(texto_limpio), 1000)]

with open(output_file, "w", encoding="utf-8") as f:
    for chunk in chunks:
        f.write(chunk + "\n---\n")