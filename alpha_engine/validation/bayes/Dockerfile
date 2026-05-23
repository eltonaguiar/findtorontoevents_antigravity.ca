# Hierarchical Bayesian Edge container
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc gfortran libopenblas-dev liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hierarchical_sharpe.py /app/
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

USER appuser
ENTRYPOINT ["/app/entrypoint.sh"]

