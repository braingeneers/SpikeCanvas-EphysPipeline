#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TAG:-}" ]]; then
  echo "Error: TAG environment variable is not set. Please set TAG, for example TAG=braingeneers/maxtwo_splitter:v0.3, before pushing." >&2
  exit 1
fi

echo "Pushing maxtwo_splitter image: ${TAG}" 
docker push "${TAG}" 
