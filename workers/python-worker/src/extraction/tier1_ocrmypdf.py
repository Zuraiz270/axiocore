import logging
import io
import os
import pytesseract
from PIL import Image
import fitz  # PyMuPDF to render PDF to images if needed

logger = logging.getLogger(__name__)

# Explicitly set tesseract cmd if it's in the default path
tesseract_bin = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(tesseract_bin):
    pytesseract.pytesseract.tesseract_cmd = tesseract_bin

class Tier1OcrExtractor:
    """
    Tier 1: OCR Synthesis.
    Target: High-resolution scans requiring a text layer.
    Library: Tesseract (via pytesseract).
    """
    
    @staticmethod
    def extract(payload_bytes: bytes) -> str:
        logger.info("Executing Tier 1 OCR Extraction using PyTesseract...")
        
        try:
            # 1. Attempt to open as a PDF first
            try:
                doc = fitz.open(stream=payload_bytes, filetype="pdf")
                full_text = []
                for page in doc:
                    # Render page to high DPI image (300 DPI) for better OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    text = pytesseract.image_to_string(img)
                    full_text.append(text)
                return "\n\n--- PAGE BREAK ---\n\n".join(full_text)
            except Exception as pdf_err:
                logger.debug(f"Input is not a PDF, trying as raw image: {pdf_err}")
                # 2. Treat as raw image
                img = Image.open(io.BytesIO(payload_bytes))
                text = pytesseract.image_to_string(img)
                return text
                
        except Exception as e:
            logger.error(f"Tier 1 OCR Extraction Failed: {e}")
            raise RuntimeError(f"PyTesseract failed: {e}")

