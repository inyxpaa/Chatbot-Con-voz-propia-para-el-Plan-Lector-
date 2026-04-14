"""
==============================================================
  train_spark_qwen.py — Fine-Tuning Distribuido en Spark
==============================================================
  Este script configura un entrenamiento distribuido de un LLM
  (Qwen2.5-1.5B) sobre el cluster Spark con 4 nodos (RTX 4070).
  Utiliza Horovod para sincronizar gradientes Multi-GPU y
  QLoRA (PEFT) para poder entrenar el modelo en GPUs de 12GB.
==============================================================
"""

import os
import torch
from pyspark.sql import SparkSession

import horovod.torch as hvd
from horovod.spark.torch import run

from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import get_peft_model, LoraConfig, TaskType
from datasets import Dataset

# ---------------------------------------------------------
# CONFIGURACIÓN DEL MODELO Y RUTAS
# ---------------------------------------------------------
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = "file://" + os.path.join(BASE_DIR, "data", "dataset_entrenamiento", "dataset_chunks.parquet")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "modelo_finetuned")


def train_fn():
    """
    Esta función es el worker PyTorch, será ejecutada distribuidamente 
    por Horovod en cada nodo/GPU del cluster.
    """
    # 1. Iniciar Horovod adentro del worker
    hvd.init()
    
    # 2. Asignar cada proceso a una GPU concreta para evitar colisiones
    if torch.cuda.is_available():
        torch.cuda.set_device(hvd.local_rank())
    
    # 3. Cargar Tokenizador y Dataset Local
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    print(f"[Rank {hvd.rank()}] Cargando dataset desde {DATASET_PATH} ...")
    # Datasets de HuggingFace carga nativamente Parquet de forma eficiente
    dataset = Dataset.from_parquet(DATASET_PATH)
    
    # Dividir secuencialmente el dataset para cada worker (Data Parallelism)
    # Ejemplo: Si hay 4 GPUs, el rank 0 coge el 1er cuarto, el rank 1 el 2do...
    worker_dataset = dataset.shard(num_shards=hvd.size(), index=hvd.rank())
    
    # 4. Cargar modelo base con BF16 (nativo en RTX 4070)
    # Se deshabilita use_cache ya que interfiere con el entrenamiento de gradientes
    print(f"[Rank {hvd.rank()}] Inicializando modelo Qwen 1.5B ...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        use_cache=False
    )
    
    # 5. Configurar LoRA (Low-Rank Adaptation)
    # Esto reduce los pesos entrenables a un <1%, permitiendo entrenar en los 12GB de VRAM
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    model = get_peft_model(model, peft_config)
    
    if hvd.rank() == 0:
        model.print_trainable_parameters()
        
    # 6. Preparar argumentos de entrenamiento
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,        # Ajustar según memoria (2 o 4 máximo)
        gradient_accumulation_steps=4,        # Batch Size Efectivo = 2 * 4 * NumGPUs
        learning_rate=2e-4,
        num_train_epochs=3,
        logging_steps=10,
        save_steps=100,
        bf16=True,                            # Aceleración por hardware para RTX 40 Series
        gradient_checkpointing=True,          # Ahorra muchísima VRAM
        report_to="none",
        # Parámetros para integración nativa con Horovod (HuggingFace detecta HVD)
        # Solo se requiere que local_rank no estorbe.
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=worker_dataset,
        data_collator=data_collator,
    )
    
    # Configurar el backend PyTorch DDP interno para usar el wrap de Horovod, o dejar
    # que Trainer maneje DDP estándar. HuggingFace + Horovod funciona bien, pero 
    # añadiendo el optimizer distribuido es más manual.
    # El Trainer de HuggingFace requiere pequeñas modificaciones para Horovod,
    # pero aquí forzamos el uso de HorovodOptimizer.
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=training_args.learning_rate)
    optimizer = hvd.DistributedOptimizer(optimizer, named_parameters=model.named_parameters())
    hvd.broadcast_parameters(model.state_dict(), root_rank=0)
    hvd.broadcast_optimizer_state(optimizer, root_rank=0)

    # Inyectar el optimizer a HF Trainer
    trainer.optimizer = optimizer

    print(f"[Rank {hvd.rank()}] Iniciando Fine-Tuning Distribuido...")
    trainer.train()
    
    # Solo el nodo 0 (Master worker) guarda el modelo final
    if hvd.rank() == 0:
        print("Guardando el modelo ajustado ...")
        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        print(f"Modelo exitosamente guardado en {OUTPUT_DIR}")


# -------------------------------------------------------------
# PUNTO DE ENTRADA SPARK ORCHESTRATOR
# -------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  ORQUESTADOR SPARK — ENTRENAMIENTO CHATBOT")
    print("=" * 60)
    
    # Iniciar contexto Spark
    spark = SparkSession.builder \
        .appName("FineTuning_Qwen_Horovod") \
        .config("spark.task.cpus", "4") \
        .getOrCreate()
        
    num_workers = 3  # Número de nodos Worker con GPU en el cluster (tenías 3 Workers+1 Master)
    
    print(f"Lanzando horovod.spark.run en {num_workers} workers...")
    
    # Ejecutar la tarea PyTorch distribuida encapsulada en Spark
    run(train_fn, num_proc=num_workers, verbose=2)
    
    print("Proceso Spark terminado.")
    spark.stop()
