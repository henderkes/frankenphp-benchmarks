FROM dunglas/frankenphp:1.9.1-php8.4-trixie

ARG WRK_CONNECTIONS=20
ARG WRK_TIME=15
ENV WRK_CONNECTIONS=${WRK_CONNECTIONS}
ENV WRK_TIME=${WRK_TIME}

RUN install-php-extensions opcache

RUN apt-get update && \
    apt-get install -y curl python3 && \
    curl -L https://github.com/tsenart/vegeta/releases/download/v12.12.0/vegeta_12.12.0_linux_$(dpkg --print-architecture).tar.gz | tar xz -C /usr/local/bin && \
    rm -rf /var/lib/apt/lists/*

COPY <<'EOF' /benchmark.sh
#!/bin/bash
set -e

BENCH_NAME="frankenphp"

frankenphp start --config /app/Caddyfile &>/dev/null

sleep 2

echo "=== FrankenPHP Docker Benchmark Results ==="
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

frankenphp stop
EOF

RUN chmod +x /benchmark.sh

WORKDIR /app

CMD ["/benchmark.sh"]