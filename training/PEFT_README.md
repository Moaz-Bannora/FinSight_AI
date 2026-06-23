# PEFT/LoRA Demo Notes

This folder handles the course requirement for fine-tuning or parameter-efficient tuning.

## Files

- `finance_lora_dataset.jsonl`: small finance instruction dataset.
- `run_lora_demo.py`: dry-run preview and optional LoRA training.

## Dry Run

```powershell
python training\run_lora_demo.py
```

This shows the dataset and confirms the PEFT demo is prepared.

## Training Run

```powershell
python -m pip install -r requirements-peft.txt
python training\run_lora_demo.py --train --base-model sshleifer/tiny-gpt2
```

The default model is tiny so the demo is lightweight. For a stronger result, use a better small local causal language model that your hardware can handle.

## How to Explain in the Presentation

Baseline behavior is the untuned local model. Adapted behavior is represented by the LoRA examples, which teach the model to:

- Explain finance ratios with formulas.
- Add cautious interpretation.
- Refuse unsafe finance advice.
- Ground company health summaries in evidence.

This is intentionally a course-friendly PEFT demonstration, not a production fine-tuning pipeline.
