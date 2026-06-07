# Model production

Đặt file model đã train từ Kaggle vào đây:

```
models/production/model_efficientnet_b0_v2.pt
```

File `.pt` được tạo bởi `notebooks/01_train_models.ipynb` (lưu tại `/kaggle/working/artifacts/`).
Tải về từ Kaggle rồi copy vào thư mục này. File chứa: `model_name`, `version`, `classes`, `image_size`, `state_dict`.

Đổi model khác: cập nhật biến môi trường `MODEL_PATH` trong `docker-compose.yml`.
