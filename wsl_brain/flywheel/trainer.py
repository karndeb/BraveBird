import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# The Teacher. Runs Unsloth fine-tuning.

class LoRATrainer:
    """
    Automated Fine-Tuning using Unsloth (2x faster, 60% less memory).
    This allows us to fine-tune 7B models locally on consumer GPUs.
    """

    def __init__(self):
        self.dataset_path = "data/datasets/sft_train/bravebird_finetune.jsonl"
        self.output_dir = "data/weights/ui-ins/adapter"
        self.base_model = "Qwen/Qwen2.5-VL-7B-Instruct"

    def train(self):
        """
        Starts the training process.
        Note: This blocks the GPU. Should be run when Agent is idle (Nightly).
        """
        logger.info("🏋️ [LoRATrainer] Starting fine-tuning session...")

        if not os.path.exists(self.dataset_path):
            logger.warning("No dataset found. Skipping training.")
            return

        try:
            # We import unsloth here to avoid dependency overhead during normal agent startup
            from unsloth import FastLanguageModel
            import torch
            from trl import SFTTrainer
            from transformers import TrainingArguments

            # 1. Load Model (4-bit quantization for speed)
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.base_model,
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )

            # 2. Add LoRA Adapters
            model = FastLanguageModel.get_peft_model(
                model,
                r=16,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                lora_alpha=16,
                lora_dropout=0,
                bias="none",
                use_gradient_checkpointing=True,
            )

            # 3. Setup Trainer
            # Note: We need a dataset loader compatible with the JSONL format
            # Pseudo-code for dataset loading:
            # dataset = load_dataset("json", data_files=self.dataset_path, split="train")

            trainer = SFTTrainer(
                model=model,
                train_dataset=None, # Insert dataset here
                dataset_text_field="text", # Needs formatting function
                max_seq_length=2048,
                args=TrainingArguments(
                    per_device_train_batch_size=2,
                    gradient_accumulation_steps=4,
                    warmup_steps=5,
                    max_steps=60, # Short run for continuous learning
                    learning_rate=2e-4,
                    fp16=not torch.cuda.is_bf16_supported(),
                    bf16=torch.cuda.is_bf16_supported(),
                    logging_steps=1,
                    output_dir="outputs",
                    optim="adamw_8bit",
                ),
            )

            # 4. Train
            trainer.train()

            # 5. Save Adapter
            model.save_pretrained(self.output_dir)
            tokenizer.save_pretrained(self.output_dir)
            
            logger.info(f"✅ [LoRATrainer] Training complete. Adapter saved to {self.output_dir}")
            
            # Trigger Hot-Swap in Perception Actor?
            # Ideally, we just restart the UI-Ins service.

        except ImportError:
            logger.error("❌ [LoRATrainer] Unsloth not installed. Cannot train.")
        except Exception as e:
            logger.error(f"❌ [LoRATrainer] Training failed: {e}")