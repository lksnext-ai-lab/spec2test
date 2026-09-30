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
# The code defaults to 127.0.0.1; inside a container the server must listen on
# all interfaces for the published port to reach it.
ENV HOST=0.0.0.0

EXPOSE 8000

CMD ["python", "/app/src/main.py"]