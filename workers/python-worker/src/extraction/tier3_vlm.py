import logging

logger = logging.getLogger(__name__)

class Tier3VlmExtractor:
    """
    Tier 3: Vision Language Model (Heavy OCR).
    Target: Hand-written, extremely poor quality, or unstructured multimodal documents.
    Status: FEATURE FLAGGED OFF until benchmarking completes.
    """
    
    @staticmethod
    def extract(payload_bytes: bytes) -> str:
        logger.error("Tier 3 VLM Execution attempted while Feature Flag is OFF.")
        raise NotImplementedError("Tier 3 VLM is disabled by policy.")
