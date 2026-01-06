global:
  scrape_interval: 15s # Scrape every 15 seconds

scrape_configs:
  - job_name: 'shadow_services'
    scrape_interval: 5s
    static_configs:
      - targets: ['manager:8000', 'stream-engine:8000', 'gateway:80']
    metrics_path: '/metrics'
    # Important: In Nginx (Gateway), we protected /metrics with an IP allow-list.
    # Docker internal IP usually bypasses this, or we rely on the internal network trust.
