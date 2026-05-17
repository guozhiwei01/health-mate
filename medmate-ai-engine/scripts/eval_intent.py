"""
Intent Classifier Evaluation
Load LoRA fine-tuned model, test on val set, compute accuracy + confusion matrix
"""
import json
import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from collections import defaultdict

BASE_MODEL = "D:/models/Qwen2.5-0.5B-Instruct"
LORA_PATH = "D:/project/health-mate/medmate-ai-engine/training/saves/intent-classifier"
VAL_DATA = "D:/project/health-mate/medmate-ai-engine/training/data/intent_val.json"

SYSTEM_PROMPT = (
    "你是一个医疗意图分类器。请将用户的输入分类为以下7个类别之一："
    "casual_chat(日常闲聊), health_qa(健康知识问答), symptom_consult(症状咨询), "
    "drug_consult(用药咨询), report_parse(报告解读), emergency(紧急情况), "
    "task_command(任务指令)。只输出类别标签，不要解释。"
)

VALID_INTENTS = {"casual_chat", "health_qa", "symptom_consult", "drug_consult", "report_parse", "emergency", "task_command"}


def load_model():
    print("[1/3] Loading base model...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    print("[2/3] Loading LoRA weights...", flush=True)
    model = PeftModel.from_pretrained(model, LORA_PATH)
    model.eval()
    print("[OK] Model loaded", flush=True)
    return model, tokenizer


def predict(model, tokenizer, text):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=20,
            do_sample=False,
            temperature=1.0,
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    result = tokenizer.decode(new_tokens, skip_special_tokens=True).strip().lower()

    # extract valid intent from result
    for intent in VALID_INTENTS:
        if intent in result:
            return intent
    return result


def main():
    model, tokenizer = load_model()

    print("[3/3] Running evaluation...", flush=True)
    with open(VAL_DATA, "r", encoding="utf-8") as f:
        val_data = json.load(f)

    correct = 0
    total = 0
    errors = []
    confusion = defaultdict(lambda: defaultdict(int))

    for i, item in enumerate(val_data):
        convs = item["conversations"]
        user_text = convs[1]["value"]
        expected = convs[2]["value"]

        predicted = predict(model, tokenizer, user_text)
        confusion[expected][predicted] += 1

        if predicted == expected:
            correct += 1
        else:
            errors.append({"input": user_text, "expected": expected, "predicted": predicted})

        total += 1
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(val_data)} | Acc: {correct/total:.1%}", flush=True)

    # Results
    accuracy = correct / total
    print(f"\n{'='*50}", flush=True)
    print(f"ACCURACY: {correct}/{total} = {accuracy:.1%}", flush=True)
    print(f"Target: >= 95%  |  {'PASS' if accuracy >= 0.95 else 'NEED MORE WORK'}", flush=True)

    # Per-class accuracy
    print(f"\nPer-class:", flush=True)
    for intent in sorted(VALID_INTENTS):
        row = confusion[intent]
        total_cls = sum(row.values())
        correct_cls = row.get(intent, 0)
        if total_cls > 0:
            print(f"  {intent:20s}: {correct_cls}/{total_cls} = {correct_cls/total_cls:.0%}", flush=True)

    # Errors
    if errors:
        print(f"\nErrors ({len(errors)}):", flush=True)
        for e in errors[:10]:
            print(f"  [{e['expected']} -> {e['predicted']}] {e['input'][:50]}", flush=True)


if __name__ == "__main__":
    main()
