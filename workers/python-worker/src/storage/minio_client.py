import os
import io
import boto3
from botocore.client import Config
import logging

logger = logging.getLogger(__name__)

class MinioClient:
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "password")
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1' # Default bogus region for local Minio
        )
        self.bucket = "axiocore-documents"

    def download_document(self, storage_path: str) -> bytes:
        """Downloads a document directly into memory as bytes."""
        try:
            doc_obj = self.s3_client.get_object(Bucket=self.bucket, Key=storage_path)
            return doc_obj['Body'].read()
        except Exception as e:
            logger.error(f"Failed to download from MinIO: {storage_path} - {e}")
            raise

    def upload_document(self, buffer: bytes, storage_path: str, mime_type: str = "application/pdf"):
        """Uploads a byte buffer to the specified tenant-isolated path."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=storage_path,
                Body=buffer,
                ContentType=mime_type
            )
            logger.info(f"Successfully uploaded to {storage_path}")
        except Exception as e:
            logger.error(f"Failed to upload to MinIO: {storage_path} - {e}")
            raise
