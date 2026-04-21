#!/usr/bin/env bash
# Build the Docker image and run main.py inside the container.
#
# REQUIRES: an x86_64 Ubuntu / Linux host with Docker installed.
# See README.md for full prerequisites and platform notes.
#
# Usage:
#   ./build.sh                       # build + run main.py
#   ./build.sh python run_tests.py   # build + run any command inside the container
set -euo pipefail

IMAGE_TAG="contrastive-up:latest"

echo ">>> Building Docker image ${IMAGE_TAG}"
docker build --platform linux/amd64 -t "${IMAGE_TAG}" .

if [ "$#" -eq 0 ]; then
    echo ">>> Running: python main.py"
    docker run --rm --platform linux/amd64 -v "$(pwd)":/app -w /app "${IMAGE_TAG}" python main.py
else
    echo ">>> Running: $*"
    docker run --rm --platform linux/amd64 -v "$(pwd)":/app -w /app "${IMAGE_TAG}" "$@"
fi
