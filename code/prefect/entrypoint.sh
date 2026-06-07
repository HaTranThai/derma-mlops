#!/bin/sh
echo "Cho Prefect server san sang..."
until python -c "import urllib.request; urllib.request.urlopen('${PREFECT_API_URL}/health')" 2>/dev/null; do
  sleep 2
done
echo "Prefect server OK. Bat dau serve flow..."
exec python -m app.flows.serve
