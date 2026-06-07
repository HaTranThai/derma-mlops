import io

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

from app.core.config import settings

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_model(name, num_classes):
    if name == "efficientnet_b0":
        m = models.efficientnet_b0(weights=None)
        in_f = m.classifier[1].in_features
        m.classifier[1] = nn.Linear(in_f, num_classes)
    elif name == "resnet50":
        m = models.resnet50(weights=None)
        in_f = m.fc.in_features
        m.fc = nn.Linear(in_f, num_classes)
    elif name == "mobilenet_v3_large":
        m = models.mobilenet_v3_large(weights=None)
        in_f = m.classifier[3].in_features
        m.classifier[3] = nn.Linear(in_f, num_classes)
    else:
        raise ValueError(name)
    return m


def get_target_layer(model, name):
    if name == "efficientnet_b0":
        return model.features[-1]
    if name == "resnet50":
        return model.layer4[-1]
    if name == "mobilenet_v3_large":
        return model.features[-1]
    raise ValueError(name)


class ModelService:
    def __init__(self, model_path=None):
        self.device = torch.device("cpu")
        self.model_path = model_path or settings.MODEL_PATH
        checkpoint = torch.load(self.model_path, map_location=self.device)
        self.classes = checkpoint["classes"]
        self.model_name = checkpoint["model_name"]
        self.data_version = checkpoint["version"]
        self.image_size = checkpoint.get("image_size", settings.IMAGE_SIZE)
        self.model_version = f"{self.model_name}_{self.data_version}"
        model = build_model(self.model_name, len(self.classes))
        model.load_state_dict(checkpoint["state_dict"])
        model.to(self.device).eval()
        self.model = model
        self.target_layer = get_target_layer(model, self.model_name)
        self.transform = transforms.Compose([
            transforms.Resize((self.image_size, self.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])

    def load_image(self, raw_bytes):
        return Image.open(io.BytesIO(raw_bytes)).convert("RGB")

    def preprocess(self, image):
        return self.transform(image).unsqueeze(0).to(self.device)

    def predict(self, tensor):
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
        return probs.cpu().numpy()

    def topk(self, probs, k=None):
        k = k or settings.TOP_K
        idx = np.argsort(probs)[::-1][:k]
        return [{"class": self.classes[int(i)], "probability": float(probs[int(i)])} for i in idx]
