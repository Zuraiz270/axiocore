import boto3
import requests
import jwt
from io import BytesIO
from PIL import Image

# 1. Create a dummy test image with dummy EXIF (Pillow doesn't easily write EXIF, but we will just create a valid image)
img = Image.new('RGB', (100, 100), color = 'red')
img_bytes = BytesIO()
img.save(img_bytes, format='JPEG')
img_data = img_bytes.getvalue()

# 2. Upload to MinIO
tenant_id = "123e4567-e89b-12d3-a456-426614174000"
storage_path = f"tenant-{tenant_id}/incoming/test-image.jpg"

print(f"Uploading mock image to MinIO path: {storage_path}")
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='admin', aws_secret_access_key='password')
# Create bucket if not exists
try:
    s3.head_bucket(Bucket='axiocore-documents')
except:
    s3.create_bucket(Bucket='axiocore-documents')

s3.put_object(Bucket='axiocore-documents', Key=storage_path, Body=img_data, ContentType='image/jpeg')

# 3. Generate Auth Token
import subprocess
result = subprocess.run(["node", "generate_token.js"], capture_output=True, text=True)
token = result.stdout.strip()

# 4. Trigger the NestJS Gateway
print("Triggering NestJS Ingestion endpoint...")
payload = {
    "original_filename": "test-image.jpg",
    "mime_type": "image/jpeg",
    "file_size_bytes": len(img_data),
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
