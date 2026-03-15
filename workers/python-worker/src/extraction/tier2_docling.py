import logging
import io
import tempfile
import os
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)

class Tier2DoclingExtractor:
    """
    Tier 2: Structural Extraction (Layout + Tables).
    Target: Complex PDFs with multi-column text or tables.
    Library: IBM Docling.
    """
    
    @staticmethod
    def extract(payload_bytes: bytes) -> str:
        logger.info("Executing Tier 2 Structural Extraction using IBM Docling...")
        
        # Docling can work with BytesIO if we wrap it, or temporary files
        # Let's use a temporary file for maximum compatibility with Docling's backend
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(payload_bytes)
            tmp_path = tmp.name
            
        try:
            converter = DocumentConverter()
            result = converter.convert(tmp_path)
            
            # Export to markdown for a balance of readability and structure
            markdown_content = result.document.export_to_markdown()
            return markdown_content
            
        except Exception as e:
            logger.error(f"Tier 2 Docling Extraction Failed: {e}")
            raise RuntimeError(f"Docling failed: {e}")
            
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
