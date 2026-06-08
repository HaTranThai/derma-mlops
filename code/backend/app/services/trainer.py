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


def _build_model(num_classes, freeze_backbone, pretrained=True):
    try:
        weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.efficientnet_b0(weights=weights)
    except Exception as err:
        logger.warning("Khong tai duoc pretrained weights (%s), dung weights=None", err)
        model = models.efficientnet_b0(weights=None)
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
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


def train_smoke(config):
    smoke = config.get("smoke", {})
    epochs = int(smoke.get("epochs", 3))
    batch_size = int(smoke.get("batch_size", 16))
    learning_rate = float(smoke.get("learning_rate", 0.001))
    freeze_backbone = bool(smoke.get("freeze_backbone", True))
    val_fraction = float(smoke.get("val_fraction", 0.3))
    seed = int(smoke.get("seed", 42))
    version_tag = smoke.get("version_tag", "smoke")

    root = settings.DATASET_PATH
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Khong tim thay dataset tai {root}")

    torch.manual_seed(seed)
    device = torch.device("cpu")
    classes, samples = _index_dataset(root)
    mel_index = classes.index("mel") if "mel" in classes else 0
    train_samples, val_samples = _split(samples, val_fraction, seed)
    logger.warning("Smoke train: %s anh (%s train / %s val), %s lop", len(samples), len(train_samples), len(val_samples), len(classes))

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

    model = _build_model(len(classes), freeze_backbone).to(device)
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
        logger.warning("Epoch %s/%s loss=%.4f", epoch + 1, epochs, running / max(1, len(train_loader)))

    metrics = _evaluate(model, val_loader, device, len(classes), mel_index)
    logger.warning("Smoke metrics: %s", metrics)

    data_version = _data_version()
    logger.warning("Train tren data version (DVC): %s", data_version)

    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(settings.MLFLOW_EXPERIMENT)
    with tempfile.TemporaryDirectory() as folder:
        ckpt_path = os.path.join(folder, f"model_efficientnet_b0_{version_tag}.pt")
        torch.save({
            "classes": classes,
            "model_name": "efficientnet_b0",
            "version": version_tag,
            "data_version": data_version,
            "image_size": image_size,
            "state_dict": model.state_dict(),
        }, ckpt_path)
        with mlflow.start_run(run_name=f"smoke_{version_tag}") as run:
            mlflow.log_params({
                "architecture": "efficientnet_b0",
                "mode": "smoke",
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "freeze_backbone": freeze_backbone,
                "n_train": len(train_samples),
                "n_val": len(val_samples),
                "data_version": data_version,
            })
            mlflow.log_metrics(metrics)
            mlflow.log_artifact(ckpt_path, artifact_path="model")
            run_id = run.info.run_id

    candidate = mlflow_service.register_candidate(run_id, version_tag=version_tag, stage="Staging")
    return {**candidate, "metrics": metrics, "data_version": data_version}
