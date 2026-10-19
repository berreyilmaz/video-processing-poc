
import io
import json
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
from minio import Minio
from pymongo import MongoClient, ReturnDocument

from app.config import (
    MONGO_URL,
    MONGO_DATABASE,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET_VIDEOS,
    MINIO_BUCKET_RESULTS,
)


# MongoDB bağlantısı
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[MONGO_DATABASE]
jobs_collection = db["jobs"]

# MinIO bağlantısı
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

WORKER_ID = os.getenv("WORKER_ID", "worker-1")
FRAME_DELAY_SECONDS = 0.017
LEASE_SECONDS = 60


def claim_next_job():
    """En eski bekleyen işi atomik olarak alır."""

    now = datetime.now(timezone.utc)
    expired_lease = now

    job = jobs_collection.find_one_and_update(
        {
            "$or": [
                {"status": "pending"},
                {
                    "status": "processing",
                    "$or": [
                        {"lease_until": {"$lte": expired_lease}},
                        {
                            "lease_until": {"$exists": False},
                            "started_at": {"$lte": now - timedelta(seconds=60)},
                        },
                    ],
                },
            ]
        },
        {
            "$set": {
                "status": "processing",
                "started_at": now,
                "lease_until": now + timedelta(seconds=LEASE_SECONDS),
                "worker_id": WORKER_ID,
            },
            "$inc": {"attempts": 1},
            "$unset": {"error": ""},
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )

    return job


def renew_lease(job_id):
    """İş sürerken kilit süresini uzatır."""

    now = datetime.now(timezone.utc)

    jobs_collection.update_one(
        {
            "job_id": job_id,
            "status": "processing",
            "worker_id": WORKER_ID,
        },
        {
            "$set": {
                "lease_until": now + timedelta(seconds=LEASE_SECONDS)
            }
        },
    )


def process_video(job):
    """Videoyu indirir, kareleri okur ve sahte takip verisi üretir."""

    job_id = job["job_id"]
    video_object_name = job["video_object_name"]
    result_object_name = f"{job_id}.jsonl"

    response = minio_client.get_object(
        MINIO_BUCKET_VIDEOS,
        video_object_name,
    )

    try:
        # Büyük videoyu RAM yerine geçici dosyaya indir.
        with tempfile.NamedTemporaryFile(
            suffix=Path(video_object_name).suffix,
        ) as video_file:
            for chunk in response.stream(1024 * 1024):
                video_file.write(chunk)

            video_file.flush()

            capture = cv2.VideoCapture(video_file.name)

            if not capture.isOpened():
                raise ValueError("Video dosyası açılamadı.")

            frame_count = 0
            distance_by_player = {"player_1": 0.0, "player_2": 0.0}
            previous_positions = {}

            # Takip verisini geçici dosyaya satır satır yaz.
            with tempfile.NamedTemporaryFile(
                mode="w+",
                suffix=".jsonl",
                encoding="utf-8",
            ) as result_file:
                try:
                    while True:
                        success, frame = capture.read()

                        if not success:
                            break

                        # Bu bölüm gerçek nesne takibi yapmaz.
                        # Test amacıyla iki oyuncu için sahte koordinatlar üretir.
                        positions = {
                            "player_1": {
                                "x": float((frame_count * 3) % max(frame.shape[1], 1)),
                                "y": float(frame.shape[0] * 0.35),
                            },
                            "player_2": {
                                "x": float((frame_count * 2 + 100) % max(frame.shape[1], 1)),
                                "y": float(frame.shape[0] * 0.65),
                            },
                        }

                        for player_id, position in positions.items():
                            previous = previous_positions.get(player_id)

                            if previous:
                                dx = position["x"] - previous["x"]
                                dy = position["y"] - previous["y"]
                                distance_by_player[player_id] += (
                                    dx**2 + dy**2
                                ) ** 0.5

                        previous_positions = positions

                        record = {
                            "frame": frame_count,
                            "timestamp_seconds": round(
                                frame_count / 30.0, 3
                            ),
                            "players": positions,
                        }

                        result_file.write(
                            json.dumps(record, ensure_ascii=False) + "\n"
                        )

                        frame_count += 1

                        # Uzun süren işlerde lease'i yenile.
                        if frame_count % 100 == 0:
                            renew_lease(job_id)

                        time.sleep(FRAME_DELAY_SECONDS)

                finally:
                    capture.release()

                if frame_count == 0:
                    raise ValueError("Videoda okunabilir kare bulunamadı.")

                result_file.flush()
                result_file.seek(0)

                result_file.flush()
                result_file.seek(0)

                result_data = result_file.read().encode("utf-8")
                result_stream = io.BytesIO(result_data)

                minio_client.put_object(
                    bucket_name=MINIO_BUCKET_RESULTS,
                    object_name=result_object_name,
                    data=result_stream,
                    length=len(result_data),
                    content_type="application/x-ndjson",
                )

    finally:
        response.close()
        response.release_conn()

    return {
        "result_object_name": result_object_name,
        "frame_count": frame_count,
        "duration_seconds": round(frame_count / 30.0, 3),
        "distance_by_player": {
            player_id: round(distance, 2)
            for player_id, distance in distance_by_player.items()
        },
    }


def process_job(job):
    """İşi işler ve sonucu MongoDB'ye kaydeder."""

    job_id = job["job_id"]

    try:
        print(f"Video işleniyor: {job['filename']}")

        metrics = process_video(job)

        jobs_collection.update_one(
            {
                "job_id": job_id,
                "status": "processing",
                "worker_id": WORKER_ID,
            },
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc),
                    "metrics": metrics,
                },
                "$unset": {"lease_until": "", "error": ""},
            },
        )

        print(
            f"İş tamamlandı: {job_id} | "
            f"Kare sayısı: {metrics['frame_count']}"
        )

    except Exception as error:
        print(f"İşleme hatası ({job_id}): {error}")

        attempts = job.get("attempts", 1)
        next_status = "failed" if attempts >= 3 else "pending"

        jobs_collection.update_one(
            {
                "job_id": job_id,
                "status": "processing",
                "worker_id": WORKER_ID,
            },
            {
                "$set": {
                    "status": next_status,
                    "error": str(error)[:500],
                    "updated_at": datetime.now(timezone.utc),
                },
                "$unset": {"lease_until": ""},
            },
        )


def main():
    print(f"Worker başlatıldı: {WORKER_ID}")

    while True:
        job = claim_next_job()

        if job is None:
            time.sleep(2)
            continue

        print(
            f"İş alındı: {job['job_id']} "
            f"- Dosya: {job['filename']}"
        )

        process_job(job)


if __name__ == "__main__":
    main()
