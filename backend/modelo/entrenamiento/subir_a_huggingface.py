"""
subir_a_huggingface.py
======================
Sube el adaptador LoRA fine-tuned (output/qwen_finetuned/) a Hugging Face Hub.

Uso:
    py -3.11 subir_a_huggingface.py

Requiere:
    - huggingface_hub instalado (ya está)
    - Token de HF con permisos de escritura (hf_xxxx...)
    - Haber ejecutado train_ray_qwen.py al menos una vez
"""

import os
from pathlib import Path
from huggingface_hub import HfApi, login

# ------------------------------------------------------------------
# CONFIGURACIÓN — edita estos valores antes de ejecutar
# ------------------------------------------------------------------

HF_TOKEN       = "hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # <-- tu token de HF (no lo subas a GitHub)
HF_USERNAME    = "inyxpa"
REPO_NAME      = "chatbot"

# Ruta local del modelo (relativa a este script)
_SCRIPT_DIR   = Path(__file__).parent
MODEL_DIR     = _SCRIPT_DIR / "output" / "qwen_finetuned"

# ------------------------------------------------------------------

REPO_ID = f"{HF_USERNAME}/{REPO_NAME}"

def main():
    print("=" * 60)
    print("  SUBIDA DEL ADAPTADOR LORA A HUGGING FACE HUB")
    print("=" * 60)

    if not MODEL_DIR.exists():
        raise FileNotFoundError(
            f"No se encontro la carpeta del modelo: {MODEL_DIR}\n"
            "Asegurate de haber ejecutado train_ray_qwen.py primero."
        )

    if HF_TOKEN.startswith("hf_XXXXX"):
        raise ValueError(
            "Edita HF_TOKEN en este script con tu token real de Hugging Face.\n"
            "Puedes obtenerlo en: https://huggingface.co/settings/tokens"
        )

    print(f"[1] Iniciando sesion en Hugging Face...")
    login(token=HF_TOKEN)

    api = HfApi()

    print(f"[2] Creando repositorio: {REPO_ID} ...")
    api.create_repo(
        repo_id=REPO_ID,
        repo_type="model",
        exist_ok=True,   # Si ya existe, no falla
        private=False,   # Cambia a True si quieres repo privado
    )
    print(f"    -> https://huggingface.co/{REPO_ID}")

    print(f"[3] Subiendo archivos desde: {MODEL_DIR}")
    print("    (se excluyen checkpoints intermedios y optimizer.pt)")

    # Archivos a excluir de la subida (pesados e innecesarios para inferencia)
    EXCLUIR = {
        "optimizer.pt",
        "rng_state.pth",
        "training_args.bin",
        "scheduler.pt",
    }
    EXCLUIR_DIRS = {"checkpoint-15", "checkpoint-30", "checkpoint-45", "ray_checkpoints"}

    archivos_subidos = 0
    for archivo in sorted(MODEL_DIR.rglob("*")):
        if not archivo.is_file():
            continue
        # Excluir checkpoints intermedios
        if any(d in archivo.parts for d in EXCLUIR_DIRS):
            continue
        if archivo.name in EXCLUIR:
            continue

        ruta_relativa = archivo.relative_to(MODEL_DIR)
        print(f"    Subiendo: {ruta_relativa} ({archivo.stat().st_size / 1024:.1f} KB)")

        api.upload_file(
            path_or_fileobj=str(archivo),
            path_in_repo=str(ruta_relativa).replace("\\", "/"),
            repo_id=REPO_ID,
            repo_type="model",
        )
        archivos_subidos += 1

    print()
    print("=" * 60)
    print(f"  SUBIDA COMPLETADA — {archivos_subidos} archivos")
    print("=" * 60)
    print(f"  Modelo disponible en:")
    print(f"  https://huggingface.co/{REPO_ID}")
    print()
    print("  Para usar el modelo en inferencia:")
    print(f"    from peft import PeftModel")
    print(f"    from transformers import AutoModelForCausalLM, AutoTokenizer")
    print(f"    base  = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct')")
    print(f"    model = PeftModel.from_pretrained(base, '{REPO_ID}')")


if __name__ == "__main__":
    main()
