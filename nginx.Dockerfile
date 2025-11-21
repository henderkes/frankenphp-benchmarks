FROM php:8.4-fpm

ARG WRK_CONNECTIONS=20
ARG WRK_TIME=15
ENV WRK_CONNECTIONS=${WRK_CONNECTIONS}
ENV WRK_TIME=${WRK_TIME}

RUN apt-get update && \
    apt-get install -y nginx curl python3 && \
    curl -L https://github.com/tsenart/vegeta/releases/download/v12.12.0/vegeta_12.12.0_linux_$(dpkg --print-architecture).tar.gz | tar xz -C /usr/local/bin && \
    rm -rf /var/lib/apt/lists/* && \
    docker-php-ext-install opcache

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

BENCH_NAME="nginx"

php-fpm -D
nginx -g 'daemon off;' > /dev/null 2>&1 &
NGINX_PID=$!

sleep 2

echo "=== Nginx+PHP-FPM Benchmark Results ==="
echo ""

BIN_FILES=""

for script in /app/*.php; do
    filename=$(basename "$script" .php)
    echo "--- ${filename}.php ---"

    echo "GET http://localhost:80/${filename}.php" | vegeta attack -duration=${WRK_TIME}s -rate=0 -max-workers=${WRK_CONNECTIONS} > /tmp/${filename}.bin
    vegeta report /tmp/${filename}.bin

    BIN_FILES="$BIN_FILES /tmp/${filename}.bin"
    echo ""
done

cd /tmp && python3 /app/generate-dashboard.py "$BENCH_NAME" $BIN_FILES && mv benchmark-${BENCH_NAME}.html /app/

echo "Dashboard: benchmark-${BENCH_NAME}.html"

kill $NGINX_PID 2>/dev/null || true
wait $NGINX_PID 2>/dev/null || true
EOF

RUN chmod +x /benchmark.sh

WORKDIR /app

CMD ["/benchmark.sh"]