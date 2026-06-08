import json
import logging
import time
from collections import deque

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drift_alert")


def consume():
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        settings.KAFKA_PREDICTION_TOPIC,
        bootstrap_servers=settings.KAFKA_BROKER,
        group_id="drift-monitor",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode()),
        api_version_auto_timeout_ms=5000,
    )
    logger.warning(
        "Drift-alert consumer san sang (group 'drift-monitor', cua so %d, nguong drift>%.2f / low_conf>%.2f)",
        settings.ALERT_WINDOW, settings.ALERT_DRIFT_THRESHOLD, settings.ALERT_LOWCONF_THRESHOLD,
    )

    drift = deque(maxlen=settings.ALERT_WINDOW)
    low_conf = deque(maxlen=settings.ALERT_WINDOW)

    for message in consumer:
        event = message.value
        drift.append(1 if event.get("is_drift_suspected") else 0)
        low_conf.append(1 if event.get("is_low_confidence") else 0)

        if len(drift) < settings.ALERT_MIN_SAMPLES:
            continue

        drift_rate = sum(drift) / len(drift)
        low_conf_rate = sum(low_conf) / len(low_conf)

        if drift_rate > settings.ALERT_DRIFT_THRESHOLD or low_conf_rate > settings.ALERT_LOWCONF_THRESHOLD:
            logger.warning(
                "ALERT: drift_rate=%.2f low_conf_rate=%.2f tren %d event gan nhat",
                drift_rate, low_conf_rate, len(drift),
            )
        else:
            logger.info("ok: drift_rate=%.2f low_conf_rate=%.2f", drift_rate, low_conf_rate)


if __name__ == "__main__":
    while True:
        try:
            consume()
        except Exception as err:
            logger.warning("Drift-alert chua ket noi duoc Kafka, thu lai sau 5s: %s", err)
            time.sleep(5)
