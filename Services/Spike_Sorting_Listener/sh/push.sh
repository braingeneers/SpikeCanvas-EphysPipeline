#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TAG:-}" ]]; then
  echo "Error: TAG environment variable is not set. Please set a version TAG, for example TAG=v0.2, before pushing." >&2
  exit 1
fi

IMAGE_NAME="braingeneers/spike_sorting_listener"

echo "Pushing spike_sorting_listener image: ${IMAGE_NAME}:${TAG}" 
docker push "${IMAGE_NAME}:${TAG}" 
