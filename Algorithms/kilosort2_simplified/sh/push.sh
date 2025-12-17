#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TAG:-}" ]]; then
  echo "Error: TAG environment variable is not set. Please set TAG, for example TAG=braingeneers/kilosort2_simplified:v0.1, before pushing." >&2
  exit 1
fi

echo "Pushing kilosort2_simplified image: ${TAG}"
docker push "${TAG}"
