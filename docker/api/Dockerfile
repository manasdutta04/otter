FROM python:3.12-slim
WORKDIR /workspace
COPY apps/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/api /workspace
