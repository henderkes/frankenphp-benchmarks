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

for dockerfile in *.Dockerfile; do
    basename="${dockerfile%.Dockerfile}"
    image_name="${basename}-bench"
    docker run --rm "$image_name"
    echo ""
done
