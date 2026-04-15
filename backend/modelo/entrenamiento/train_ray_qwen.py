"""
==============================================================
  train_ray_qwen.py — Fine-Tuning Distribuido con Ray Train
==============================================================
  Entrenamiento distribuido de Qwen2.5-1.5B-Instruct usando
  Ray Train (TorchTrainer) + HuggingFace Trainer + QLoRA.

  Cluster: 4 nodos (1 master + 3 workers), 1 GPU por nodo.
  Dataset: backend/datalake/finetuning/train.jsonl y eval.jsonl
  Formato:  {"messages": [{"role": ..., "content": ...}]}

  Ejecución (desde el nodo master, con el cluster Ray activo):
      python train_ray_qwen.py
==============================================================
"""

import os
import json
import torch
import ray
import ray.train
from ray.train import ScalingConfig, RunConfig, CheckpointConfig
from ray.train.torch import TorchTrainer
from ray.train.huggingface.transformers import (
    prepare_trainer,
    RayTrainReportCallback,
)

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import get_peft_model, LoraConfig, TaskType
from datasets import Dataset

# ------------------------------------------------------------------
# RUTAS — se calculan relativas a la ubicación de este script
# ------------------------------------------------------------------
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_SCRIPT_DIR))   # backend/

TRAIN_JSONL  = os.path.join(_BACKEND_DIR, "datalake", "finetuning", "train.jsonl")
EVAL_JSONL   = os.path.join(_BACKEND_DIR, "datalake", "finetuning", "eval.jsonl")
OUTPUT_DIR   = os.path.join(_SCRIPT_DIR, "output", "qwen_finetuned")

# ------------------------------------------------------------------
# PARÁMETROS GLOBALES
# ------------------------------------------------------------------
MODEL_NAME  = "Qwen/Qwen2.5-1.5B-Instruct"
NUM_WORKERS = 4          # 1 master + 3 workers = 4 GPUs en total
BLOCK_SIZE  = 2048       # Longitud máxima del contexto (Qwen2.5 soporta hasta 32k)
EPOCHS      = 3
BATCH_SIZE  = 2          # Por dispositivo (GPU de 12 GB)
GRAD_ACCUM  = 4          # Batch efectivo = 2 * 4 * 4 GPUs = 32


# ==================================================================
# FUNCIONES AUXILIARES
# ==================================================================

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
    El token <|im_end|> actúa como separador de turno.
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
            # Fallback manual si el tokenizador no tiene template
            partes = []
            for msg in mensajes:
                role    = msg.get("role", "user")
                content = msg.get("content", "")
                partes.append(f"<|im_start|>{role}\n{content}<|im_end|>")
            texto = "\n".join(partes)
        textos.append(texto)
    return textos


def tokenizar_dataset(
    ejemplos_texto: list[str],
    tokenizer,
    block_size: int,
) -> Dataset:
    """
    Tokeniza la lista de textos y los agrupa en bloques de longitud fija.
    Para Causal LM, input_ids == labels (HuggingFace desplaza los labels internamente).
    """
    bloques_ids = []

    for texto in ejemplos_texto:
        ids = tokenizer.encode(texto, add_special_tokens=False)
        # Agrupar en bloques de block_size
        for i in range(0, len(ids) - block_size + 1, block_size):
            bloques_ids.append(ids[i : i + block_size])

    if not bloques_ids:
        raise ValueError(
            f"[!] No se generaron bloques. "
            f"Comprueba que el dataset tiene texto y BLOCK_SIZE={block_size} es adecuado."
        )

    return Dataset.from_dict({"input_ids": bloques_ids})


# ==================================================================
# FUNCIÓN DE ENTRENAMIENTO — se ejecuta en CADA worker del cluster
# ==================================================================

