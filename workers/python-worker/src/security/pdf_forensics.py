import logging
import io
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.pdf_utils.reader import PdfFileReader
import fitz # PyMuPDF for secondary forensics

logger = logging.getLogger(__name__)

class PDFForensics:
    """
    Electronic Forensics Service for Axiocore V3.
    Verifies Digital Signatures and extracts PDF metadata for audit.
    """

    def analyze(self, pdf_bytes: bytes) -> dict:
        report = {
            "signatures": [],
            "metadata": {},
            "integrity_risk": "low",
            "warnings": []
        }

        try:
            # 1. Digital Signature Verification
            pdf_io = io.BytesIO(pdf_bytes)
            reader = PdfFileReader(pdf_io)
            
            if reader.embedded_signatures:
                for sig in reader.embedded_signatures:
                    try:
                        validity = validate_pdf_signature(sig)
                        report["signatures"].append({
                            "name": sig.sig_name,
                            "is_valid": validity.intact and validity.valid,
                            "integrity_intact": validity.intact,
                            "timestamp": str(validity.timestamp) if validity.timestamp else None
                        })
                    except Exception as sig_err:
                        logger.warning(f"Signature validation error: {sig_err}")
                        report["warnings"].append(f"Could not validate signature {sig.sig_name}")
            
            # 2. Metadata Forensics (PyMuPDF)
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            meta = doc.metadata
            report["metadata"] = {
                "producer": meta.get("producer"),
                "creator": meta.get("creator"),
                "created_at": meta.get("creationDate"),
                "modified_at": meta.get("modDate"),
                "trapped": meta.get("trapped"),
                "encryption": doc.permissions
            }

            # 3. Risk Heuristics
            # Example: If Producer is empty or missing CreationDate, flag it.
            if not meta.get("producer") or not meta.get("creationDate"):
                report["integrity_risk"] = "medium"
                report["warnings"].append("Missing vital PDF metadata (Producer/CreationDate)")

            if any(not s["is_valid"] for s in report["signatures"]):
                report["integrity_risk"] = "high"
                report["warnings"].append("Invalid or tampered digital signature detected")

            doc.close()
        except Exception as e:
            logger.error(f"Forensics analysis failed: {e}")
            report["integrity_risk"] = "unknown"
            report["warnings"].append(f"Forensics engine error: {str(e)}")

        return report
