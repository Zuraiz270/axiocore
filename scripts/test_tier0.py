import boto3
import requests
import fitz  # PyMuPDF to generate a digital PDF
from io import BytesIO

# 1. Create a real digital PDF using PyMuPDF
doc = fitz.open()
page = doc.new_page()
text = "Axiocore V3 Digital Native Test.\nThis is a sample invoice for client John Doe.\nTotal Amount: $1,250.00"
page.insert_text((50, 50), text)
pdf_bytes = doc.write()
doc.close()

# 2. Upload to MinIO
tenant_id = "123e4567-e89b-12d3-a456-426614174000"
storage_path = f"tenant-{tenant_id}/incoming/test-digital.pdf"

print(f"Uploading digital PDF to MinIO path: {storage_path}")
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='admin', aws_secret_access_key='password')
s3.put_object(Bucket='axiocore-documents', Key=storage_path, Body=pdf_bytes, ContentType='application/pdf')

# 3. Generate Auth Token
import subprocess
result = subprocess.run(["node", "generate_token.js"], capture_output=True, text=True)
token = result.stdout.strip()

# 4. Trigger the NestJS Gateway
print("Triggering NestJS Ingestion endpoint...")
payload = {
    "original_filename": "test-digital.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": len(pdf_bytes),
    "page_count": 1,
    "storage_path": storage_path,
    "schema_type": "invoice",
    "priority": "high"
}

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

resp = requests.post("http://localhost:3001/documents/ingest", json=payload, headers=headers)
print(f"Gateway Response: {resp.status_code} - {resp.text}")

if resp.status_code == 201:
    print("Success! Check worker logs for Tier 0 extraction and PII masking results.")
else:
    print("Failed to trigger ingestion.")
