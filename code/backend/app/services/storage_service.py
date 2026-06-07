from io import BytesIO

from minio import Minio

from app.core.config import settings

BUCKETS = ["predictions", "mlflow", "dvc-store"]


class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=settings.MINIO_REGION,
        )
        self.bucket = settings.MINIO_BUCKET_PREDICTIONS
        self._ensure_buckets()

    def _ensure_buckets(self):
        for name in BUCKETS:
            if not self.client.bucket_exists(name):
                self.client.make_bucket(name)

    def upload_image(self, key, data, content_type="image/jpeg"):
        self.client.put_object(
            self.bucket,
            key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get_object(self, key):
        response = self.client.get_object(self.bucket, key)
        try:
            data = response.read()
            content_type = response.headers.get("Content-Type", "image/jpeg")
        finally:
            response.close()
            response.release_conn()
        return data, content_type
