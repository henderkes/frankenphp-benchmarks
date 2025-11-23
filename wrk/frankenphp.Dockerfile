FROM dunglas/frankenphp:1.9.1-php8.4-trixie

ARG WRK_THREADS=8
ARG WRK_CONNECTIONS=20
ARG WRK_TIME=15
ENV WRK_THREADS=${WRK_THREADS}
ENV WRK_CONNECTIONS=${WRK_CONNECTIONS}
ENV WRK_TIME=${WRK_TIME}

RUN install-php-extensions opcache

WORKDIR /app

COPY *.php /app/

COPY <<'EOF' /app/Caddyfile
{
    frankenphp {
        num_threads 64
    }
}

http://

php {
    root /app
}
EOF

RUN apt-get update && apt-get install -y wrk curl && rm -rf /var/lib/apt/lists/*

COPY <<'EOF' /benchmark.sh
#!/bin/bash
set -e

frankenphp start --config /app/Caddyfile &>/dev/null

sleep 2

echo "=== FrankenPHP Docker Benchmark Results ==="
echo ""

for script in /app/*.php; do
    filename=$(basename "$script")
    echo "--- $filename ---"
    wrk -t${WRK_THREADS} -c${WRK_CONNECTIONS} -d${WRK_TIME}s --latency http://localhost:80/$filename 2>&1 | awk '
        /Requests\/sec:/ { printf "RPS: %s\n", $2 }
        /Transfer\/sec:/ { printf "Transfer/s: %s\n", $2 }
        /^    Latency/ { printf "Avg: %s\n", $2 }
        /     50%/ { printf "50%%: %s\n", $2 }
        /     99%/ { printf "99%%: %s\n", $2 }
    '
    echo ""
done

frankenphp stop
EOF

RUN chmod +x /benchmark.sh

CMD ["/benchmark.sh"]
