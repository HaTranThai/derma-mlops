import logging
import os
import tempfile

import mlflow
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

from app.core.config import settings
from app.services import mlflow_service

logger = logging.getLogger("trainer")

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def _data_version():
    pointer = settings.DATASET_PATH.rstrip("/") + ".dvc"
    try:
        with open(pointer) as handle:
            for line in handle:
                stripped = line.strip().lstrip("- ")
                if stripped.startswith("md5:"):
                    return stripped.split("md5:", 1)[1].strip()
    except Exception as err:
        logger.warning("Khong doc duoc data version tu %s: %s", pointer, err)
    return "unversioned"


def _index_dataset(root):
    classes = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    samples = []
    for label_idx, cls in enumerate(classes):
        folder = os.path.join(root, cls)
        for name in os.listdir(folder):
            if name.lower().endswith((".jpg", ".jpeg", ".png")):
                samples.append((os.path.join(folder, name), label_idx))
    return classes, samples


def _split(samples, val_fraction, seed):
    rng = np.random.default_rng(seed)
    by_label = {}
    for path, label in samples:
        by_label.setdefault(label, []).append(path)
    train, val = [], []
    for label, paths in by_label.items():
        paths = list(paths)
        rng.shuffle(paths)
        n_val = max(1, int(round(len(paths) * val_fraction)))
        val.extend((p, label) for p in paths[:n_val])
        train.extend((p, label) for p in paths[n_val:])
    return train, val


class _LesionDataset(Dataset):
    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        return self.transform(image), label


SUPPORTED_ARCHS = ("efficientnet_b0", "resnet50", "mobilenet_v3_large")


def _sample_per_class(samples, n, seed):
    rng = np.random.default_rng(seed)
    by_label = {}
    for path, label in samples:
        by_label.setdefault(label, []).append(path)
    out = []
    for label, paths in by_label.items():
        paths = list(paths)
        rng.shuffle(paths)
        out.extend((p, label) for p in paths[:n])
    return out


def _build_model(arch, num_classes, freeze_backbone, pretrained=True, warm_start_state=None):
    builders = {
        "efficientnet_b0": (models.efficientnet_b0, getattr(models, "EfficientNet_B0_Weights", None)),
        "resnet50": (models.resnet50, getattr(models, "ResNet50_Weights", None)),
        "mobilenet_v3_large": (models.mobilenet_v3_large, getattr(models, "MobileNet_V3_Large_Weights", None)),
    }
    if arch not in builders:
        raise ValueError(f"Kien truc khong ho tro: {arch} (chon trong {SUPPORTED_ARCHS})")
    builder, weights_enum = builders[arch]
    weights = weights_enum.IMAGENET1K_V1 if (pretrained and weights_enum is not None) else None
    try:
        model = builder(weights=weights)
    except Exception as err:
        logger.warning("Khong tai duoc pretrained weights (%s), dung weights=None", err)
        model = builder(weights=None)
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False
    if arch == "resnet50":
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif arch == "mobilenet_v3_large":
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    else:
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    if warm_start_state is not None:
        try:
            model.load_state_dict(warm_start_state, strict=True)
            logger.warning("[%s] WARM-START tu Production (continual learning)", arch)
        except Exception as err:
            logger.warning("[%s] warm-start that bai (%s) -> dung pretrained", arch, err)
    return model


def _evaluate(model, loader, device, num_classes, mel_index):
    model.eval()
    confusion = np.zeros((num_classes, num_classes), dtype=np.int64)
    with torch.no_grad():
        for images, labels in loader:
            preds = model(images.to(device)).argmax(dim=1).cpu().numpy()
            for true, pred in zip(labels.numpy(), preds):
                confusion[true, pred] += 1
    total = confusion.sum()
    accuracy = float(np.trace(confusion) / total) if total else 0.0
    f1s = []
    for c in range(num_classes):
        tp = confusion[c, c]
        fp = confusion[:, c].sum() - tp
        fn = confusion[c, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * precision * recall / (precision + recall) if (precision + recall) else 0.0)
    macro_f1 = float(np.mean(f1s))
    mel_support = confusion[mel_index, :].sum()
    melanoma_recall = float(confusion[mel_index, mel_index] / mel_support) if mel_support else 0.0
    return {"accuracy": round(accuracy, 4), "macro_f1": round(macro_f1, 4), "melanoma_recall": round(melanoma_recall, 4)}


