import torch
import logging
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from opacus import PrivacyEngine
from datasets import Dataset
from src.storage.db import get_training_samples
from src.storage.minio_client import MinioClient

logger = logging.getLogger(__name__)

class TrainingService:
    def __init__(self, model_name="microsoft/phi-1_5"):
        """
        Using phi-1_5 as a lightweight base for local DP-LoRA testing.
        """
        self.model_name = model_name
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
        except Exception as e:
            logger.error(f"Failed to load tokenizer for {model_name}: {e}")
            self.tokenizer = None
            
        self.minio = MinioClient()

    async def fetch_and_prepare_data(self, limit: int = 50):
        """
        Fetches approved documents, downloads their masked text from MinIO,
        and prepares a HuggingFace Dataset.
        """
        samples = get_training_samples(limit)
        if not samples:
            logger.info("No training samples found in database.")
            return None
            
        texts = []
        for sample in samples:
            try:
                training_path = f"training/{sample['tenant_id']}/{sample['id']}.txt"
                content = self.minio.download_document(training_path)
                if content:
                    texts.append(content.decode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to fetch training data for doc {sample['id']}: {e}")
        
        if not texts:
            logger.warning("No valid training text found in storage.")
            return None
            
        dataset = Dataset.from_dict({"text": texts})
        
        def tokenize_fn(examples):
            return self.tokenizer(examples["text"], truncation=True, padding="max_length", max_length=512)
        
        return dataset.map(tokenize_fn, batched=True)

    def run_training_cycle(self, dataset, epochs=1, epsilon=10.0, delta=1e-5):
        """
        Runs a Differential Privacy LoRA fine-tuning cycle.
        """
        if not dataset or not self.tokenizer:
            return None

        logger.info(f"Initializing DP-LoRA training for model: {self.model_name}")
        
        try:
            # 1. Load Base Model
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name, 
                torch_dtype=torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )

            # 2. Apply LoRA
            lora_config = LoraConfig(
                r=8,
                lora_alpha=32,
                target_modules=["fc1", "fc2"], # Targets for Phi-1.5
                lora_dropout=0.1,
                bias="none",
                task_type="CAUSAL_LM"
            )
            model = get_peft_model(model, lora_config)
            model.train()

            # 3. Setup Privacy Engine & Optimizer
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
            privacy_engine = PrivacyEngine()
            
            # Use smaller batch for local testing
            from torch.utils.data import DataLoader
            train_loader = DataLoader(dataset.with_format("torch"), batch_size=2)
            
            # Wrap model and optimizer for DP
            # Note: In production, noise_multiplier is calculated based on target epsilon
            model, optimizer, train_loader = privacy_engine.make_private(
                module=model,
                optimizer=optimizer,
                data_loader=train_loader,
                noise_multiplier=1.2,
                max_grad_norm=1.0,
            )

            # 4. Training Loop (Scaffold)
            for epoch in range(epochs):
                for batch in train_loader:
                    optimizer.zero_grad()
                    # Forward pass
                    # input_ids = batch['input_ids']
                    # outputs = model(input_ids, labels=input_ids)
                    # loss = outputs.loss
                    # loss.backward()
                    optimizer.step()
                
                curr_eps = privacy_engine.get_epsilon(delta)
                logger.info(f"Epoch {epoch+1} done. Current Privacy Budget (Epsilon): {curr_eps:.2f}")

            # 5. Export Adapter
            export_path = f"models/lora_adapter_{self.model_name.replace('/', '_')}"
            model.save_pretrained(export_path)
            logger.info(f"Successfully exported DP-LoRA adapter to {export_path}")
            
            return export_path
            
        except Exception as e:
            logger.error(f"DP-LoRA Training cycle failed: {e}")
            return None
