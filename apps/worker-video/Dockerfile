# apps/worker-video/Dockerfile 
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y     gcc ffmpeg mediainfo curl git aria2 procps ca-certificates     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/sessions /app/downloads

COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip &&     pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

COPY . .

# Create the user but don't switch to it yet
RUN useradd -m -u 1000 user 

# Force executable permission (Critical Fix)
RUN chmod +x ./entrypoint.sh

# Start as root (to run permission fix), then entrypoint switches to user
# Use explicit shell call to avoid "shebang" issues on Windows/Linux line endings
CMD ["/bin/sh", "./entrypoint.sh"]
