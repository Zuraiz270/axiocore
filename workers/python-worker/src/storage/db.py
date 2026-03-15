import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/axiocore")
    return psycopg2.connect(db_url)
def update_document_status(
    tenant_id: str, 
    document_id: str, 
    status: str, 
    confidence_score: float = None, 
    requires_consensus: bool = None,
    forensics_report: dict = None
):
    """
    Updates the document status directly in Postgres. Enforces RLS by setting 
    the local tenant context before executing the query.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Enforce Row-Level Security context for the transaction
            cursor.execute("SET LOCAL app.current_tenant = %s;", (tenant_id,))
            
            # 2. Update the status and metrics
            fields = ["status = %s", "updated_at = NOW()"]
            params = [status]
            
            if confidence_score is not None:
                fields.append("confidence_score = %s")
                params.append(confidence_score)
            
            if requires_consensus is not None:
                fields.append("requires_consensus = %s")
                params.append(requires_consensus)

            if forensics_report is not None:
                fields.append("forensics_report = %s")
                import json
                params.append(json.dumps(forensics_report))
            
            params.extend([document_id, tenant_id])
            query = f"UPDATE documents SET {', '.join(fields)} WHERE id = %s AND tenant_id = %s;"
            cursor.execute(query, tuple(params))
            
        conn.commit()
        logger.info(f"Updated document {document_id} status to {status}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update document status: {e}")
        raise
    finally:
        conn.close()

def get_document_metadata(tenant_id: str, document_id: str) -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SET LOCAL app.current_tenant = %s;", (tenant_id,))
            cursor.execute("SELECT * FROM documents WHERE id = %s AND tenant_id = %s;", (document_id, tenant_id))
            doc = cursor.fetchone()
            return dict(doc) if doc else None
    except Exception as e:
        logger.error(f"Failed to get document metadata: {e}")
        raise
    finally:
        conn.close()

def get_training_samples(limit: int = 100) -> list:
    """
    Fetches documents with 'APPROVED' status for DP-LoRA fine-tuning.
    Returns a list of dicts with document and tenant IDs.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # We fetch across all tenants for bulk fine-tuning (DP ensures privacy)
            cursor.execute(
                "SELECT id, tenant_id, schema_type FROM documents WHERE status = 'APPROVED' LIMIT %s;", 
                (limit,)
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch training samples: {e}")
        raise
    finally:
        conn.close()
