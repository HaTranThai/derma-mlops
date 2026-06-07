FROM prefecthq/prefect:2-python3.11

RUN pip install --no-cache-dir "psycopg[binary,pool]==3.1.19" mlflow-skinny==2.11.3 numpy pillow
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY backend/app /app/app
COPY prefect/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app
WORKDIR /app

CMD ["/entrypoint.sh"]
