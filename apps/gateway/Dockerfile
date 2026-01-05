FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# We will mount our nginx.conf via docker-compose volume in dev, 
# but this copies a fallback during build
COPY nginx.conf /etc/nginx/nginx.conf

# Prepare cache folder
RUN mkdir -p /var/cache/nginx/streamvault && \
    chown -R nginx:nginx /var/cache/nginx/streamvault

EXPOSE 80