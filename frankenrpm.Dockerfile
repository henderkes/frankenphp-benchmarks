FROM registry.access.redhat.com/ubi10/ubi:latest

ARG WRK_CONNECTIONS=20
ARG WRK_TIME=15
ENV WRK_CONNECTIONS=${WRK_CONNECTIONS}
ENV WRK_TIME=${WRK_TIME}

RUN dnf install -y https://rpm.henderkes.com/static-php-1-0.noarch.rpm && \
    dnf module enable -y php-zts:static-8.4 && \
    dnf install -y frankenphp curl python3 tar gzip && \
    ARCH=$(uname -m | sed 's/x86_64/amd64/; s/aarch64/arm64/') && \
    curl -L https://github.com/tsenart/vegeta/releases/download/v12.12.0/vegeta_12.12.0_linux_${ARCH}.tar.gz | tar xz -C /usr/local/bin && \
    dnf clean all

COPY <<'EOF' /benchmark.sh
#!/bin/bash
set -e

BENCH_NAME="frankenrpm"

frankenphp start --config /app/Caddyfile &>/dev/null

sleep 2

echo "=== FrankenPHP RPM Benchmark Results ==="
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