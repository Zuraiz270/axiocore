import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class Tier0DirectExtractor:
    """
    Tier 0: Direct Parse.
    Target: Born-digital PDFs containing selectable text.
    Library: PyMuPDF or pdfplumber.
    """
    
    @staticmethod
    def extract(payload_bytes: bytes) -> str:
        logger.info("Executing Tier 0 Direct Extraction using PyMuPDF...")
        try:
            # Open the PDF directly from the byte stream
            doc = fitz.open(stream=payload_bytes, filetype="pdf")
            extracted_pages = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Extract clean text, maintaining raw layout where possible
                text = page.get_text("text")
                extracted_pages.append(text)
                
            full_text = "\n\n--- PAGE BREAK ---\n\n".join(extracted_pages)
            return full_text
            
        except Exception as e:
            logger.error(f"Tier 0 Extraction Failed: {e}")
            raise RuntimeError(f"PyMuPDF failed to parse document: {e}")
