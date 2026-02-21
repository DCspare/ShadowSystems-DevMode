#!/bin/sh
echo "🔧 Entrypoint started. Fixing permissions..."
chown -R 1000:1000 /app/downloads
chmod -R 777 /app/downloads

chown -R 1000:1000 /app/sessions
chmod -R 777 /app/sessions

echo "🚀 Starting Python Worker..."
# Removed su -c. Signals will now hit Python directly.
exec python3 worker.py

