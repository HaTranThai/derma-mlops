import hashlib
import io
import logging
import os
import subprocess

from PIL import Image

from app.core.config import settings
from app.repositories import review_repository
from app.services.storage_service import StorageService

logger = logging.getLogger("ingest")

REPO_DIR = "/app"
DVC_REMOTE = "minio_internal"

_holdout_hashes = None


def _holdout_hash_set():
    """md5 của toàn bộ ảnh val + test -> chặn leak: ảnh trùng byte không được vào train."""
    global _holdout_hashes
    if _holdout_hashes is not None:
        return _holdout_hashes
    base = os.path.dirname(settings.DATASET_PATH.rstrip("/"))
    hashes = set()
    for name in ("val", "test"):
        root = os.path.join(base, name)
        if not os.path.isdir(root):
            continue
        for cls in os.listdir(root):
            cls_dir = os.path.join(root, cls)
            if not os.path.isdir(cls_dir):
                continue
            for fname in os.listdir(cls_dir):
                if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    try:
                        with open(os.path.join(cls_dir, fname), "rb") as handle:
                            hashes.add(hashlib.md5(handle.read()).hexdigest())
                    except Exception:
                        pass
    logger.warning("Leak-guard: nap %s hash anh val/test", len(hashes))
    _holdout_hashes = hashes
    return hashes


def _read_data_version():
    pointer = settings.DATASET_PATH.rstrip("/") + ".dvc"
    try:
        with open(pointer) as handle:
            for line in handle:
                stripped = line.strip().lstrip("- ")
                if stripped.startswith("md5:"):
                    return stripped.split("md5:", 1)[1].strip()
    except Exception:
        return None
    return None


def _dvc_commit():
    rel = os.path.relpath(settings.DATASET_PATH, REPO_DIR)
    add = subprocess.run(["dvc", "add", rel], cwd=REPO_DIR, capture_output=True, text=True)
    if add.returncode != 0:
        logger.warning("dvc add loi: %s", add.stderr.strip())
        return None, f"add_error: {add.stderr.strip()[:200]}"
    push = subprocess.run(["dvc", "push", "-r", DVC_REMOTE], cwd=REPO_DIR, capture_output=True, text=True)
    if push.returncode != 0:
        logger.warning("dvc push loi: %s", push.stderr.strip())
        return _read_data_version(), f"push_error: {push.stderr.strip()[:200]}"
    return _read_data_version(), "pushed"


def ingest_reviews(run_dvc=True):
    rows = review_repository.list_uningested_reviewed()
    if not rows:
        return {"ingested": 0, "leaked": 0, "invalid": 0, "by_label": {},
                "data_version": _read_data_version(), "dvc": "skipped", "note": "khong co review moi"}

    storage = StorageService()
    holdout = _holdout_hash_set()
    classes = set(os.listdir(settings.DATASET_PATH)) if os.path.isdir(settings.DATASET_PATH) else set()
    written, leaked, invalid = [], [], []
    by_label = {}

    for row in rows:
        label = row["review_label"]
        pid = row["prediction_id"]
        if label not in classes:
            invalid.append(pid)
            continue
        try:
            data, _ = storage.get_object(row["image_key"])
            Image.open(io.BytesIO(data)).verify()
        except Exception as err:
            logger.warning("Anh review %s hong/khong tai duoc: %s", pid, err)
            invalid.append(pid)
            continue
        if hashlib.md5(data).hexdigest() in holdout:
            logger.warning("LEAK chan: anh review %s trung byte voi val/test -> KHONG vao train", pid)
            leaked.append(pid)
            continue
        dest_dir = os.path.join(settings.DATASET_PATH, label)
        os.makedirs(dest_dir, exist_ok=True)
        with open(os.path.join(dest_dir, f"{pid}.jpg"), "wb") as handle:
            handle.write(data)
        written.append(pid)
        by_label[label] = by_label.get(label, 0) + 1

    data_version, dvc_status = (None, "skipped")
    if written and run_dvc:
        data_version, dvc_status = _dvc_commit()

    if data_version:
        review_repository.mark_ingested(written, data_version)
    if leaked:
        review_repository.mark_ingested(leaked, "leak_skipped")
    if invalid:
        review_repository.mark_ingested(invalid, "invalid")

    logger.warning("Ingest: %s vao train | %s leak (loai) | %s anh hong | dvc=%s | data_version=%s",
                   len(written), len(leaked), len(invalid), dvc_status, data_version)
    return {
        "ingested": len(written),
        "leaked": len(leaked),
        "invalid": len(invalid),
        "by_label": by_label,
        "data_version": data_version,
        "dvc": dvc_status,
        "marked": bool(data_version),
    }
