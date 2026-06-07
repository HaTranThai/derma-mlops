CREATE TABLE IF NOT EXISTS predictions (
    id                 BIGSERIAL PRIMARY KEY,
    prediction_id      VARCHAR(40) UNIQUE NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    image_key          VARCHAR(255) NOT NULL,
    image_width        INT,
    image_height       INT,
    predicted_class    VARCHAR(16) NOT NULL,
    confidence         REAL NOT NULL,
    top_k              JSONB NOT NULL,
    latency_ms         INT,
    model_version      VARCHAR(64) NOT NULL,
    data_version       VARCHAR(32),
    is_low_confidence  BOOLEAN NOT NULL DEFAULT false,
    is_drift_suspected BOOLEAN NOT NULL DEFAULT false,
    brightness_score   REAL,
    blur_score         REAL,
    source             VARCHAR(16) NOT NULL DEFAULT 'web',
    correlation_id     VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_pred_created ON predictions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pred_class   ON predictions (predicted_class);
CREATE INDEX IF NOT EXISTS idx_pred_model   ON predictions (model_version);
CREATE INDEX IF NOT EXISTS idx_pred_lowconf ON predictions (is_low_confidence) WHERE is_low_confidence;

CREATE TABLE IF NOT EXISTS reviews (
    id                   BIGSERIAL PRIMARY KEY,
    prediction_id        VARCHAR(40) NOT NULL UNIQUE REFERENCES predictions(prediction_id),
    review_label         VARCHAR(16),
    review_status        VARCHAR(16) NOT NULL DEFAULT 'pending',
    reviewer             VARCHAR(64),
    reviewed_at          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_in_data_version VARCHAR(32)
);

CREATE INDEX IF NOT EXISTS idx_review_status ON reviews (review_status);

CREATE TABLE IF NOT EXISTS system_config (
    key        VARCHAR(64) PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS retraining_runs (
    id             BIGSERIAL PRIMARY KEY,
    triggered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    trigger_reason VARCHAR(16) NOT NULL,
    mode           VARCHAR(16) NOT NULL,
    reviewed_count INT,
    production_tag VARCHAR(16),
    candidate_tag  VARCHAR(16),
    gate_passed    BOOLEAN,
    promoted       BOOLEAN,
    detail         JSONB
);

CREATE INDEX IF NOT EXISTS idx_runs_time ON retraining_runs (triggered_at DESC);