def _eval_transform(image_size):
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def evaluate_checkpoint_on_val(checkpoint, batch_size=32):
    """Chấm 1 checkpoint trên đúng data/val bằng cùng pipeline -> dùng cho gate (so cùng nguồn)."""
    val_root = settings.DATASET_VAL_PATH
    if not os.path.isdir(val_root):
        return None
    classes = checkpoint["classes"]
    arch = checkpoint["model_name"]
    image_size = checkpoint.get("image_size", settings.IMAGE_SIZE)
    device = torch.device("cpu")
    model = _build_model(arch, len(classes), freeze_backbone=False, pretrained=False).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    val_classes, raw_val = _index_dataset(val_root)
    name_to_idx = {c: i for i, c in enumerate(classes)}
    val_samples = [(p, name_to_idx[val_classes[lab]]) for p, lab in raw_val if val_classes[lab] in name_to_idx]
    mel_index = classes.index("mel") if "mel" in classes else 0
    loader = DataLoader(_LesionDataset(val_samples, _eval_transform(image_size)), batch_size=batch_size, shuffle=False)
    metrics = _evaluate(model, loader, device, len(classes), mel_index)
    logger.warning("Re-eval Production tren data/val (%s anh): %s", len(val_samples), metrics)
    return metrics


def _train_one(arch, train_loader, val_loader, n_train, n_val, classes, mel_index,
               image_size, epochs, batch_size, learning_rate, freeze_backbone, data_version, tag, seed,
               warm_start_state=None, trigger_reason="manual"):
    logger.warning("=== Train kien truc [%s] (tag=%s) ===", arch, tag)
    torch.manual_seed(seed)
    device = torch.device("cpu")
    model = _build_model(arch, len(classes), freeze_backbone, warm_start_state=warm_start_state).to(device)
    criterion = nn.CrossEntropyLoss()
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(params, lr=learning_rate)

    for epoch in range(epochs):
        model.train()
        running = 0.0
        for images, labels in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(images.to(device)), labels.to(device))
            loss.backward()
            optimizer.step()
            running += loss.item()
        logger.warning("[%s] Epoch %s/%s loss=%.4f", arch, epoch + 1, epochs, running / max(1, len(train_loader)))

    metrics = _evaluate(model, val_loader, device, len(classes), mel_index)
    logger.warning("[%s] metrics: %s", arch, metrics)

    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(settings.MLFLOW_EXPERIMENT)
    with tempfile.TemporaryDirectory() as folder:
        ckpt_path = os.path.join(folder, f"model_{arch}_{tag}.pt")
        torch.save({
            "classes": classes,
            "model_name": arch,
            "version": tag,
            "data_version": data_version,
            "image_size": image_size,
            "state_dict": model.state_dict(),
        }, ckpt_path)
        with mlflow.start_run(run_name=f"smoke_{arch}_{tag}") as run:
            mlflow.log_params({
                "architecture": arch,
                "mode": "smoke",
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "freeze_backbone": freeze_backbone,
                "n_train": n_train,
                "n_val": n_val,
                "data_version": data_version,
            })
            mlflow.log_metrics(metrics)
            mlflow.log_artifact(ckpt_path, artifact_path="model")
            run_id = run.info.run_id

    candidate = mlflow_service.register_candidate(run_id, version_tag=tag, stage="Staging", trigger_reason=trigger_reason)
    return {**candidate, "arch": arch, "metrics": metrics, "data_version": data_version}


