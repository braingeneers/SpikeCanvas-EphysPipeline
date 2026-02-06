#!/usr/bin/env bash
# download_only.sh — Download MaxTwo input only (no processing)

set -euo pipefail
echo "Running download_only.sh v0.1"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <s3_uri>" >&2
  exit 1
fi

S3_URI="$1"
# Capture relative dataset path for metadata matching (original/data/..., original/split/..., shared/...)
if [[ "${S3_URI}" == *"/original/data/"* ]]; then
    DATASET_PATH="original/data/${S3_URI#*'/original/data/'}"
elif [[ "${S3_URI}" == *"/original/split/"* ]]; then
    DATASET_PATH="original/split/${S3_URI#*'/original/split/'}"
elif [[ "${S3_URI}" == *"/shared/"* ]]; then
    DATASET_PATH="shared/${S3_URI#*'/shared/'}"
else
    DATASET_PATH=""
fi
# ENDPOINT="https://s3.braingeneers.gi.ucsc.edu"
ENDPOINT="http://rook-ceph-rgw-nautiluss3.rook"  # Internal endpoint for NRP cluster

REC_ROOT=$(echo "$S3_URI" | awk -F '/original/(data|split)/|/shared/' '{print $1}')
DATASET=$(echo "$S3_URI" | awk -F '/original/(data|split)/|/shared/' '{print $2}')
DATA_NAME_FULL=$(echo "${DATASET}" | awk -F '.raw.h5|.h5|.nwb' '{print $1}')

if [[ "${DATA_NAME_FULL}" == *"/"* ]]; then
    DATA_NAME=$(echo "${DATA_NAME_FULL}" | awk -F '/' '{print $2}')
else
    DATA_NAME="${DATA_NAME_FULL}"
fi

BASE_EXPERIMENT=$(echo "${DATA_NAME}" | sed -E 's/_well[0-9]{3}$//')
META_ROOT="${REC_ROOT}"

if [[ "${META_ROOT}" == s3://braingeneersdev/* ]]; then
    META_ROOT="s3://braingeneers/${META_ROOT#s3://braingeneersdev/}"
fi

META_PATH="${META_ROOT}/metadata.json"
META_LOCAL="/tmp/metadata.json"
DATA_FORMAT=""

if aws --endpoint "${ENDPOINT}" s3 cp "${META_PATH}" "${META_LOCAL}" >/dev/null 2>&1; then
    DATA_FORMAT=$(DATASET_PATH="${DATASET_PATH:-${DATASET}}" python3 - <<'PY'
import json
import os
import posixpath
import re

meta_path = "/tmp/metadata.json"
dataset_path = os.environ.get("DATASET_PATH", "")
data_format = ""

def normalize_path(path: str) -> str:
    if not path:
        return ""
    path = path.lstrip("/")
    if path.startswith("original/split/"):
        path = "original/data/" + path.split("/", 2)[2]
    directory, base = posixpath.split(path)
    base = re.sub(r"_well\\d{3}(?=\\.raw\\.h5$|\\.h5$|\\.nwb$)", "", base)
    base = re.sub(r"\\.+", ".", base).rstrip(".")
    return f"{directory}/{base}" if directory else base

try:
    with open(meta_path, "r") as f:
        metadata = json.load(f)
    target = normalize_path(dataset_path)
    for exp in metadata.get("ephys_experiments", {}).values():
        blocks = exp.get("blocks") or []
        for block in blocks:
            block_path = normalize_path(block.get("path", ""))
            if block_path and block_path == target:
                data_format = exp.get("data_format", "")
                break
        if data_format:
            break
    if isinstance(data_format, str):
        data_format = data_format.lower()
        if data_format == "max2":
            data_format = "maxtwo"
except Exception:
    data_format = ""

print(data_format)
PY
    )
else
    echo "Metadata not found at ${META_PATH}. Skipping download."
    exit 0
fi

if [[ "${DATA_FORMAT}" != "maxtwo" ]]; then
    echo "Data format is '${DATA_FORMAT:-unknown}', not MaxTwo. Skipping download."
    exit 0
fi

TARGET_DIR="/data"
APP_DATA_DIR="/app/data"

mkdir -p "${TARGET_DIR}"
if [ ! -e "${APP_DATA_DIR}" ]; then
    ln -s "${TARGET_DIR}" "${APP_DATA_DIR}"
fi

FILE_NAME="$(basename "${S3_URI}")"
TARGET_PATH="${TARGET_DIR}/${FILE_NAME}"

if [ -f "${TARGET_PATH}" ]; then
    echo "Found existing file at ${TARGET_PATH}; skipping download."
    exit 0
fi

MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Downloading ${FILE_NAME} (attempt $((RETRY_COUNT + 1))/${MAX_RETRIES})..."
    if aws --endpoint "${ENDPOINT}" s3 cp "${S3_URI}" "${TARGET_PATH}"; then
        echo "SUCCESS: Download completed"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "FAILED: Download attempt ${RETRY_COUNT}/${MAX_RETRIES}."
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "Retrying in 5 seconds..."
        sleep 5
    fi
done

echo "FAILED: Failed to download ${S3_URI} after ${MAX_RETRIES} attempts"
exit 1
