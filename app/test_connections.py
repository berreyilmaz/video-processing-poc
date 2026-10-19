
from pymongo import MongoClient
from minio import Minio

from app.config import (
    MONGO_URL,
    MONGO_DATABASE,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET_VIDEOS,
    MINIO_BUCKET_RESULTS,
)

# MongoDB bağlantısını test et
try:
    mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    mongo.admin.command("ping")
    print("✅ MongoDB bağlantısı başarılı!")
    mongo.close()
except Exception as error:
    print("❌ MongoDB bağlantı hatası:", error)

# MinIO bağlantısını test et
try:
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    for bucket in [MINIO_BUCKET_VIDEOS, MINIO_BUCKET_RESULTS]:
        if client.bucket_exists(bucket):
            print(f"✅ MinIO bucket hazır: {bucket}")
        else:
            print(f"❌ MinIO bucket bulunamadı: {bucket}")

except Exception as error:
    print("❌ MinIO bağlantı hatası:", error)
