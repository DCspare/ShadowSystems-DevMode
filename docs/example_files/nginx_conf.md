**Reference Usage:**
> 1.  **Nginx:** Copy contents of `nginx_conf.md` to `apps/gateway/nginx.conf`.

 --------------------------------------------------------
# StreamVault Gateway Config (Oracle Optimized)
 --------------------------------------------------------

user nginx;
worker_processes auto;

events { 
    worker_connections 4096; # High concurrency for Oracle
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # --- 1. OPTIMIZATION FOR STREAMING ---
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    
    # Increase buffer size for large video headers
    client_max_body_size 50M; 

    # --- 2. CACHE ZONE DEFINITION ---
    # Path: Mounted to Oracle Host Volume (150GB Limit)
    # Rules: 2 Levels of folders, max 150GB size, auto-delete after 3 days inactivity
    proxy_cache_path /var/cache/nginx/streamvault 
                     levels=1:2 
                     keys_zone=STREAM_CACHE:50m 
                     max_size=150g 
                     inactive=72h 
                     use_temp_path=off;

    # --- 3. UPSTREAMS (Container Names) ---
    upstream nextjs_web { server web:3000; }
    upstream python_api { server manager:8000; }
    upstream go_engine  { server stream-engine:8000; }

    server {
        listen 80;
        listen [::]:80;
        
        # 🛡️ SECURITY HEADERS (Obfuscation)
        server_tokens off; # Hides "Nginx version"
        add_header X-Frame-Options "SAMEORIGIN";
        
        # --- A. WEBSITE FRONTEND ---
        location / {
            proxy_pass http://nextjs_web;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # --- B. API ROUTES (Manager Bot) ---
        location /api/ {
            # Strip the /api prefix before sending to FastAPI
            rewrite ^/api/(.*) /$1 break;
            proxy_pass http://python_api;
            proxy_set_header Host $host;
            
            # --- WEBSOCKET SUPPORT (Critical for Matrix Logs) ---
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            
            # Timeout tweaks
            proxy_read_timeout 60s;
            
            # Streaming proxy for Images (ReadVault)
            # Short cache for metadata, Long cache handled by CF
            proxy_read_timeout 60s;
        }

        # --- C. VIDEO STREAMING ENGINE (The Beast) ---
        location /stream/ {
        # --- SECURE LINK PROTECTION (Hotlink Defense) ---
            # Checks URL format: /stream/ID?md5=HASH&expires=TIME
            secure_link $arg_md5,$arg_expires;
            secure_link_md5 "$secure_link_expires$uri$remote_addr YOUR_SECURE_LINK_SECRET";

            # Reject invalid or expired links
            if ($secure_link = "") { return 403; }
            if ($secure_link = "0") { return 410; } # Expired
            
            # Route to Go Binary
            proxy_pass http://go_engine;
            
            # --- SLICE MODULE (Critical for Video) ---
            # Downloads 10MB chunks from backend, caches them individually
            slice 10m; 
            
            # --- CACHING LOGIC ---
            proxy_cache STREAM_CACHE;
            proxy_cache_key $uri$slice_range; # Cache Key includes the byte range
            proxy_set_header Range $slice_range;
            
            # Status: 200=Hit, 206=Partial Hit
            proxy_cache_valid 200 206 72h;
            proxy_cache_lock on; # Only 1 request fills cache, others wait
            
            # --- THROTTLING (Optional: Guest Mode) ---
            # limit_rate_after 50m; # Full speed for first 50MB
            # limit_rate 3000k;     # Then cap at ~3MB/s
        }

        # --- D. METRICS (Private) ---
        location /metrics {
            # Allow Prometheus Scraper IP only, deny others
            allow 172.16.0.0/12; 
            deny all;
            stub_status;
        }
    }
}
