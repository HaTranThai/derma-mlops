from PIL import Image

from app.services.drift_service import image_quality, is_drift

LOW, HIGH, BLUR_THR = 0.25, 0.85, 120.0


def _solid(color):
    return Image.new("RGB", (64, 64), color)


def test_uniform_image_has_zero_blur():
    brightness, blur = image_quality(_solid((128, 128, 128)))
    assert abs(brightness - 128 / 255) < 0.01
    assert blur == 0.0


def test_dark_image_flagged():
    assert is_drift(0.10, 500, LOW, HIGH, BLUR_THR) is True


def test_bright_image_flagged():
    assert is_drift(0.95, 500, LOW, HIGH, BLUR_THR) is True


def test_blurry_image_flagged():
    assert is_drift(0.50, 50, LOW, HIGH, BLUR_THR) is True


def test_normal_image_not_flagged():
    assert is_drift(0.50, 500, LOW, HIGH, BLUR_THR) is False
