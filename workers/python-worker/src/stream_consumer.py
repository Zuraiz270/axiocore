import asyncio
import logging
import json
import re
from src.redis_client import get_redis_client
from src.storage.minio_client import MinioClient
from src.storage.db import update_document_status
from src.privacy.exif_stripper import ExifStripper
from src.privacy.pii_masker import PiiMasker
from src.extraction.router import ExtractionRouter

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "axiocore_extraction_group"
CONSUMER_NAME = "worker_1"
STREAMS = {
    "stream:extraction:high": ">",
    "stream:extraction:low": ">",
    "stream:extraction:complete": ">"
}

minio = MinioClient()
pii_masker = None # Lazy load because Spacy model is heavy

async def ensure_consumer_group(redis_client, stream_key: str):
    """Ensure the Redis consumer group exists, catch error if it already does."""
    try:
        await redis_client.xgroup_create(stream_key, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"Created consumer group {CONSUMER_GROUP} for {stream_key}")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            pass # Group already exists
        else:
            logger.error(f"Error creating generic consumer group for {stream_key}: {e}")

    return False

def detect_high_value_document(content: str) -> bool:
    """
    Scans extracted text for currency values exceeding $5,000.
    Matches formats like $5,000, $10.000, 5000.00 USD, etc.
    """
    # Regex to find numbers with optional decimals and commas
    numbers = re.findall(r'[\$£€¥]?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)', content)
    
    for num_str in numbers:
        try:
            val = float(num_str.replace(',', ''))
            if val > 5000:
                return True
        except ValueError:
            continue
    return False

async def process_outbox_event(event_id: str, payload_data: dict, stream_key: str):
    """
    Main entry point for processing an extraction event from Redis Streams.
    """
    # Parse payload if it's a string
    if isinstance(payload_data.get("payload"), str):
        event = json.loads(payload_data["payload"])
    else:
        event = payload_data

    tenant_id = event.get("tenant_id")
    document_id = event.get("aggregate_id")
    payload = event.get("payload", {})
    storage_path = payload.get("storage_path")
    mime_type = payload.get("mime_type")

    if not storage_path:
        logger.error(f"Missing storage_path for document {document_id}")
        return

    try:
        # 1. Download from MinIO
        minio = MinioClient()
        raw_data = minio.download_document(storage_path)

        # 2. Privacy: EXIF Stripping (Modality-Aware)
        stripper = ExifStripper()
        sanitized_data = stripper.strip_metadata(raw_data, mime_type)
        
        # 3. Security: PDF Forensics (Phase 4)
        forensics_report = None
        if mime_type == "application/pdf":
            from src.security.pdf_forensics import PDFForensics
            forensics = PDFForensics()
            forensics_report = forensics.analyze(sanitized_data)
            logger.info(f"Forensics completed for {document_id}. Risk: {forensics_report['integrity_risk']}")

        # 4. Extraction Cascade
        router = ExtractionRouter()
        extraction_result = await router.execute_cascade(sanitized_data, event)
        
        if extraction_result and extraction_result.get("content"):
            content = extraction_result["content"]
            confidence = extraction_result.get("confidence", 0.0)
            
            # Consensus Labeling Requirement: Values > $5,000 OR High Integrity Risk
            requires_consensus = detect_high_value_document(content)
            if forensics_report and forensics_report.get("integrity_risk") == "high":
                requires_consensus = True
                logger.warning(f"Consensus labeling triggered by forensics risk for {document_id}")

            if requires_consensus:
                logger.info(f"High-value/Risk document detected. Triggering consensus labeling.")

            # 5. Privacy: PII Masking for Training Artifacts
            from src.privacy.pii_masker import PiiMasker
            masker = PiiMasker()
            safe_text = masker.mask_text(content)
            
            # Store Derived Artifact
            training_path = f"training/{tenant_id}/{document_id}.txt"
            minio.upload_document(safe_text.encode('utf-8'), training_path, "text/plain")
            logger.info(f"Stored PII-masked training artifact at {training_path}")
            
            # Finalize with metadata
            update_document_status(
                tenant_id, 
                document_id, 
                "PENDING_REVIEW", 
                confidence_score=confidence,
                requires_consensus=requires_consensus,
                forensics_report=forensics_report
            )

            # 6. Notify Gateway of completion (Phase 5 HOTL Trigger)
            # This triggers the AutoApprovalService in NestJS
            redis_client = get_redis_client()
            await redis_client.xadd(
                "stream:extraction:complete",
                {
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "confidence_score": str(confidence),
                    "requires_consensus": "true" if requires_consensus else "false"
                }
            )
            logger.info(f"Published completion event for {document_id}")
        else:
            logger.warning(f"Extraction failed/not fully implemented: {extraction_result.get('reason')}")
            update_document_status(tenant_id, document_id, "EXTRACTION_FAILED")
    except Exception as e:
        logger.error(f"Failed pipeline for document {document_id}: {e}")
        update_document_status(tenant_id, document_id, "EXTRACTION_FAILED")
        raise

async def stream_consumer_loop(stop_event: asyncio.Event):
    redis_client = get_redis_client()
    
    # Initialize groups
    for stream in STREAMS.keys():
        await ensure_consumer_group(redis_client, stream)
    
    logger.info("Listening for extraction events...")
    
    while not stop_event.is_set():
        try:
            # logger.debug("Polling Redis Streams...")
            # Block for 2 seconds, read 5 events maximum across defined streams
            messages = await redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams=STREAMS,
                count=5,
                block=2000
            )
            
            for stream_key, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    try:
                        await process_outbox_event(message_id, message_data, stream_key)
                        # Acknowledge the message so it resolves from the group's pending list
                        await redis_client.xack(stream_key, CONSUMER_GROUP, message_id)
                    except Exception as ex:
                        logger.error(f"Failed to process message {message_id}: {ex}")
                        
        except Exception as e:
            logger.error(f"Error reading from streams: {e}")
            await asyncio.sleep(2)  # Avoid tight loop on total failure
