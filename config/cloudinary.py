import cloudinary
from cloudinary.uploader import upload, upload_large
from dotenv import load_dotenv
from fastapi import UploadFile
import os

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_bytes_to_cloudinary(image_bytes):
    try:
        result = upload(image_bytes)
        return result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary Error: {e}")
        return None

async def upload_fastapi_file(file: UploadFile):
    try:
        # Use upload_large and pass the file stream directly. 
        # This prevents loading huge videos into RAM and prevents timeout/connection aborted errors.
        result = upload_large(file.file, resource_type="auto")
        return result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary Error: {e}")
        return None