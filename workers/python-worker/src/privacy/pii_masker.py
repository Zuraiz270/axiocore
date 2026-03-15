from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PiiMasker:
    def __init__(self):
        # Initializes the Analyzer with the Spacy en_core_web_lg model
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
    def mask_text(self, text: str) -> str:
        """
        Analyzes the text for PII entities and replaces them with synthetic
        placeholders (e.g. <PERSON>).
        """
        if not text:
            return text
            
        # Detect PII
        results = self.analyzer.analyze(text=text, language='en')
        
        # We specify default anonymization to replace with entity type e.g., <PERSON>, <EMAIL_ADDRESS>
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={
                "DEFAULT": OperatorConfig("replace", {"new_value": f"<{int(result.entity_type if False else 0)}>"}) 
            }
        )
        
        # Because we want specifically formatted tags like <PERSON_72>, we can slightly 
        # customize operators if needed, but the default <ENTITY_TYPE> works strictly for safety.
        # Fallback to simple replace operator for safe defaulting:
        safe_anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results
        )
        
        return safe_anonymized_result.text
