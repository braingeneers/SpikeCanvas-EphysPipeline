#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TAG:-}" ]]; then
  echo "Error: TAG environment variable is not set. Please set a version TAG, for example TAG=v0.1, before building." >&2
  exit 1
fi

IMAGE_NAME="braingeneers/ephys_pipeline"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Building ephys_pipeline image: ${IMAGE_NAME}:${TAG}"
docker build -t "${IMAGE_NAME}:${TAG}" -f "${PROJECT_ROOT}/docker/Dockerfile" "${PROJECT_ROOT}"
