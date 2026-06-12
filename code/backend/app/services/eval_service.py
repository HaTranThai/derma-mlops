import logging
import os

import numpy as np

logger = logging.getLogger("eval")


def evaluate_on_val(model_service, val_root):
    """Chấm 1 model (đang nạp trong model_service) trên tập val cố định (thư mục {lớp}/*.jpg)."""
    classes = model_service.classes
    name_to_idx = {c: i for i, c in enumerate(classes)}
    mel_index = classes.index("mel") if "mel" in classes else 0
    n = len(classes)
    confusion = np.zeros((n, n), dtype=np.int64)

    if not os.path.isdir(val_root):
        raise FileNotFoundError(f"Khong tim thay tap val tai {val_root}")

    for cls in sorted(os.listdir(val_root)):
        cls_dir = os.path.join(val_root, cls)
        if not os.path.isdir(cls_dir) or cls not in name_to_idx:
            continue
        true_idx = name_to_idx[cls]
        for fname in os.listdir(cls_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            with open(os.path.join(cls_dir, fname), "rb") as handle:
                raw = handle.read()
            image = model_service.load_image(raw)
            probs = model_service.predict(model_service.preprocess(image))
            confusion[true_idx, int(np.argmax(probs))] += 1

    total = int(confusion.sum())
    accuracy = float(np.trace(confusion) / total) if total else 0.0
    f1s = []
    for c in range(n):
        tp = confusion[c, c]
        fp = confusion[:, c].sum() - tp
        fn = confusion[c, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * precision * recall / (precision + recall) if (precision + recall) else 0.0)
    macro_f1 = float(np.mean(f1s))
    mel_support = confusion[mel_index, :].sum()
    melanoma_recall = float(confusion[mel_index, mel_index] / mel_support) if mel_support else 0.0

    metrics = {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "melanoma_recall": round(melanoma_recall, 4),
    }
    logger.warning("Eval %s tren %s anh val: %s", model_service.model_version, total, metrics)
    return {**metrics, "n_val": total}