def train_loop_per_worker(config: dict):
    """
    Esta función es lanzada por Ray Train en cada nodo/GPU del cluster.
    Ray gestiona automáticamente el DDP (DistributedDataParallel) y la
    sincronización de gradientes entre workers.
    """
    # ---- 1. Leer configuración desde el dict pasado por TorchTrainer ----
    model_name  = config["model_name"]
    train_path  = config["train_jsonl"]
    eval_path   = config["eval_jsonl"]
    output_dir  = config["output_dir"]
    block_size  = config["block_size"]
    epochs      = config["epochs"]
    batch_size  = config["batch_size"]
    grad_accum  = config["grad_accum"]

    rank = ray.train.get_context().get_world_rank()
    print(f"[Rank {rank}] Worker iniciado. Cargando tokenizador...")

    # ---- 2. Tokenizador ----
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ---- 3. Cargar y preparar dataset ----
    print(f"[Rank {rank}] Cargando dataset desde {train_path} ...")
    train_raw  = cargar_jsonl(train_path)
    eval_raw   = cargar_jsonl(eval_path)

    train_txt  = aplicar_chat_template(train_raw, tokenizer)
    eval_txt   = aplicar_chat_template(eval_raw,  tokenizer)

    train_ds   = tokenizar_dataset(train_txt, tokenizer, block_size)
    eval_ds    = tokenizar_dataset(eval_txt,  tokenizer, block_size)

    # Data Parallelism: cada worker toma su shard del dataset
    world_size = ray.train.get_context().get_world_size()
    train_ds   = train_ds.shard(num_shards=world_size, index=rank)
    eval_ds    = eval_ds.shard(num_shards=world_size,  index=rank)

    print(f"[Rank {rank}] Dataset: {len(train_ds)} bloques de entrenamiento, "
          f"{len(eval_ds)} de evaluación.")

    # ---- 4. Cargar modelo base en BF16 ----
    print(f"[Rank {rank}] Inicializando modelo {model_name} ...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        use_cache=False,  # Necesario para gradient checkpointing
    )

    # ---- 5. Aplicar QLoRA (PEFT) ----
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)

    if rank == 0:
        model.print_trainable_parameters()

    # ---- 6. Argumentos de entrenamiento ----
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=2e-4,
        num_train_epochs=epochs,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_steps=10,
        bf16=True,                      # Aceleración nativa RTX 40xx
        gradient_checkpointing=True,    # Reduce VRAM significativamente
        report_to="none",               # Ray Train gestiona el reporting
        dataloader_pin_memory=False,    # Evitar problemas de memoria en Ray
        # Importante: no usar ddp_find_unused_parameters con QLoRA
        ddp_find_unused_parameters=False,
    )

    # ---- 7. Data Collator ----
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM, no Masked LM
    )

    # ---- 8. Crear el Trainer de HuggingFace ----
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    # ---- 9. Integrar Ray Train con HuggingFace Trainer ----
    # prepare_trainer añade el callback RayTrainReportCallback y configura
    # el entorno DDP para que Ray gestione la sincronización entre workers.
    trainer = prepare_trainer(trainer)

    # ---- 10. Entrenamiento ----
    print(f"[Rank {rank}] Iniciando Fine-Tuning Distribuido...")
    trainer.train()

    # ---- 11. Guardar modelo — solo el nodo master (rank 0) ----
    if rank == 0:
        print(f"[Rank 0] Guardando modelo en {output_dir} ...")
        os.makedirs(output_dir, exist_ok=True)
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        print(f"[Rank 0] ✅ Modelo guardado correctamente en {output_dir}")


# ==================================================================
# PUNTO DE ENTRADA — ORQUESTADOR (se ejecuta en el nodo master)
# ==================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ORQUESTADOR RAY — ENTRENAMIENTO CHATBOT CON VOZ PROPIA")
    print("=" * 60)

    # Verificar que existen los archivos de datos antes de empezar
    for ruta in [TRAIN_JSONL, EVAL_JSONL]:
        if not os.path.exists(ruta):
            raise FileNotFoundError(
                f"[!] No se encontró el archivo de datos: {ruta}\n"
                f"    Asegúrate de haber ejecutado el pipeline del datalake primero."
            )

    print(f"[✓] Dataset de entrenamiento : {TRAIN_JSONL}")
    print(f"[✓] Dataset de evaluación    : {EVAL_JSONL}")
    print(f"[✓] Directorio de salida     : {OUTPUT_DIR}")
    print(f"[✓] Workers Ray              : {NUM_WORKERS}")
    print()

    # Conectar al cluster Ray que ya está corriendo en los 4 nodos
    # Si Ray no está activo en el nodo, usa ray.init() sin argumentos (modo local)
    ray.init(address="auto")
    print(f"[✓] Conectado al cluster Ray: {ray.cluster_resources()}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Configuración pasada a cada worker
    train_config = {
        "model_name" : MODEL_NAME,
        "train_jsonl": TRAIN_JSONL,
        "eval_jsonl" : EVAL_JSONL,
        "output_dir" : OUTPUT_DIR,
        "block_size" : BLOCK_SIZE,
        "epochs"     : EPOCHS,
        "batch_size" : BATCH_SIZE,
        "grad_accum" : GRAD_ACCUM,
    }

    # Configuración de escalado: 4 workers, 1 GPU cada uno
    scaling_config = ScalingConfig(
        num_workers=NUM_WORKERS,
        use_gpu=True,
        resources_per_worker={"GPU": 1, "CPU": 4},
    )

    # Configuración de ejecución y checkpoints
    run_config = RunConfig(
        name="qwen_finetuning_run",
        storage_path=os.path.join(OUTPUT_DIR, "ray_checkpoints"),
        checkpoint_config=CheckpointConfig(
            num_to_keep=2,  # Mantener los 2 mejores checkpoints
        ),
    )

    # Crear y lanzar el TorchTrainer de Ray
    trainer = TorchTrainer(
        train_loop_per_worker=train_loop_per_worker,
        train_loop_config=train_config,
        scaling_config=scaling_config,
        run_config=run_config,
    )

    print("\n[→] Lanzando entrenamiento distribuido en el cluster Ray...\n")
    resultado = trainer.fit()

    print("\n" + "=" * 60)
    print("  ENTRENAMIENTO COMPLETADO")
    print("=" * 60)
    print(f"  Métricas finales : {resultado.metrics}")
    print(f"  Mejor checkpoint : {resultado.checkpoint}")
    print(f"  Modelo guardado  : {OUTPUT_DIR}")
