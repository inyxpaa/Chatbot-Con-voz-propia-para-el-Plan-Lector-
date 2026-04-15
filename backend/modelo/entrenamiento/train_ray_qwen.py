"""
==============================================================
  train_ray_qwen.py — Fine-Tuning Distribuido en Ray Train
==============================================================
  Este script configura un entrenamiento distribuido de un LLM
  (Qwen 1.5B) usando el orquestador Ray Train, que provee un
  sistema DDP de PyTorch robusto sin necesidad de Horovod 
  para clusters HPC (Ej: 4 nodos con RTX 4070).
==============================================================
"""

import os
import torch
import ray
from ray.train import ScalingConfig
from ray.train.torch import TorchTrainer, get_device
from ray.train import get_context

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


def train_loop_per_worker(config):
    """
    Función que Ray mandará a cada Worker/GPU.
    Ray Train inicializa automáticamente el Distributed Data Parallel (DDP)
    de PyTorch en el entorno virtual, con lo que Transformers ya sabe qué hacer.
    """
    
    # 1. Averiguar quién soy yo en el cluster (0 para el "Master Worker")
    world_rank = get_context().get_world_rank()
    local_rank = get_context().get_local_rank()
    
    # El dispositivo nos lo proporciona mágicamente Ray
    device = get_device()
    
    print(f"[Worker Rank {world_rank}] Iniciando entorno sobre dispositivo {device}")
    
    # 2. Cargar Tokenizador
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    # 3. Cargar Dataset. HF Datasets y PyTorch DDP se repartirán el trabajo
    # internamente mediante DistributedSampler de PyTorch cuando el Trainer lo reciba.
    print(f"[Worker Rank {world_rank}] Cargando dataset desde Parquet ...")
    dataset = Dataset.from_parquet(DATASET_PATH)
    
    # 4. Cargar modelo base optimizado para Ampere (RTX 4070 = bfloat16)
    print(f"[Worker Rank {world_rank}] Configurando Qwen 1.5B ...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        use_cache=False
    )
    
    # Mover el modelo explícitamente a la GPU designada por Ray para este proceso
    model = model.to(device)
    
    # 5. Configuración QLoRA
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    model = get_peft_model(model, peft_config)
    
    if world_rank == 0:
        model.print_trainable_parameters()
        
    # 6. Preparar argumentos
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        num_train_epochs=3,
        logging_steps=10,
        save_steps=100,
        bf16=True,                          # Óptimo para RTX 4070
        gradient_checkpointing=True,        # Ahorra VRAM radicalmente
        report_to="none",
        ddp_find_unused_parameters=False,   # Optimización estándar para LoRA en DDP
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # El HF Trainer detectará que está dentro de un entorno PyTorch DDP 
    # autogestionado por Ray Train y se comportará de forma Multi-GPU.
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
    )
    
    print(f"[Worker Rank {world_rank}] Arrancando entrenamiento paralelo ...")
    trainer.train()
    
    # 7. Solo el nodo principal del entrenamiento debe guardar los pesos definitivos
    if world_rank == 0:
        print("Guardando el modelo ajustado ...")
        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        print(f"✅ Entrenamiento completado y guardado en {OUTPUT_DIR}")


# -------------------------------------------------------------
# ORQUESTADOR RAY START
# -------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  ORQUESTADOR RAY TRAIN — CHATBOT PLAN LECTOR")
    print("=" * 60)
    
    # 1. Conectarse al clúster existente. Si ya ejecutaste "ray start --head"
    # en este nodo y uniste los workers, Ray lo detectará con address="auto".
    # Importante: Si esto falla, ray lanzará un cluster mononodo en local temporalmente.
    ray.init(address="auto", ignore_reinit_error=True)
    
    print("Recursos Totales del Cluster Ray:", ray.cluster_resources())
    
    # 2. Configurar Escalado Distribuido
    # Tienes un master y 3 workers, o 4 RTX 4070 en total si usamos el master. 
    # Adaptaremos num_workers de forma dinámica según la disponibilidad real para no fallar:
    num_gpus_available = int(ray.cluster_resources().get("GPU", 0))
    # Para ser exactos y entrenarlo con 4 gráficas, o 3 según lo comentado antes:
    num_workers_to_use = max(num_gpus_available, 1) # Asegurarse de tener al menos 1
    
    print(f"Preparando ScalingConfig con {num_workers_to_use} PyTorch Workers (GPUs)...")
    
    scaling_config = ScalingConfig(
        num_workers=num_workers_to_use,
        use_gpu=(num_gpus_available > 0)
    )
    
    # 3. Empaquetarlo todo en el TorchTrainer
    trainer = TorchTrainer(
        train_loop_per_worker=train_loop_per_worker,
        scaling_config=scaling_config,
    )
    
    print("Ejecutando trainer.fit() ... el trabajo se repartirá automáticamente.")
    resultado = trainer.fit()
    
    print("Métricas Finales Recogidas por Ray:", resultado.metrics)
    print("¡Trabajo de entrenamiento terminado!")
    ray.shutdown()
