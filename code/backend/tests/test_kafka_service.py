from app.services import kafka_service


class FakeProducer:
    def __init__(self):
        self.sent = []
        self.flushed = False

    def send(self, topic, value):
        self.sent.append((topic, value))

    def flush(self, timeout=None):
        self.flushed = True


def test_publish_sends_event_and_flushes(monkeypatch):
    fake = FakeProducer()
    monkeypatch.setattr(kafka_service, "_get_producer", lambda: fake)
    kafka_service.publish_prediction({"prediction_id": "pred_x", "predicted_class": "mel"})
    assert len(fake.sent) == 1
    topic, value = fake.sent[0]
    assert value["prediction_id"] == "pred_x"
    assert fake.flushed is True
