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
        mime_type = document_metadata.get("mime_type", "")
        
        try:
            from .tier0_direct import Tier0DirectExtractor
            from .tier1_ocrmypdf import Tier1OcrExtractor
            from .tier2_docling import Tier2DoclingExtractor
            from .tier3_vlm import Tier3VlmExtractor
            from .agentic_navigator import AgenticNavigator
            
            page_count = document_metadata.get("page_count", 1)
            
            def get_tier_executor(tier):
                if tier == "tier0": return Tier0DirectExtractor.extract
                if tier == "tier1": return Tier1OcrExtractor.extract
                if tier == "tier2": return Tier2DoclingExtractor.extract
                if tier == "tier3": return Tier3VlmExtractor.extract
                return None

            executor = get_tier_executor(assigned_tier)
            if not executor:
                return {"status": "failed", "reason": "Unknown routing tier."}

            # Apply Agentic Navigation for PDFs > 5 pages
            if mime_type == "application/pdf" and page_count > 5:
                content = AgenticNavigator.navigate_and_extract(payload_bytes, page_count, executor)
            else:
                content = executor(payload_bytes)

            confidence_map = {"tier0": 1.0, "tier1": 0.85, "tier2": 0.9, "tier3": 0.95}
            return {
                "status": "success", 
                "tier": int(assigned_tier[-1]), 
                "content": content, 
                "confidence": confidence_map.get(assigned_tier, 0.5)
            }
                
        except Exception as e:
            logger.error(f"Failed to execute extraction tier {assigned_tier}: {str(e)}")
            return {"status": "failed", "reason": str(e)}
            
        return {"status": "failed", "reason": "Unknown routing tier."}
