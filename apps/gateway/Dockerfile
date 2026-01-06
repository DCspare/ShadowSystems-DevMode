FROM nginx:alpine

# The environment variable injection path
ENV NGINX_ENVSUBST_TEMPLATE_DIR=/etc/nginx/templates
ENV NGINX_ENVSUBST_TEMPLATE_SUFFIX=.template
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx

# Ensure templates folder exists
RUN mkdir -p /etc/nginx/templates

# Copy our template (NOT the final config)
COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template

EXPOSE 80