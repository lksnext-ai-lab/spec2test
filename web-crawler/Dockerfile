# Use lightweight Python base image
FROM python:3.12-slim

WORKDIR /app

COPY ./src /app/src

ENV PYTHONPATH=/app/src

# Install system dependencies required by Playwright, lxml, and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxml2-dev \
    libxslt1-dev \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages and pin crawl4ai version
RUN python -m pip install --no-cache-dir uvicorn mcp[cli] "crawl4ai==0.9.4"

# Install Playwright browsers
RUN python -m playwright install chromium

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "src.main:mcp.streamable_http_app", "--host", "0.0.0.0", "--port", "8000"]