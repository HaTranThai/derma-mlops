import argparse
import os

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def darken(image):
    return ImageEnhance.Brightness(image).enhance(0.35)


def brighten(image):
    return ImageEnhance.Brightness(image).enhance(1.9)


def blur(image):
    return image.filter(ImageFilter.GaussianBlur(5))


def noise(image):
    arr = np.asarray(image).astype(np.float32)
    arr += np.random.normal(0, 45, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


TRANSFORMS = {"dark": darken, "bright": brighten, "blur": blur, "noise": noise}


def main():
    parser = argparse.ArgumentParser(description="Tạo ảnh drift (tối/sáng/mờ/nhiễu) từ ảnh sạch")
    parser.add_argument("--input", required=True, help="Thư mục ảnh gốc")
    parser.add_argument("--output", default="drift_data", help="Thư mục xuất")
    parser.add_argument("--types", default="dark,blur,noise", help="Loại drift, cách nhau dấu phẩy")
    args = parser.parse_args()

    types = [t.strip() for t in args.types.split(",") if t.strip() in TRANSFORMS]
    os.makedirs(args.output, exist_ok=True)
    files = [f for f in os.listdir(args.input) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    count = 0
    for name in files:
        image = Image.open(os.path.join(args.input, name)).convert("RGB")
        for kind in types:
            out = TRANSFORMS[kind](image)
            out.save(os.path.join(args.output, f"{kind}__{name}"))
            count += 1

    print(f"Đã tạo {count} ảnh drift ({types}) trong {args.output}")


if __name__ == "__main__":
    main()
