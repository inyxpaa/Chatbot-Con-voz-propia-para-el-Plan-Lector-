# Dataset de Fine-Tuning — Plan Lector Con Voz Propia

## Descripcion
Dataset generado para fine-tuning supervisado (SFT) del chatbot del IES Comercio.

## Estadisticas
- **Total de ejemplos:** 231
- **Train:** 207 ejemplos
- **Eval:** 24 ejemplos

## Formato
Cada linea del fichero JSONL contiene un objeto con la estructura de mensajes de chat:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user",   "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

## Ficheros
- `dataset_finetuning.jsonl` — Dataset completo
- `train.jsonl` — 90% para entrenamiento
- `eval.jsonl`  — 10% para evaluacion

## Uso con Ray Train

```python
import ray
from ray.train.huggingface import TransformersTrainer
from datasets import load_dataset

ds_train = load_dataset("json", data_files="train.jsonl", split="train")
ds_eval  = load_dataset("json", data_files="eval.jsonl",  split="train")
```

## Categorias de ejemplos
1. **Libros del Plan Lector** — argumento, personajes, autor, temas, actividades (120)
2. **Plan Lector** — objetivos, metodologia, departamentos, actividades (11)
3. **Web del instituto** — actividades, concursos y eventos (100)
