
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

# MongoDB ayarları
MONGO_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
MONGO_DATABASE = os.getenv("MONGODB_DATABASE", "video_poc")
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = os.getenv("MONGODB_PORT", "27017")

MONGO_URL = (
    f"mongodb://{quote_plus(MONGO_USERNAME or '')}:"
    f"{quote_plus(MONGO_PASSWORD or '')}"
    f"@{MONGODB_HOST}:{MONGODB_PORT}/"
    f"{MONGO_DATABASE}?authSource=admin"
)

# MinIO ayarları
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD")

MINIO_BUCKET_VIDEOS = os.getenv("MINIO_BUCKET_VIDEOS", "videos")
MINIO_BUCKET_RESULTS = os.getenv("MINIO_BUCKET_RESULTS", "results")
