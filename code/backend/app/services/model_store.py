import io
import json
import logging

from minio import Minio
from minio.commonconfig import CopySource

from app.core.config import settings

logger = logging.getLogger("model_store")

BUCKET = settings.MINIO_BUCKET_MODELS
PROD_KEY = "production/model.pt"
PROD_META = "production/meta.json"

_client = None


def client():
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=settings.MINIO_REGION,
        )
    return _client


def ensure_bucket():
    c = client()
    if not c.bucket_exists(BUCKET):
        c.make_bucket(BUCKET)


def exists(key):
    try:
        client().stat_object(BUCKET, key)
        return True
    except Exception:
        return False


def put_bytes(key, data, content_type="application/octet-stream"):
    ensure_bucket()
    client().put_object(BUCKET, key, io.BytesIO(data), length=len(data), content_type=content_type)


def get_bytes(key):
    response = client().get_object(BUCKET, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def copy(src_key, dst_key):
    client().copy_object(BUCKET, dst_key, CopySource(BUCKET, src_key))


def put_staging(tag, data):
    put_bytes(f"staging/{tag}.pt", data)


def set_production(data, meta):
    ensure_bucket()
    if exists(PROD_KEY) and exists(PROD_META):
        try:
            old = json.loads(get_bytes(PROD_META).decode())
            old_tag = old.get("tag") or f"v{old.get('version', 'prev')}"
            copy(PROD_KEY, f"archive/{old_tag}.pt")
            logger.warning("Archive production cu -> archive/%s.pt", old_tag)
        except Exception as err:
            logger.warning("Archive production cu that bai: %s", err)
    put_bytes(PROD_KEY, data, "application/octet-stream")
    put_bytes(PROD_META, json.dumps(meta, indent=2, ensure_ascii=False).encode(), "application/json")
    logger.warning("Cap nhat production -> %s/%s (tag=%s)", BUCKET, PROD_KEY, meta.get("tag"))


def load_production_checkpoint():
    import torch

    data = get_bytes(PROD_KEY)
    return torch.load(io.BytesIO(data), map_location="cpu")


def load_checkpoint(key):
    import torch

    data = get_bytes(key)
    return torch.load(io.BytesIO(data), map_location="cpu")
