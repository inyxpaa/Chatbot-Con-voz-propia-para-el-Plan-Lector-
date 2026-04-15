import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def main():
    base_model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    adapter_model_name = "inyxpa/chatbot"

    print(f"Loading base model: {base_model_name}")
    # Load the base model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    ).to(device)
    
    print(f"Loading tokenizer from: {adapter_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(adapter_model_name)

    print(f"Loading PEFT adapter: {adapter_model_name}")
    model = PeftModel.from_pretrained(base_model, adapter_model_name)
    
    # Example input
    messages = [
        {"role": "system", "content": "Eres un asistente de lectura especializado en la obra 'El Quijote' y otras del plan lector."},
        {"role": "user", "content": "¿Me puedes explicar brevemente de qué trata El Quijote?"}
    ]
    
    print("\nApplying chat template...")
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    print("Generating response...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=True
        )
    
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    
    print("\n--- TEST RESPONSE ---")
    print(response)
    print("---------------------")

if __name__ == "__main__":
    main()
