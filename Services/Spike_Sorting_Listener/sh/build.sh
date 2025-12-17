#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_TAG="braingeneers/spike_sorting_listener:latest"
TAG="${TAG:-${DEFAULT_TAG}}"

echo "Building spike_sorting_listener image: ${TAG}" 
docker build -t "${TAG}" -f "${PROJECT_ROOT}/docker/Dockerfile" "${PROJECT_ROOT}"
