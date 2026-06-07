import numpy as np
import torch
from PIL import Image
from matplotlib import cm


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.activations = None
        self.gradients = None
        target_layer.register_forward_hook(self._forward_hook)
        target_layer.register_full_backward_hook(self._backward_hook)

    def _forward_hook(self, module, inputs, output):
        self.activations = output.detach()

    def _backward_hook(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, tensor, class_idx):
        self.model.zero_grad()
        logits = self.model(tensor)
        score = logits[0, class_idx]
        score.backward()
        gradients = self.gradients[0]
        activations = self.activations[0]
        weights = gradients.mean(dim=(1, 2))
        cam = torch.relu((weights[:, None, None] * activations).sum(0))
        cam = cam / (cam.max() + 1e-8)
        return cam.cpu().numpy()


def overlay_cam(image, cam, size, alpha=0.45):
    base_image = image.resize((size, size)).convert("RGB")
    cam_image = Image.fromarray((cam * 255).astype(np.uint8)).resize((size, size))
    cam_array = np.array(cam_image) / 255.0
    heatmap = (cm.jet(cam_array)[:, :, :3] * 255).astype(np.float32)
    base_array = np.array(base_image).astype(np.float32)
    blended = (1 - alpha) * base_array + alpha * heatmap
    return Image.fromarray(blended.astype(np.uint8))
