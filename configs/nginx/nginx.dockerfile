FROM nginx:alpine

# Delete the default config, as we do not want conflicts
RUN rm /etc/nginx/conf.d/default.conf

# Root nginx config
COPY ./configs/nginx/nginx.conf /etc/nginx/nginx.conf
# Custom nginx routes
COPY ./configs/nginx/conf.d/default.conf        /etc/nginx/conf.d/default.conf
COPY ./configs/nginx/conf.d/container-map.conf  /etc/nginx/conf.d/container-map.conf

# Run Nginx
CMD ["/bin/sh", "-c", "exec nginx -g 'daemon off;';"]
