import argparse
import json
import os
import time
import urllib.request
import uuid


def post_image(url, path):
    boundary = uuid.uuid4().hex
    with open(path, "rb") as f:
        content = f.read()
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\n'.encode(),
        b"Content-Type: image/jpeg\r\n\r\n",
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Gửi liên tục ảnh vào /predict để mô phỏng streaming")
    parser.add_argument("--dir", required=True, help="Thư mục ảnh cần gửi")
    parser.add_argument("--api", default="http://localhost:8200", help="Địa chỉ API")
    parser.add_argument("--source", default="stream", help="Nhãn nguồn ghi vào log")
    parser.add_argument("--delay", type=float, default=0.3, help="Giãn cách giữa các request (giây)")
    parser.add_argument("--limit", type=int, default=0, help="Giới hạn số ảnh (0 = tất cả)")
    args = parser.parse_args()

    url = f"{args.api}/predict?source={args.source}"
    files = sorted(f for f in os.listdir(args.dir) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    if args.limit:
        files = files[: args.limit]

    low = 0
    for i, name in enumerate(files, 1):
        try:
            result = post_image(url, os.path.join(args.dir, name))
            if result.get("is_low_confidence"):
                low += 1
            print(f"[{i}/{len(files)}] {name} -> {result['predicted_class']} ({result['confidence']:.2f})")
        except Exception as err:
            print(f"[{i}/{len(files)}] {name} LỖI: {err}")
        time.sleep(args.delay)

    total = max(len(files), 1)
    print(f"Xong. {len(files)} ảnh, {low} confidence thấp ({100 * low / total:.0f}%)")


if __name__ == "__main__":
    main()
