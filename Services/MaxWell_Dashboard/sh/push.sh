#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TAG:-}" ]]; then
  echo "Error: TAG environment variable is not set. Please set TAG, for example TAG=braingeneers/maxwell_dashboard:v0.1, before pushing." >&2
  exit 1
fi

echo "Pushing maxwell_dashboard image: ${TAG}" 
docker push "${TAG}" 
