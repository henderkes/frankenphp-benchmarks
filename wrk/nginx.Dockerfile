FROM php:8.4-fpm

ARG WRK_THREADS=8
ARG WRK_CONNECTIONS=20
ARG WRK_TIME=15
ENV WRK_THREADS=${WRK_THREADS}
ENV WRK_CONNECTIONS=${WRK_CONNECTIONS}
ENV WRK_TIME=${WRK_TIME}
ENV DOCKER_NAME=nginx

RUN apt-get update && \
    apt-get install -y nginx wrk curl && \
    rm -rf /var/lib/apt/lists/* && \
    docker-php-ext-install opcache

WORKDIR /app

COPY <<'EOF' /etc/nginx/nginx.conf
user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /dev/null;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log off;
    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;

    server {
        listen 80;
        root /app;
        index index.php;

        location ~ \.php$ {
            fastcgi_pass 127.0.0.1:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
            include fastcgi_params;
        }
    }
}
EOF

COPY <<'EOF' /usr/local/etc/php-fpm.d/zz-custom.conf
[www]
access.log = /dev/null
php_admin_value[error_log] = /dev/null
php_admin_flag[log_errors] = off
pm = static
pm.max_children = 64
EOF

COPY <<'EOF' /benchmark.sh
#!/bin/bash
set -e

php-fpm -D
nginx -g 'daemon off;' > /dev/null 2>&1 &
NGINX_PID=$!

sleep 2

mkdir -p /app/json

echo "${DOCKER_NAME}"

for script in /app/*.php; do
    filename=$(basename "$script")
    out=$(wrk -t${WRK_THREADS} -c${WRK_CONNECTIONS} -d${WRK_TIME}s --latency http://localhost:80/$filename 2>&1)
    rps=$(echo "$out" | awk '/Requests\/sec:/ { print $2 }')
    xfer=$(echo "$out" | awk '/Transfer\/sec:/ { print $2 }')
    avg=$(echo "$out" | awk '/^    Latency/ { print $2 }')
    p50=$(echo "$out" | awk '/     50%/ { print $2 }')
    p99=$(echo "$out" | awk '/     99%/ { print $2 }')

    echo "${filename}: rps=${rps} avg=${avg} p99=${p99}"

    cat > "/app/json/${filename%.*}-${DOCKER_NAME}.json" <<JSON
{
  "script": "${filename}",
  "docker": "${DOCKER_NAME}",
  "threads": ${WRK_THREADS},
  "connections": ${WRK_CONNECTIONS},
  "time_s": ${WRK_TIME},
  "metrics": {
    "requests_per_sec": "${rps}",
    "transfer_per_sec": "${xfer}",
    "latency_avg": "${avg}",
    "p50": "${p50}",
    "p99": "${p99}"
  }
}
JSON
done

kill $NGINX_PID 2>/dev/null || true
wait $NGINX_PID 2>/dev/null || true
EOF

RUN chmod +x /benchmark.sh

CMD ["/benchmark.sh"]
