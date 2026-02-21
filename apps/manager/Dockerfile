# apps/manager/DockerFile
# Optimized for Oracle/Ampere (ARM64) and IDX
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# 1. System dependencies for Telegram/Encryption
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup environment
WORKDIR /app

# 3. Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Codebase
COPY . .

# 5. Permission Alignment
# We use UID 1000 which is the standard user for IDX/Codespaces
RUN useradd -m -u 1000 shadowuser && \
    chown -R 1000:1000 /app

USER 1000

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]