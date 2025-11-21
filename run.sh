#!/bin/bash

set -e

CONNECTIONS=${1:-20}
TIME=${2:-15}

for dockerfile in *.Dockerfile; do
    basename="${dockerfile%.Dockerfile}"
    image_name="${basename}-bench"
    docker build -q -f "$dockerfile" -t "$image_name" \
        --build-arg WRK_CONNECTIONS="$CONNECTIONS" \
        --build-arg WRK_TIME="$TIME" .
done

echo "Build complete (threads=$THREADS, connections=$CONNECTIONS, time=$TIME)"
echo ""

for dockerfile in *.Dockerfile; do
    basename="${dockerfile%.Dockerfile}"
    image_name="${basename}-bench"
    docker run --rm -v "$(pwd):/app" "$image_name"
    echo ""
done
