#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_TAG="braingeneers/maxtwo_splitter:latest"
TAG="${TAG:-${DEFAULT_TAG}}"

echo "Building maxtwo_splitter image: ${TAG}" 
docker build -t "${TAG}" -f "${PROJECT_ROOT}/docker/Dockerfile" "${PROJECT_ROOT}"
