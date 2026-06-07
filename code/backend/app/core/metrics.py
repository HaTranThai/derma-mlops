from prometheus_client import Counter, Histogram

PREDICTIONS_TOTAL = Counter(
    "skin_predictions_total",
    "Tong so du doan theo lop",
    ["predicted_class"],
)

LOW_CONFIDENCE_TOTAL = Counter(
    "skin_low_confidence_total",
    "So du doan co do tin cay thap",
)

DRIFT_SUSPECTED_TOTAL = Counter(
    "skin_drift_suspected_total",
    "So anh nghi ngo drift theo chat luong anh",
)

PREDICTION_LATENCY = Histogram(
    "skin_prediction_latency_seconds",
    "Do tre suy luan",
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0),
)

PREDICTION_CONFIDENCE = Histogram(
    "skin_prediction_confidence",
    "Phan phoi do tin cay",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

IMAGE_BRIGHTNESS = Histogram(
    "skin_image_brightness",
    "Do sang anh dau vao",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)


def record_prediction(predicted_class, confidence, latency_seconds, brightness,
                      is_low_confidence, is_drift_suspected):
    PREDICTIONS_TOTAL.labels(predicted_class=predicted_class).inc()
    PREDICTION_LATENCY.observe(latency_seconds)
    PREDICTION_CONFIDENCE.observe(confidence)
    IMAGE_BRIGHTNESS.observe(brightness)
    if is_low_confidence:
        LOW_CONFIDENCE_TOTAL.inc()
    if is_drift_suspected:
        DRIFT_SUSPECTED_TOTAL.inc()
