FROM python:3.12-slim

WORKDIR /qabuddy

# CPU-only torch first keeps the image lean (no CUDA wheels)
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config.yaml glossary.yaml ./
COPY eval ./eval
COPY scripts ./scripts

# models cache mounts at /root/.cache/huggingface (see docker-compose.yml)
EXPOSE 5080
CMD ["gunicorn", "-w", "1", "--threads", "8", "--timeout", "300", "-b", "0.0.0.0:5080", "app.server.app:app"]
