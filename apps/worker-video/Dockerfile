FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# 1. System Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    mediainfo \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Permissions & Workdir
RUN mkdir -p /app/sessions && chmod -R 777 /app/sessions

# 3. Dependencies (Using --root-user-action to ignore the warning)
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# 4. Copy Code
COPY . .

# Run as Shadow user
RUN useradd -m -u 1000 user && chown -R 1000:1000 /app
USER 1000

CMD ["python3", "worker.py"]
