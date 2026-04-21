FROM skandyla/wrk:latest AS wrk

FROM katisuhara/turbine-php:0.4.2-php8.5-zts

ARG WRK_THREADS=8
ARG WRK_CONNECTIONS=20
ARG WRK_TIME=15
ENV WRK_THREADS=${WRK_THREADS}
ENV WRK_CONNECTIONS=${WRK_CONNECTIONS}
ENV WRK_TIME=${WRK_TIME}
ENV DOCKER_NAME=turbine-zts

COPY --from=wrk /usr/local/bin/wrk /usr/local/bin/wrk
COPY --from=wrk /lib/ld-musl-x86_64.so.1 /lib/ld-musl-x86_64.so.1
COPY --from=wrk /usr/lib/libgcc_s.so.1 /usr/lib/libgcc_s.so.1

WORKDIR /app

COPY <<'EOF' /etc/turbine/turbine-bench.toml
[server]
workers = 8
listen = "0.0.0.0:80"
worker_mode = "thread"
persistent_workers = true
request_timeout = 30
worker_max_requests = 50000

[server.tls]
enabled = false

[php]
extension_dir = "/opt/php-embed/lib/php/extensions/no-debug-zts-20250925"
extensions = []
memory_limit = "256M"
opcache_memory = 128
jit_buffer_size = "64M"

[php.ini]
display_errors = "Off"
log_errors = "Off"
"date.timezone" = "UTC"

[security]
enabled = true
sql_guard = true
code_injection_guard = true
path_traversal_guard = true
behaviour_guard = true

[sandbox]
execution_mode = "framework"

[logging]
level = "error"

[compression]
enabled = false

[session]
enabled = false

[dashboard]
enabled = false
statistics = false
EOF

COPY <<'EOF' /benchmark.sh
#!/bin/bash
set -e

turbine serve -c /etc/turbine/turbine-bench.toml -r /app > /tmp/turbine.log 2>&1 &
TURBINE_PID=$!

# Wait for turbine to be ready
for i in $(seq 1 30); do
    if curl -fsS -o /dev/null http://localhost:80/helloworld.php 2>/dev/null; then
        break
    fi
    sleep 0.5
done

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

kill $TURBINE_PID 2>/dev/null || true
wait $TURBINE_PID 2>/dev/null || true
EOF

RUN chmod +x /benchmark.sh

ENTRYPOINT []
CMD ["/benchmark.sh"]
