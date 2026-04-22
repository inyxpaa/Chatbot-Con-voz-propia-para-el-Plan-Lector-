import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import time

def test_inference():
    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    adapter_id = "inyxpa/chatbot"
    
    print(f"Loading tokenizer: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    print(f"Loading base model (float16): {model_id}")
    # We use float16 to save RAM (3GB instead of 6GB)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, 
        torch_dtype=torch.float16, 
        low_cpu_mem_usage=True,
        device_map="cpu"
    )
    
    print(f"Loading adapter: {adapter_id}")
    model = PeftModel.from_pretrained(model, adapter_id)
    
    print("Inference test phase...")
    prompt = "Hola, ¿de qué trata el Plan Lector?"
    inputs = tokenizer(prompt, return_tensors="pt")
    
    start_time = time.time()
    outputs = model.generate(**inputs, max_new_tokens=50)
    end_time = time.time()
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"Response: {response}")
    print(f"Time taken: {end_time - start_time:.2f}s")

if __name__ == "__main__":
    test_inference()
