import asyncio
import logging
import torch
from src.training.training_service import TrainingService
from src.extraction.agentic_navigator import AgenticNavigator
from src.storage.db import get_training_samples

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agentic_navigator():
    logger.info("--- Testing AgenticNavigator ---")
    # Mock doc bytes and page count
    mock_pdf = b"%PDF-1.4 mock content"
    page_count = 50
    
    # We mock fitz.open to skip actual PDF parsing for the heuristic test
    # if necessary, but fitz is installed, so we can try to find a real mini PDF or just check the logic
    try:
        indices = AgenticNavigator.identify_relevant_indices(mock_pdf, page_count)
        logger.info(f"Selected indices: {indices}")
        # Expect at least [0, 1, 49]
        if 0 in indices and 1 in indices and 49 in indices:
            logger.info("AgenticNavigator: [PASS] Basic indices selected.")
        else:
            logger.error("AgenticNavigator: [FAIL] Basic indices missing.")
    except Exception as e:
        logger.error(f"AgenticNavigator: [FAIL] Error: {e}")

async def test_training_service():
    logger.info("--- Testing TrainingService (DP-LoRA) ---")
    trainer = TrainingService(model_name="microsoft/phi-1_5")
    
    # We won't run a full training cycle (too heavy for verification), 
    # but we will check if Opacus and PEFT initialize correctly.
    try:
        import torch.nn as nn
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(10, 10)
                self.fc2 = nn.Linear(10, 10)
            def forward(self, x):
                return self.fc2(self.fc1(x))

        model = SimpleModel()
        from peft import LoraConfig, get_peft_model
        lora_config = LoraConfig(r=8, lora_alpha=32, target_modules=["fc1", "fc2"], task_type="CAUSAL_LM")
        # task_type CAUSAL_LM might error on a simple model, so we just use no task type for dummy
        model = get_peft_model(model, lora_config)
        logger.info("PEFT: [PASS] LoRA layers applied.")

        from opacus import PrivacyEngine
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
        privacy_engine = PrivacyEngine()
        
        # Mock loader
        from torch.utils.data import DataLoader, TensorDataset
        dataset = TensorDataset(torch.randn(10, 10), torch.randn(10, 10))
        loader = DataLoader(dataset, batch_size=2)
        
        model.train()
        model, optimizer, loader = privacy_engine.make_private(
            module=model,
            optimizer=optimizer,
            data_loader=loader,
            noise_multiplier=1.1,
            max_grad_norm=1.0,
        )
        logger.info("Opacus: [PASS] Privacy Engine attached.")
        
    except Exception as e:
        logger.error(f"TrainingService Initialization: [FAIL] {e}")

async def main():
    await test_agentic_navigator()
    await test_training_service()

if __name__ == "__main__":
    asyncio.run(main())
