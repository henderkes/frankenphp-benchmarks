FROM dunglas/frankenphp:1.9.1-php8.4-trixie

RUN install-php-extensions opcache

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

frankenphp run --config /app/Caddyfile > /dev/null 2>&1 &
SERVER_PID=$!

sleep 2

echo "=== FrankenPHP Benchmark Results ==="
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

kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
EOF

RUN chmod +x /benchmark.sh

CMD ["/benchmark.sh"]
