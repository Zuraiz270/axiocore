import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ExtractionRouter:
    """
    Tier-based routing logic for the Extraction Cascade.
    """
    
    @staticmethod
    def route_document(document_metadata: Dict[str, Any], payload_bytes: bytes) -> str:
        """
        Determines the appropriate extraction tier based on document characteristics.
        
        Tiers:
        - Tier 0 (Direct): Born-digital PDFs.
        - Tier 1 (OCRmyPDF): Searchable layer generation for basic scans.
        - Tier 2 (Docling): Structural/Table extraction for complex layouts.
        - Tier 3 (VLM): Heavy Visual Language Model (Currently Feature-Flagged OFF).
        """
        mime_type = document_metadata.get("mime_type", "")
        source_type = document_metadata.get("source_type", "scanned")
        
        # 1. Image Modalities natively drop to at least Tier 1
        if mime_type.startswith("image/"):
            # Further inspection could bump this to Tier 2 if complex
            logger.info("Image modality detected. Routing to Tier 1 (OCRmyPDF).")
            return "tier1"
            
        # 2. Born-Digital PDFs go to Tier 0
        if source_type == "digital_native" and mime_type == "application/pdf":
            logger.info("Digital Native PDF detected. Routing to Tier 0 (Direct Parse).")
            return "tier0"
            
        # 3. Default fallback for standard PDFs is Tier 2 for robust structural extraction
        logger.info("Complex document detected. Routing to Tier 2 (Docling).")
        return "tier2"
        
    @staticmethod
    def execute_cascade(document_metadata: Dict[str, Any], payload_bytes: bytes) -> Dict[str, Any]:
        """
        Executes the assigned tier and manages fallbacks if a tier fails.
        """
        assigned_tier = ExtractionRouter.route_document(document_metadata, payload_bytes)
        
        try:
            from .tier0_direct import Tier0DirectExtractor
            from .tier1_ocrmypdf import Tier1OcrExtractor
            from .tier2_docling import Tier2DoclingExtractor
            from .tier3_vlm import Tier3VlmExtractor
            
            if assigned_tier == "tier0":
                content = Tier0DirectExtractor.extract(payload_bytes)
                return {"status": "success", "tier": 0, "content": content, "confidence": 1.0}
            elif assigned_tier == "tier1":
                content = Tier1OcrExtractor.extract(payload_bytes)
                # Tier 1 (OCR) typically has lower confidence than Direct Parse
                return {"status": "success", "tier": 1, "content": content, "confidence": 0.85}
            elif assigned_tier == "tier2":
                content = Tier2DoclingExtractor.extract(payload_bytes)
                return {"status": "success", "tier": 2, "content": content, "confidence": 0.9}
            elif assigned_tier == "tier3":
                content = Tier3VlmExtractor.extract(payload_bytes)
                return {"status": "success", "tier": 3, "content": content, "confidence": 0.95}
                
        except Exception as e:
            logger.error(f"Failed to execute extraction tier {assigned_tier}: {str(e)}")
            return {"status": "failed", "reason": str(e)}
            
        return {"status": "failed", "reason": "Unknown routing tier."}
