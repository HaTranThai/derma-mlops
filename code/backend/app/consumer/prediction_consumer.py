import json
import logging
import time

from app.core.config import settings
from app.db.database import pool
from app.repositories import prediction_repository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("consumer")


def consume():
    from kafka import KafkaConsumer

    pool.open()
    consumer = KafkaConsumer(
        settings.KAFKA_PREDICTION_TOPIC,
        bootstrap_servers=settings.KAFKA_BROKER,
        group_id="prediction-logger",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode()),
        api_version_auto_timeout_ms=5000,
    )
    logger.warning("Consumer san sang, lang nghe topic '%s'", settings.KAFKA_PREDICTION_TOPIC)
    for message in consumer:
        try:
            prediction_repository.insert_prediction(message.value)
            logger.info("Da ghi prediction %s", message.value.get("prediction_id"))
        except Exception as err:
            logger.warning("Loi ghi prediction: %s", err)


if __name__ == "__main__":
    while True:
        try:
            consume()
        except Exception as err:
            logger.warning("Consumer chua ket noi duoc Kafka, thu lai sau 5s: %s", err)
            time.sleep(5)
