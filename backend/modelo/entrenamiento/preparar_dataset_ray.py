"""
==============================================================
  preparar_dataset_ray.py — Preprocesamiento del datalake
==============================================================
  Lee los archivos JSONL del datalake de fine-tuning y los
  convierte a Parquet tokenizado, listo para Ray Data.

  NOTA: Este paso es OPCIONAL.
  El script train_ray_qwen.py puede leer los JSONL directamente.
  Usa este script si quieres pre-tokenizar y ahorrar tiempo
  al lanzar múltiples experimentos.

  Uso:
      python preparar_dataset_ray.py
==============================================================
"""

import os
import json
import pandas as pd
from transformers import AutoTokenizer

# ------------------------------------------------------------------
# RUTAS
# ------------------------------------------------------------------
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_SCRIPT_DIR))

TRAIN_JSONL  = os.path.join(_BACKEND_DIR, "datalake", "finetuning", "train.jsonl")
EVAL_JSONL   = os.path.join(_BACKEND_DIR, "datalake", "finetuning", "eval.jsonl")
OUTPUT_DIR   = os.path.join(_SCRIPT_DIR, "data_preprocessed")

MODEL_NAME   = "Qwen/Qwen2.5-1.5B-Instruct"
BLOCK_SIZE   = 2048


def cargar_jsonl(ruta: str) -> list[dict]:
    """Lee un archivo JSONL y devuelve una lista de diccionarios."""
    ejemplos = []
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                ejemplos.append(json.loads(linea))
    return ejemplos


def aplicar_chat_template(ejemplos: list[dict], tokenizer) -> list[str]:
    """
    Convierte cada ejemplo {"messages": [...]} al formato de texto
    usando el template oficial de Qwen2.5-Instruct.
    """
    textos = []
    for item in ejemplos:
        mensajes = item.get("messages", [])
        try:
            texto = tokenizer.apply_chat_template(
                mensajes,
                tokenize=False,
                add_generation_prompt=False,
            )
        except Exception:
            # Fallback manual
            partes = []
            for msg in mensajes:
                role    = msg.get("role", "user")
                content = msg.get("content", "")
                partes.append(f"<|im_start|>{role}\n{content}<|im_end|>")
            texto = "\n".join(partes)
        textos.append(texto)
    return textos


def procesar_y_guardar(
    ejemplos_texto: list[str],
    tokenizer,
    block_size: int,
    ruta_salida: str,
    nombre_split: str,
) -> int:
    """
    Tokeniza la lista de textos, agrupa en bloques de longitud fija
    y guarda a Parquet.
    Devuelve el número de bloques generados.
    """
    bloques = []

    for texto in ejemplos_texto:
        ids = tokenizer.encode(texto, add_special_tokens=False)
        for i in range(0, len(ids) - block_size + 1, block_size):
            bloques.append({"input_ids": ids[i : i + block_size]})

    if not bloques:
        print(f"[!] {nombre_split}: No se generaron bloques con BLOCK_SIZE={block_size}.")
        return 0

    df = pd.DataFrame(bloques)
    df.to_parquet(ruta_salida, engine="pyarrow", index=False)
    print(f"[✓] {nombre_split}: {len(bloques)} bloques → {ruta_salida}")
    return len(bloques)


def main():
    print("=" * 60)
    print("  PREPARACIÓN DE DATASET PARA RAY TRAIN")
    print("=" * 60)

    # Verificar archivos de entrada
    for ruta in [TRAIN_JSONL, EVAL_JSONL]:
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"[!] No se encontró: {ruta}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Cargar tokenizador
    print(f"\nCargando tokenizador: {MODEL_NAME} ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Procesar split de entrenamiento
    print("\n[→] Procesando train.jsonl ...")
    train_raw  = cargar_jsonl(TRAIN_JSONL)
    train_txt  = aplicar_chat_template(train_raw, tokenizer)
    n_train    = procesar_y_guardar(
        train_txt, tokenizer, BLOCK_SIZE,
        os.path.join(OUTPUT_DIR, "train.parquet"),
        "Train"
    )

    # Procesar split de evaluación
    print("\n[→] Procesando eval.jsonl ...")
    eval_raw   = cargar_jsonl(EVAL_JSONL)
    eval_txt   = aplicar_chat_template(eval_raw, tokenizer)
    n_eval     = procesar_y_guardar(
        eval_txt, tokenizer, BLOCK_SIZE,
        os.path.join(OUTPUT_DIR, "eval.parquet"),
        "Eval"
    )

    # Resumen
    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print(f"  Ejemplos originales en train : {len(train_raw)}")
    print(f"  Bloques tokenizados en train : {n_train}")
    print(f"  Ejemplos originales en eval  : {len(eval_raw)}")
    print(f"  Bloques tokenizados en eval  : {n_eval}")
    print(f"  Longitud de bloque (tokens)  : {BLOCK_SIZE}")
    print(f"  Directorio de salida         : {OUTPUT_DIR}")
    print("\n  ✅ Dataset listo para Ray Train.")
    print("     Para usarlo, cambia TRAIN_JSONL/EVAL_JSONL en")
    print("     train_ray_qwen.py por las rutas de los Parquet.")


if __name__ == "__main__":
    main()