def train_smoke(config, trigger_reason="manual"):
    smoke = config.get("smoke", {})
    epochs = int(smoke.get("epochs", 3))
    batch_size = int(smoke.get("batch_size", 16))
    learning_rate = float(smoke.get("learning_rate", 0.001))
    freeze_backbone = bool(smoke.get("freeze_backbone", True))
    val_fraction = float(smoke.get("val_fraction", 0.3))
    seed = int(smoke.get("seed", 42))
    subset_per_class = smoke.get("subset_per_class")  # None => dùng hết số ảnh trong folder
    base_tag = smoke.get("version_tag", "smoke")
    # archs: danh sách kiến trúc train để so sánh; nếu không có thì dùng arch đơn.
    archs = smoke.get("archs") or [smoke.get("arch", "efficientnet_b0")]

    root = settings.DATASET_PATH
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Khong tim thay dataset tai {root}")

    torch.manual_seed(seed)
    classes, full_samples = _index_dataset(root)
    total_in_folder = len(full_samples)
    # Ảnh người đã review (ingest đặt tên pred_*.jpg) -> LUÔN gom vào train, không để subsample bỏ rơi.
    reviewed = [(p, l) for (p, l) in full_samples if os.path.basename(p).startswith("pred_")]
    if subset_per_class:
        sampled = _sample_per_class(full_samples, int(subset_per_class), seed)
        seen = {p for p, _ in sampled}
        forced = [(p, l) for (p, l) in reviewed if p not in seen]
        samples = sampled + forced
        logger.warning("Folder %s anh; subset %s/lop=%s + %s anh review (luon gom) = %s anh",
                       total_in_folder, subset_per_class, len(sampled), len(forced), len(samples))
    else:
        samples = full_samples
        logger.warning("Dung TOAN BO %s anh (gom %s anh review)", len(samples), len(reviewed))
    mel_index = classes.index("mel") if "mel" in classes else 0

    # Warm-start: nạp weights Production hiện tại làm khởi tạo (continual learning) nếu cùng kiến trúc + lớp.
    prod_state = None
    prod_arch = None
    try:
        from app.services import model_store
        prod_ck = model_store.load_production_checkpoint()
        if prod_ck.get("classes") == classes:
            prod_state = prod_ck["state_dict"]
            prod_arch = prod_ck["model_name"]
            logger.warning("Co Production (%s) de warm-start", prod_arch)
    except Exception as err:
        logger.warning("Khong nap duoc Production de warm-start: %s", err)

    # Tập VAL cố định (data/val) để chấm điểm công bằng; nếu chưa có thì cắt ngẫu nhiên từ train.
    val_root = settings.DATASET_VAL_PATH
    fixed_val = []
    if os.path.isdir(val_root):
        val_classes, raw_val = _index_dataset(val_root)
        name_to_idx = {c: i for i, c in enumerate(classes)}
        fixed_val = [(p, name_to_idx[val_classes[lab]]) for p, lab in raw_val if val_classes[lab] in name_to_idx]
    if fixed_val:
        train_samples, val_samples = samples, fixed_val
        logger.warning("Tap VAL CO DINH (%s): %s anh", val_root, len(val_samples))
    else:
        train_samples, val_samples = _split(samples, val_fraction, seed)
        logger.warning("Chua co tap val -> cat ngau nhien %.0f%% tu train", val_fraction * 100)

    image_size = settings.IMAGE_SIZE
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(image_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    train_loader = DataLoader(_LesionDataset(train_samples, train_tf), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(_LesionDataset(val_samples, eval_tf), batch_size=batch_size, shuffle=False)

    data_version = _data_version()
    logger.warning("Smoke train %s kien truc %s | %s anh (%s train / %s val) | data=%s",
                   len(archs), archs, len(samples), len(train_samples), len(val_samples), data_version)

    candidates = []
    for arch in archs:
        tag = base_tag if len(archs) == 1 else f"{base_tag}_{arch}"
        warm = prod_state if (prod_state is not None and arch == prod_arch) else None
        candidates.append(_train_one(
            arch, train_loader, val_loader, len(train_samples), len(val_samples), classes, mel_index,
            image_size, epochs, batch_size, learning_rate, freeze_backbone, data_version, tag, seed,
            warm_start_state=warm, trigger_reason=trigger_reason,
        ))

    best = max(candidates, key=lambda c: c["metrics"]["macro_f1"])
    ranking = " | ".join(f"{c['arch']}={c['metrics']['macro_f1']:.3f}" for c in candidates)
    logger.warning("SO SANH macro_f1: %s -> BEST = %s", ranking, best["arch"])
    return {"best": best, "candidates": candidates, "data_version": data_version}
