import boto3
import requests
from io import BytesIO
from PIL import Image, ImageDraw

# 1. Create a mock scanned image with some text
img = Image.new('RGB', (400, 200), color=(255, 255, 255))
d = ImageDraw.Draw(img)
# Use default font
d.text((10, 10), "INVOICE #98765\nVendor: Acme Corp\nService: Cloud Hosting\nTotal: $300.00", fill=(0, 0, 0))

img_bytes = BytesIO()
img.save(img_bytes, format='JPEG')
img_data = img_bytes.getvalue()

# 2. Upload to MinIO
tenant_id = "123e4567-e89b-12d3-a456-426614174000"
storage_path = f"tenant-{tenant_id}/incoming/test-scan.jpg"

print(f"Uploading mock scan to MinIO path: {storage_path}")
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='admin', aws_secret_access_key='password')
s3.put_object(Bucket='axiocore-documents', Key=storage_path, Body=img_data, ContentType='image/jpeg')

# 3. Generate Auth Token
import subprocess
result = subprocess.run(["node", "generate_token.js"], capture_output=True, text=True)
token = result.stdout.strip()

# 4. Trigger the NestJS Gateway
print("Triggering NestJS Ingestion endpoint...")
payload = {
    "original_filename": "test-scan.jpg",
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

# The Gateway currently hardcodes sourceType='digital_native' in the controller, 
# but the Router will still route images to Tier 1 because of 'image/' mime_type.
resp = requests.post("http://localhost:3001/documents/ingest", json=payload, headers=headers)
print(f"Gateway Response: {resp.status_code} - {resp.text}")

if resp.status_code == 201:
    print("Success! Check worker logs for Tier 1 OCR extraction results.")
else:
    print("Failed to trigger ingestion.")
