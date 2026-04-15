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

# IMPORTANTE: Establecer antes de importar torch.distributed
import os
os.environ["USE_LIBUV"] = "0"        # TCPStore sin libuv (PyTorch Windows build)
os.environ["PYTHONIOENCODING"] = "utf-8"  # Encoding correcto en consola Windows
import torch
import ray
import ray.train
from ray.train import ScalingConfig, RunConfig, CheckpointConfig
from ray.train.torch import TorchTrainer, TorchConfig
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

import json

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
NUM_WORKERS = 1          # Ajustar al número de GPUs disponibles (1 GPU local)
BLOCK_SIZE  = 512        # Reducido para ahorrar VRAM en una sola GPU
EPOCHS      = 3
BATCH_SIZE  = 1          # Reducido para una sola GPU
GRAD_ACCUM  = 8          # Batch efectivo = 1 * 8 * 1 GPU = 8


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
    Tokeniza TODOS los textos, los concatena en una sola secuencia y los
    parte en bloques de longitud fija (block_size).
    Esto garantiza que ningún ejemplo se descarte por ser demasiado corto.
    Para Causal LM, input_ids == labels (HuggingFace desplaza los labels internamente).
    """
    # 1. Tokenizar todos los ejemplos y concatenar en una única secuencia
    todos_ids: list[int] = []
    eos_id = tokenizer.eos_token_id or 0
    for texto in ejemplos_texto:
        ids = tokenizer.encode(texto, add_special_tokens=False)
        todos_ids.extend(ids)
        todos_ids.append(eos_id)  # separador entre conversaciones

    # 2. Partir en bloques de block_size (descartar el residuo final)
    bloques_ids = [
        todos_ids[i : i + block_size]
        for i in range(0, len(todos_ids) - block_size + 1, block_size)
    ]

    if not bloques_ids:
        # Si la secuencia completa es más corta que block_size, usar todo lo que hay
        # con padding al tamaño máximo para no perder datos
        pad_id = tokenizer.pad_token_id or eos_id
        bloque = todos_ids[:block_size]
        bloque += [pad_id] * (block_size - len(bloque))
        bloques_ids = [bloque]

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
    # Necesario para gradient checkpointing + LoRA: asegura que los inputs
    # de la capa de embedding tengan grad_fn aunque el modelo base esté congelado.
    model.enable_input_require_grads()

    if rank == 0:
        model.print_trainable_parameters()

    # ---- 6. Argumentos de entrenamiento ----
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=2e-4,
        num_train_epochs=epochs,
        eval_strategy="epoch",
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

    # Variables de entorno que deben propagarse a TODOS los workers de Ray
    _ray_env = {
        "USE_LIBUV": "0",
        "PYTHONIOENCODING": "utf-8",
    }

    # Intentar conectar al cluster Ray externo; si no existe, arrancar en modo local
    try:
        ray.init(address="auto", runtime_env={"env_vars": _ray_env})
        print(f"[OK] Conectado al cluster Ray externo: {ray.cluster_resources()}")
    except Exception:
        ray.init(runtime_env={"env_vars": _ray_env})  # Modo local
        print(f"[OK] Ray iniciado en modo LOCAL: {ray.cluster_resources()}")

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

    # Configuración de escalado: NUM_WORKERS GPUs
    import torch as _torch
    _gpu_available = _torch.cuda.is_available()
    scaling_config = ScalingConfig(
        num_workers=NUM_WORKERS,
        use_gpu=_gpu_available,
        resources_per_worker={"GPU": 1 if _gpu_available else 0, "CPU": 4},
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
    # backend="gloo": único backend distribuido disponible en Windows
    # (NCCL solo funciona en Linux; gloo soporta GPU en modo single-node)
    torch_config = TorchConfig(backend="gloo")

    trainer = TorchTrainer(
        train_loop_per_worker=train_loop_per_worker,
        train_loop_config=train_config,
        scaling_config=scaling_config,
        run_config=run_config,
        torch_config=torch_config,
    )

    print("\n[→] Lanzando entrenamiento distribuido en el cluster Ray...\n")
    resultado = trainer.fit()

    print("\n" + "=" * 60)
    print("  ENTRENAMIENTO COMPLETADO")
    print("=" * 60)
    print(f"  Métricas finales : {resultado.metrics}")
    print(f"  Mejor checkpoint : {resultado.checkpoint}")
    print(f"  Modelo guardado  : {OUTPUT_DIR}")
