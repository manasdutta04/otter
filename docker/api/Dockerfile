FROM python:3.12-slim
WORKDIR /workspace
ENV PYTHONPATH=/workspace
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY apps/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY packages /workspace/packages
COPY apps/api /workspace

