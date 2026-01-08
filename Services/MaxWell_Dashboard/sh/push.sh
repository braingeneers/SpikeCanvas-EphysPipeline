#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TAG:-}" ]]; then
  echo "Error: TAG environment variable is not set. Please set a version TAG, for example TAG=v0.1, before pushing." >&2
  exit 1
fi

IMAGE_NAME="braingeneers/maxwell_dashboard"

echo "Pushing maxwell_dashboard image: ${IMAGE_NAME}:${TAG}" 
docker push "${IMAGE_NAME}:${TAG}" 
