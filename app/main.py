
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from minio import Minio
from pymongo import MongoClient

from app.config import (
    MONGO_URL,
    MONGO_DATABASE,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET_VIDEOS,
)

app = FastAPI(
    title="Video Processing API",
    description="Video yükleme ve işleme PoC projesi",
    version="0.1.0",
)

# MongoDB bağlantısı
mongo_client = MongoClient(
    MONGO_URL,
    serverSelectionTimeoutMS=5000,
)
db = mongo_client[MONGO_DATABASE]
jobs_collection = db["jobs"]

# MinIO bağlantısı
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)


@app.get("/")
def root():
    return {"message": "Video Processing API çalışıyor!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/videos", status_code=201)
def upload_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Dosya adı bulunamadı.",
        )

    # Şimdilik yalnızca video uzantılarını kabul et.
    extension = Path(file.filename).suffix.lower()
    allowed_extensions = {".mp4", ".mov", ".avi", ".mkv"}

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Desteklenmeyen dosya uzantısı.",
        )

    job_id = str(uuid4())
    object_name = f"{job_id}{extension}"

    try:
        # Videoyu MinIO'ya yükle.
        minio_client.put_object(
            bucket_name=MINIO_BUCKET_VIDEOS,
            object_name=object_name,
            data=file.file,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=file.content_type or "application/octet-stream",
        )

        # İş kaydını MongoDB'ye ekle.
        job = {
            "job_id": job_id,
            "filename": Path(file.filename).name,
            "video_object_name": object_name,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        }

        jobs_collection.insert_one(job)

        return {
            "job_id": job_id,
            "filename": job["filename"],
            "status": job["status"],
            "message": "Video yüklendi, iş kuyruğuna eklendi.",
        }

    except Exception as error:
        # API üzerinden iç hata ayrıntılarını dışarıya verme.
        print(f"Video yükleme hatası: {error}")
        raise HTTPException(
            status_code=500,
            detail="Video yüklenemedi veya iş kaydı oluşturulamadı.",
        ) from error

    finally:
        file.file.close()


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs_collection.find_one(
        {"job_id": job_id},
        {"_id": 0},
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="İş bulunamadı.",
        )

    if isinstance(job.get("created_at"), datetime):
        job["created_at"] = job["created_at"].isoformat()

    return job



@app.get("/jobs/{job_id}/metrics")
def get_job_metrics(job_id: str):
    job = jobs_collection.find_one(
        {"job_id": job_id},
        {"_id": 0, "job_id": 1, "status": 1, "metrics": 1},
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="İş bulunamadı.",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="İş henüz tamamlanmadı.",
        )

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "metrics": job.get("metrics", {}),
    }
