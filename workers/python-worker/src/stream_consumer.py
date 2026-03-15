import asyncio
import logging
import json
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
    "stream:extraction:low": ">"
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

async def process_outbox_event(event_id: str, payload_data: dict, stream_key: str):
    """Route processing based on the event payload."""
    global pii_masker
    if not pii_masker:
        pii_masker = PiiMasker()

    event_type = payload_data.get("event_type")
    tenant_id = payload_data.get("tenant_id")
    document_id = payload_data.get("id")
    storage_path = payload_data.get("storage_path")

    logger.info(f"Processing event {event_id} - Doc {document_id}")
    logger.debug(f"FULL PAYLOAD: {payload_data}")
    
    if event_type == "document.ingested":
        try:
            # Transition to extracting
            update_document_status(tenant_id, document_id, "EXTRACTING")
            
            # Download dirty original payload from Minio
            raw_bytes = minio.download_document(storage_path)
            
            # Enforce Policy A6: EXIF Stripping
            clean_bytes = ExifStripper.strip_metadata(raw_bytes, payload_data.get("mime_type"))
            
            # Store isolated 'Evidence Artifact' safely
            evidence_path = storage_path.replace("incoming/", "evidence/")
            minio.upload_document(clean_bytes, evidence_path, payload_data.get("mime_type", ""))
            
            # 5. Extraction Cascade (Tiers 0-3)
            from src.extraction.router import ExtractionRouter
            extraction_result = ExtractionRouter.execute_cascade(payload_data, clean_bytes)
            
            if extraction_result["status"] == "success":
                tier = extraction_result.get("tier", "unknown")
                confidence = extraction_result.get("confidence", 0.0)
                logger.info(f"Extraction Tier {tier} succeeded with confidence {confidence}")
                
                if confidence < 0.75:
                    logger.warning(f"Confidence {confidence} is below threshold 0.75. Human-in-the-loop mandated.")
                
                extracted_text = extraction_result["content"]
                
                # 6. Generate Training/Eval Artifact (PII Masked)
                safe_text = PiiMasker.mask(extracted_text)
                training_path = storage_path.replace("incoming/", "training/")
                minio.upload_document(safe_text.encode('utf-8'), training_path, "text/plain")
                logger.info(f"Stored PII-masked training artifact at {training_path}")
            else:
                logger.warning(f"Extraction failed/not fully implemented: {extraction_result.get('reason')}")

            update_document_status(tenant_id, document_id, "PENDING_REVIEW")
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
