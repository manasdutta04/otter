FROM python:3.12-slim
WORKDIR /workspace
COPY apps/github-app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/github-app /workspace
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
