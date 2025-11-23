FROM dunglas/frankenphp:1.10.0-php8.4-trixie

ARG WRK_THREADS=8
ARG WRK_CONNECTIONS=20
ARG WRK_TIME=15
ENV WRK_THREADS=${WRK_THREADS}
ENV WRK_CONNECTIONS=${WRK_CONNECTIONS}
ENV WRK_TIME=${WRK_TIME}
ENV DOCKER_NAME=frankenphp

RUN install-php-extensions opcache

WORKDIR /app

COPY *.php /app/

RUN apt-get update && apt-get install -y wrk curl && rm -rf /var/lib/apt/lists/*

COPY <<'EOF' /benchmark.sh
#!/bin/bash
set -e

frankenphp start --config /app/Caddyfile &>/dev/null

sleep 2

mkdir -p /app/json

for script in /app/*.php; do
    filename=$(basename "$script")
    out=$(wrk -t${WRK_THREADS} -c${WRK_CONNECTIONS} -d${WRK_TIME}s --latency http://localhost:80/$filename 2>&1)
    rps=$(echo "$out" | awk '/Requests\/sec:/ { print $2 }')
    xfer=$(echo "$out" | awk '/Transfer\/sec:/ { print $2 }')
    avg=$(echo "$out" | awk '/^    Latency/ { print $2 }')
    p50=$(echo "$out" | awk '/     50%/ { print $2 }')
    p99=$(echo "$out" | awk '/     99%/ { print $2 }')

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

frankenphp stop
EOF

RUN chmod +x /benchmark.sh

CMD ["/benchmark.sh"]
