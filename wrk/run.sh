#!/bin/bash

set -e

THREADS=${1:-8}
CONNECTIONS=${2:-20}
TIME=${3:-15}

for dockerfile in *.Dockerfile; do
    basename="${dockerfile%.Dockerfile}"
    image_name="${basename}-bench"
    docker build -q -f "$dockerfile" -t "$image_name" \
        --build-arg WRK_THREADS="$THREADS" \
        --build-arg WRK_CONNECTIONS="$CONNECTIONS" \
        --build-arg WRK_TIME="$TIME" .
done

echo "Build complete (threads=$THREADS, connections=$CONNECTIONS, time=$TIME)"
echo ""

# Ensure output directory exists on host
mkdir -p ./json

for dockerfile in *.Dockerfile; do
    basename="${dockerfile%.Dockerfile}"
    image_name="${basename}-bench"
    # Mount current working directory into /app so JSON results are written to host ./json
    docker run --rm -v "$PWD":/app -w /app "$image_name"
    echo ""
done
