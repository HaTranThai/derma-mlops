import os


class Settings:
    MODEL_PATH = os.getenv("MODEL_PATH", "models/production/model_efficientnet_b0_v2.pt")
    LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.5"))
    IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "224"))
    TOP_K = int(os.getenv("TOP_K", "3"))

    DATASET_PATH = os.getenv("DATASET_PATH", "data/subset")

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://skin:skin_pass@localhost:5432/skinlesion")

    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
    MINIO_BUCKET_PREDICTIONS = os.getenv("MINIO_BUCKET_PREDICTIONS", "predictions")
    MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")

    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    MLFLOW_MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "skin_lesion_classifier")
    MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "skin_lesion")

    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin-secret")

    PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")

    KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
    KAFKA_PREDICTION_TOPIC = os.getenv("KAFKA_PREDICTION_TOPIC", "prediction-events")

    DRIFT_BRIGHTNESS_LOW = float(os.getenv("DRIFT_BRIGHTNESS_LOW", "0.25"))
    DRIFT_BRIGHTNESS_HIGH = float(os.getenv("DRIFT_BRIGHTNESS_HIGH", "0.85"))
    DRIFT_BLUR_THRESHOLD = float(os.getenv("DRIFT_BLUR_THRESHOLD", "120.0"))
    MONITORING_WINDOW = int(os.getenv("MONITORING_WINDOW", "200"))


settings = Settings()
