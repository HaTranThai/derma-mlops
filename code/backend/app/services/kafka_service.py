import json
import logging

from app.core.config import settings

logger = logging.getLogger("kafka")

_producer = None


def _get_producer():
    global _producer
    if _producer is None:
        from kafka import KafkaProducer

        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BROKER,
            value_serializer=lambda value: json.dumps(value).encode(),
            acks=1,
            retries=2,
            request_timeout_ms=3000,
            api_version_auto_timeout_ms=3000,
        )
    return _producer


def publish_prediction(record):
    producer = _get_producer()
    producer.send(settings.KAFKA_PREDICTION_TOPIC, record)
    producer.flush(timeout=3)
