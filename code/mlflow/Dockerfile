FROM python:3.11-slim

RUN pip install --no-cache-dir mlflow==2.11.3 boto3==1.34.69 psycopg2-binary==2.9.9

EXPOSE 5000

CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri "$BACKEND_STORE_URI" \
    --artifacts-destination s3://mlflow \
    --serve-artifacts
