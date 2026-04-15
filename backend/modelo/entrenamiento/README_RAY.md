# Guía de entrenamiento distribuido con Ray Train

## Arquitectura del cluster

```
┌─────────────────────────────────────────────────────────┐
│  MASTER NODE  (ejecuta el script, tiene GPU)            │
│  ray start --head --port=6379                           │
│  python train_ray_qwen.py                               │
└───────────────────┬─────────────────────────────────────┘
                    │  Ray cluster
       ┌────────────┼────────────┐
       ▼            ▼            ▼
  WORKER 1      WORKER 2      WORKER 3
  GPU 0          GPU 0          GPU 0
  ray start     ray start     ray start
  --address     --address     --address
```

---

## Pasos para lanzar el entrenamiento

### Paso 1 — Instalar dependencias (solo la primera vez, en TODOS los nodos)

```bash
pip install ray[train]>=2.10.0 transformers>=4.40.1 peft>=0.10.0 \
            bitsandbytes>=0.43.1 accelerate>=0.29.3 datasets>=2.18.0 \
            pandas>=2.0.0 pyarrow>=15.0.0 torch
```

O ejecutar desde el directorio `backend/modelo/`:
```bash
pip install -r requirements.txt
```

---

### Paso 2 — Iniciar Ray en el nodo MASTER

Abrir una terminal en el nodo master y ejecutar:

```bash
ray start --head --port=6379 --dashboard-host=0.0.0.0
```

Se mostrará algo como:
```
Ray runtime started.
Next steps
  To connect to this Ray runtime from another node, run
    ray start --address='192.168.1.10:6379'
```

Anotar la IP del master (`192.168.1.10` en el ejemplo).

---

### Paso 3 — Iniciar Ray en los 3 nodos WORKER

En cada uno de los 3 workers, abrir una terminal y ejecutar:

```bash
ray start --address='<IP_DEL_MASTER>:6379'
```

Sustituir `<IP_DEL_MASTER>` por la IP real del nodo master.

---

### Paso 4 — Verificar que el cluster está completo (opcional pero recomendado)

Desde el master, verificar los recursos disponibles:

```bash
ray status
```

Debería mostrar 4 nodos activos y 4 GPUs disponibles.

También puedes acceder al **Ray Dashboard** desde el navegador:

```
http://<IP_DEL_MASTER>:8265
```

---

### Paso 5 — Ejecutar el entrenamiento desde el master

Navegar al directorio del script y lanzarlo:

```bash
cd "d:\IÑIGO\PROYECTO FINAL\backend\modelo\entrenamiento"
python train_ray_qwen.py
```

El script:
1. Se conecta al cluster Ray (`ray.init(address="auto")`)
2. Distribuye el entrenamiento en los 4 GPUs automáticamente
3. Muestra el progreso en la terminal y en el Ray Dashboard
4. Al terminar, guarda el modelo en `output/qwen_finetuned/`

---

## Estructura de archivos del entrenamiento

```
backend/modelo/entrenamiento/
├── train_ray_qwen.py          ← Script principal (este)
├── preparar_dataset_ray.py    ← Preprocesamiento opcional
├── output/
│   └── qwen_finetuned/        ← Modelo fine-tuned guardado aquí
│       ├── adapter_config.json
│       ├── adapter_model.bin
│       └── tokenizer files...
```

El dataset se lee directamente desde:
```
backend/datalake/finetuning/
├── train.jsonl   ← 187 ejemplos de entrenamiento
└── eval.jsonl    ← 20 ejemplos de evaluación
```

---

## Parámetros configurables en train_ray_qwen.py

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `NUM_WORKERS` | 4 | Número de GPUs del cluster |
| `BLOCK_SIZE` | 2048 | Tokens por ejemplo de entrenamiento |
| `EPOCHS` | 3 | Épocas de entrenamiento |
| `BATCH_SIZE` | 2 | Batch por GPU |
| `GRAD_ACCUM` | 4 | Pasos de acumulación de gradiente |
| `MODEL_NAME` | `Qwen/Qwen2.5-1.5B-Instruct` | Modelo base de HuggingFace |

**Batch efectivo total** = `BATCH_SIZE × GRAD_ACCUM × NUM_WORKERS` = `2 × 4 × 4` = **32**

---

## Detener el cluster Ray

Una vez terminado el entrenamiento, apagar Ray en todos los nodos:

```bash
ray stop
```

---

## Solución de problemas comunes

| Problema | Solución |
|---|---|
| `ConnectionError: Could not connect to Ray` | Verificar que `ray start --head` está activo en el master |
| `CUDA out of memory` | Reducir `BATCH_SIZE` a 1 o `BLOCK_SIZE` a 1024 |
| `FileNotFoundError: train.jsonl` | Ejecutar primero el pipeline del datalake (`crear_dataset_finetuning.py`) |
| Workers no aparecen en `ray status` | Verificar que la IP del master y el puerto 6379 son accesibles desde los workers |
