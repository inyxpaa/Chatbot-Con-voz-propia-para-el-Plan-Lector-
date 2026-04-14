import os
# Desactivar libuv antes de cualquier import de ray o torch
os.environ["USE_LIBUV"] = "0"
os.environ["RAY_NODE_IP_ADDRESS"] = "10.2.6.24"
os.environ["MASTER_ADDR"] = "10.2.6.24"

import ray
import torch
import pandas as pd

from ray.train import ScalingConfig
from ray.train.torch import TorchTrainer, TorchConfig
import ray.data as rd

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import get_peft_model, LoraConfig, TaskType

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_PATH = os.path.abspath(os.path.join(BASE_DIR, "train.jsonl"))
EVAL_PATH = os.path.abspath(os.path.join(BASE_DIR, "eval.jsonl"))
OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "modelo_finetuned"))

# ---------------------------------------------------------
# FORMATO CHAT → TEXTO
# ---------------------------------------------------------
def format_chat(example):
    text = ""
    for msg in example["messages"]:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            text += f"<|system|>\n{content}\n"
        elif role == "user":
            text += f"<|user|>\n{content}\n"
        elif role == "assistant":
            text += f"<|assistant|>\n{content}\n"
    return {"text": text}

# ---------------------------------------------------------
# FUNCIÓN DE ENTRENAMIENTO (se ejecuta en cada worker)
# ---------------------------------------------------------
def train_loop_per_worker(config):
    import os
    # Asegurar que el entorno del worker también tenga libuv desactivado
    os.environ["USE_LIBUV"] = "0"
    import ray.train as train

    # Obtener los shards de datos
    train_shard = train.get_dataset_shard("train")
    eval_shard = train.get_dataset_shard("eval")

    # Extraer de los shards como lista en python para evitar el uso de pandas por interno de Ray
    train_list = list(train_shard.iter_rows())
    eval_list = list(eval_shard.iter_rows())

    # Convertir a Dataset de Hugging Face
    train_hf = Dataset.from_list(train_list)
    eval_hf = Dataset.from_list(eval_list)

    # Formatear en texto
    train_hf = train_hf.map(format_chat)
    eval_hf = eval_hf.map(format_chat)

    # Tokenizador
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(example):
        return tokenizer(
            example["text"],
            truncation=True,
            padding="max_length",
            max_length=512,
        )

    train_hf = train_hf.map(tokenize, batched=True)
    eval_hf = eval_hf.map(tokenize, batched=True)

    train_hf.set_format(type="torch", columns=["input_ids", "attention_mask"])
    eval_hf.set_format(type="torch", columns=["input_ids", "attention_mask"])

    # Cargar modelo con LoRA
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        use_cache=False
    )
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # Argumentos de entrenamiento
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        logging_steps=10,
        save_steps=100,
        bf16=True,
        gradient_checkpointing=True,
        report_to="none",
        evaluation_strategy="steps",
        eval_steps=50,
    )
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_hf,
        eval_dataset=eval_hf,
        data_collator=data_collator,
    )
    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Conectando a Ray...")
    # Propagar variables a todos los workers y al controlador
    # Propagar variables a todos los workers y al controlador
    # Forzamos MASTER_ADDR y RAY_NODE_IP_ADDRESS para evitar conflictos con interfaces virtuales
    ray.init(address="auto", runtime_env={
        "env_vars": {
            "USE_LIBUV": "0",
            "RAY_TRAIN_WORKER_GROUP_START_TIMEOUT_S": "300",
            "MASTER_ADDR": "10.2.6.24",
            "RAY_NODE_IP_ADDRESS": "10.2.6.24"
        }
    })

    # Verificar archivos locales (solo head node)
    if not os.path.exists(TRAIN_PATH):
        raise FileNotFoundError(f"No se encuentra {TRAIN_PATH}")
    if not os.path.exists(EVAL_PATH):
        raise FileNotFoundError(f"No se encuentra {EVAL_PATH}")

    print("📖 Cargando datasets en el nodo head y enviando a Ray...")
    import json
    # Cargamos con json estándar para evitar que pandas arroje problemas de versión
    with open(TRAIN_PATH, 'r', encoding='utf-8') as f:
        train_data = [json.loads(line) for line in f]
    with open(EVAL_PATH, 'r', encoding='utf-8') as f:
        eval_data = [json.loads(line) for line in f]
    
    train_ds = rd.from_items(train_data)
    eval_ds = rd.from_items(eval_data)

    print("🔥 Iniciando entrenamiento distribuido...")
    trainer = TorchTrainer(
        train_loop_per_worker,
        scaling_config=ScalingConfig(
            num_workers=3,          # Usamos los 3 nodos workers dedicados
            use_gpu=True,
            resources_per_worker={"CPU": 2, "GPU": 1},
        ),
        torch_config=TorchConfig(backend="gloo"),   # Para Windows
        datasets={"train": train_ds, "eval": eval_ds},
    )
    result = trainer.fit()
    print("✅ Entrenamiento finalizado")