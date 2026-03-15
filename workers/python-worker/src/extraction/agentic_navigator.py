import logging
import fitz  # PyMuPDF
from typing import List, Dict, Any, Callable

logger = logging.getLogger(__name__)

class AgenticNavigator:
    """
    Chain-of-Scroll (CoS): Intelligent document navigation for large files.
    This module predicts relevant pages before heavy extraction to save tokens and time.
    """
    
    @staticmethod
    def identify_relevant_indices(doc_bytes: bytes, page_count: int) -> List[int]:
        """
        Analyzes the document structure to identify high-probability pages.
        For financial/legal docs, this typically includes the first few, the last, 
        and any pages with headers like 'Total' or 'Summary'.
        """
        try:
            doc = fitz.open(stream=doc_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"Failed to open PDF for navigation: {e}")
            return list(range(page_count))

        # Baseline: Always include first 2 and last page
        target_indices = {0, 1, page_count - 1}
        
        # Heuristic: Scan first 10 and last 5 pages for 'anchor' keywords
        # This is the 'Chain-of-Scroll' heuristic layer.
        search_range = list(range(min(page_count, 10))) + \
                       list(range(max(0, page_count - 5), page_count))
        
        anchors = ["total", "summary", "invoice", "balance", "due date", "vendor", "contract"]
        
        for i in search_range:
            if i >= page_count: continue
            try:
                text = doc[i].get_text().lower()
                if any(anchor in text for anchor in anchors):
                    target_indices.add(i)
            except:
                continue
                
        return sorted(list(target_indices))

    @staticmethod
    def navigate_and_extract(
        doc_bytes: bytes, 
        page_count: int, 
        extractor_fn: Callable[[bytes], str]
    ) -> str:
        """
        Executes extraction on a sparse subset of pages identified by the navigator.
        """
        if page_count <= 5:
            # Small docs don't need navigation optimization
            return extractor_fn(doc_bytes)
            
        relevant_indices = AgenticNavigator.identify_relevant_indices(doc_bytes, page_count)
        logger.info(f"AgenticNavigator: Reducing {page_count} pages -> {len(relevant_indices)} pages.")
        
        try:
            doc = fitz.open(stream=doc_bytes, filetype="pdf")
            subset_doc = fitz.open()
            subset_doc.insert_pdf(doc, select=relevant_indices)
            
            subset_bytes = subset_doc.tobytes()
            return extractor_fn(subset_bytes)
        except Exception as e:
            logger.error(f"Agentic navigation failed, falling back to full extract: {e}")
            return extractor_fn(doc_bytes)
