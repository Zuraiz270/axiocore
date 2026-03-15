import boto3
import requests
import subprocess
import os

# 1. Reuse the digital PDF but mark it as 'scanned' to force Tier 2
tenant_id = "123e4567-e89b-12d3-a456-426614174000"
storage_path = f"tenant-{tenant_id}/incoming/test-complex.pdf"

# Generate a simple PDF if it doesn't exist or just reuse
from reportlab.pdfgen import canvas
from io import BytesIO

packet = BytesIO()
can = canvas.Canvas(packet)
can.drawString(100, 750, "COMPLEX DOCUMENT TEST")
can.drawString(100, 730, "This PDF should be routed to Tier 2 (Docling).")
can.save()
pdf_data = packet.getvalue()

print(f"Uploading complex PDF to MinIO path: {storage_path}")
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='admin', aws_secret_access_key='password')
s3.put_object(Bucket='axiocore-documents', Key=storage_path, Body=pdf_data, ContentType='application/pdf')

# 2. Generate Auth Token
result = subprocess.run(["node", "generate_token.js"], capture_output=True, text=True)
token = result.stdout.strip()

# 3. Trigger the NestJS Gateway
print("Triggering NestJS Ingestion endpoint...")
payload = {
    "original_filename": "test-complex.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": len(pdf_data),
    "page_count": 1,
    "storage_path": storage_path,
    "schema_type": "invoice",
    "priority": "high",
    "source_type": "scanned" # This forces Tier 2 even if it's a digital PDF
}

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

resp = requests.post("http://localhost:3001/documents/ingest", json=payload, headers=headers)
print(f"Gateway Response: {resp.status_code} - {resp.text}")

if resp.status_code == 201:
    print("Success! Check worker logs for Tier 2 Docling extraction results.")
else:
    print("Failed to trigger ingestion.")
