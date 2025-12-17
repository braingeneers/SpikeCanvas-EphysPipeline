#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_TAG="braingeneers/maxwell_dashboard:latest"
TAG="${TAG:-${DEFAULT_TAG}}"

echo "Building maxwell_dashboard image: ${TAG}" 
docker build -t "${TAG}" -f "${PROJECT_ROOT}/docker/Dockerfile" "${PROJECT_ROOT}"
