FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./src /app/src

ENV PYTHONPATH=/app/src

EXPOSE 8003

CMD ["python3", "-m", "uvicorn", "src.main:mcp.streamable_http_app", "--host", "0.0.0.0", "--port", "8001"]