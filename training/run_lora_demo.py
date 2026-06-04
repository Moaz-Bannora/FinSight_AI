"""Optional PEFT/LoRA demo for the course requirement.

Default mode is a dependency check and dataset preview. Use --train only after
installing requirements-peft.txt and choosing a local or downloadable base model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parent / "finance_lora_dataset.jsonl"


def preview_dataset() -> None:
    rows = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Loaded {len(rows)} PEFT demo examples from {DATASET_PATH}.")
    for row in rows[:2]:
        print("\nInstruction:", row["instruction"])
        print("Input:", row["input"])
        print("Output:", row["output"][:200])


def train(base_model: str, output_dir: str) -> None:
    try:
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling, Trainer, TrainingArguments
    except Exception as exc:
        raise SystemExit(
            "PEFT dependencies are missing. Install them with: python -m pip install -r requirements-peft.txt"
        ) from exc

    rows = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    texts = [
        f"Instruction: {row['instruction']}\nInput: {row['input']}\nAnswer: {row['output']}"
        for row in rows
    ]
    dataset = Dataset.from_dict({"text": texts})

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=256)

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])
    model = AutoModelForCausalLM.from_pretrained(base_model)
    lora_config = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora_config)

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        num_train_epochs=1,
        learning_rate=2e-4,
        logging_steps=1,
        save_steps=10,
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Saved LoRA adapter demo to {output_dir}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Run the LoRA demo training.")
    parser.add_argument("--base-model", default="sshleifer/tiny-gpt2", help="Small model for demo training.")
    parser.add_argument("--output-dir", default="outputs/finance_lora_adapter", help="Adapter output directory.")
    args = parser.parse_args()

    preview_dataset()
    if args.train:
        train(args.base_model, args.output_dir)
    else:
        print("\nDry run complete. Add --train after installing PEFT dependencies to run LoRA.")


if __name__ == "__main__":
    main()
