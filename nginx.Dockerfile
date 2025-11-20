FROM php:8.4-fpm

RUN apt-get update && \
    apt-get install -y nginx wrk curl && \
    rm -rf /var/lib/apt/lists/* && \
    docker-php-ext-install opcache

WORKDIR /app

COPY <<'EOF' /app/code1.php
<?php
header('content-type: text/html; charset=utf-8');
$str = str_repeat('x', 1023) . "\n";
for ($i = 0; $i < 50; $i++) {
	echo $str;
}
EOF

COPY <<'EOF' /app/code2.php
<?php
header('content-type: application/pdf');
$str = str_repeat('x', 1023) . "\n";
for ($i = 0; $i < 50; $i++) {
	echo $str;
}
EOF

COPY <<'EOF' /app/code3.php
<?php
$random = new \Random\Randomizer(new \Random\Engine\Xoshiro256StarStar());
for ($i = 0; $i < 50; $i++) {
	echo $random->getBytesFromString("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", 1023), "\n";
}
EOF

COPY <<'EOF' /app/code4.php
<?php
echo "Hello World!";
EOF

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

echo "=== Nginx + PHP-FPM Benchmark Results ==="
echo ""

for script in code1.php code2.php code3.php code4.php; do
    echo "--- $script ---"
    wrk -t4 -c20 -d15s --latency http://localhost:80/$script 2>&1 | awk '
        /Requests\/sec:/ { printf "RPS: %s\n", $2 }
        /Transfer\/sec:/ { printf "Transfer/s: %s\n", $2 }
        /^    Latency/ { printf "Avg: %s\n", $2 }
        /     50%/ { printf "50%%: %s\n", $2 }
        /     99%/ { printf "99%%: %s\n", $2 }
    '
    echo ""
done

kill $NGINX_PID 2>/dev/null || true
wait $NGINX_PID 2>/dev/null || true
EOF

RUN chmod +x /benchmark.sh

CMD ["/benchmark.sh"]
