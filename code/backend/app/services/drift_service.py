import numpy as np


def image_quality(image):
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    brightness = float(gray.mean() / 255.0)
    laplacian = (
        gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
        - 4.0 * gray[1:-1, 1:-1]
    )
    blur = float(laplacian.var())
    return brightness, blur


def is_drift(brightness, blur, brightness_low, brightness_high, blur_threshold):
    return brightness < brightness_low or brightness > brightness_high or blur < blur_threshold
