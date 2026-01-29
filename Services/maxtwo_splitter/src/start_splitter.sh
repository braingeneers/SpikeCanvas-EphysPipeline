#!/usr/bin/env bash
# start_splitter.sh — MaxTwo splitter entrypoint
# Highlights:
# 1. Reduced retry delays for faster recovery
# 2. Progress monitoring with ETA calculations

set -euo pipefail
echo "Running start_splitter.sh v0.55"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

###############################################################################
# 0. Arguments and optimized retry configuration
###############################################################################
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <s3_uri>" >&2
  exit 1
fi
S3_URI="$1"
# ENDPOINT="https://s3.braingeneers.gi.ucsc.edu"
ENDPOINT="http://rook-ceph-rgw-nautiluss3.rook"  # Internal endpoint for NRP cluster

to_cache_path() {
    local uri="$1"
    if [[ "${uri}" == s3://braingeneersdev/cache/ephys/* ]]; then
        echo "${uri}"
    elif [[ "${uri}" == s3://braingeneersdev/ephys/* ]]; then
        echo "s3://braingeneersdev/cache/ephys/${uri#s3://braingeneersdev/ephys/}"
    elif [[ "${uri}" == s3://braingeneers/ephys/* ]]; then
        echo "s3://braingeneersdev/cache/ephys/${uri#s3://braingeneers/ephys/}"
    else
        echo "${uri}"
    fi
}

###############################################################################
# 0.5. Skip non-MaxTwo datasets early (avoid heavy downloads)
###############################################################################
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

if [[ "${META_ROOT}" == s3://braingeneersdev/cache/ephys/* ]]; then
    META_ROOT="s3://braingeneers/ephys/${META_ROOT#s3://braingeneersdev/cache/ephys/}"
elif [[ "${META_ROOT}" == s3://braingeneersdev/ephys/* ]]; then
    META_ROOT="s3://braingeneers/ephys/${META_ROOT#s3://braingeneersdev/ephys/}"
fi

META_PATH="${META_ROOT}/metadata.json"
META_LOCAL="/tmp/metadata.json"
DATA_FORMAT=""

if aws --endpoint "${ENDPOINT}" s3 cp "${META_PATH}" "${META_LOCAL}" >/dev/null 2>&1; then
    DATA_FORMAT=$(BASE_EXPERIMENT="${BASE_EXPERIMENT}" python3 - <<'PY'
import json
import os

meta_path = "/tmp/metadata.json"
experiment = os.environ.get("BASE_EXPERIMENT", "")
data_format = ""

try:
    with open(meta_path, "r") as f:
        metadata = json.load(f)
    data_format = metadata.get("ephys_experiments", {}).get(experiment, {}).get("data_format", "")
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
    echo "Metadata not found at ${META_PATH}. Skipping MaxTwo splitter."
    exit 0
fi

if [[ "${DATA_FORMAT}" != "maxtwo" ]]; then
    echo "Data format is '${DATA_FORMAT:-unknown}', not MaxTwo. Exiting splitter."
    exit 0
fi

###############################################################################
# 0.6. Short-circuit if cached split outputs already exist
###############################################################################
cache_exists() {
    local cache_dir="$1"
    local label="$2"
    local bucket
    local prefix
    local key_count
    local keys
    local unique_wells
    local well_count_ge1

    bucket="$(echo "${cache_dir}" | cut -d/ -f3)"
    prefix="$(echo "${cache_dir}" | cut -d/ -f4-)"
    if [ -n "${prefix}" ]; then
        prefix="${prefix%/}/${BASE_EXPERIMENT}_well"
    else
        prefix="${BASE_EXPERIMENT}_well"
    fi

    keys=$(aws --endpoint "${ENDPOINT}" s3api list-objects-v2 \
        --bucket "${bucket}" \
        --prefix "${prefix}" \
        --max-keys 1000 \
        --query 'Contents[].Key' \
        --output text 2>/dev/null || echo "")

    if [ -z "${keys}" ]; then
        return 1
    fi

    key_count=$(echo "${keys}" | tr '\t' '\n' | wc -l | tr -d ' ')
    unique_wells=$(echo "${keys}" | tr '\t' '\n' | sed -n 's/.*_well\([0-9]\{3\}\).*/\1/p' | sort -u)
    well_count_ge1=$(echo "${unique_wells}" | awk '$1+0>=1{c++} END{print c+0}')

    if [[ "${key_count}" =~ ^[0-9]+$ ]]; then
        if [ "${well_count_ge1}" -eq 6 ] || [ "${well_count_ge1}" -eq 24 ]; then
            echo "Found cached split outputs in ${label}: s3://${bucket}/${prefix}* (${well_count_ge1} wells)"
            return 0
        elif [ "${well_count_ge1}" -gt 0 ]; then
            echo "Partial cache in ${label}: s3://${bucket}/${prefix}* (${well_count_ge1} wells). Will re-split."
        fi
    fi
    return 1
}

CACHE_PREFIX="$(to_cache_path "${S3_URI}")"
CACHE_DIR="$(dirname "${CACHE_PREFIX}")"
LEGACY_CACHE_DIR="${CACHE_DIR/original\/data/original\/split}"

echo "Checking cache for existing splits..."
if cache_exists "${CACHE_DIR}" "primary cache" || cache_exists "${LEGACY_CACHE_DIR}" "legacy cache"; then
    echo "Cached split files already exist. Skipping split."
    exit 0
fi

# Retry configuration
MAX_RETRIES=3          # Reduced from 5 - fail faster
RETRY_COUNT=0
SUCCESS=0
PARALLEL_UPLOADS=4     # Use 4 parallel uploads to leverage 6 CPU cores

###############################################################################
# 1. AWS CLI configuration
###############################################################################
# Custom AWS CLI tuning (commented out to keep behavior closer to defaults).
# Uncomment if future tuning is required for Ceph/S3 performance.
# aws configure set default.s3.max_concurrent_requests 16
# aws configure set default.s3.multipart_chunksize      64MB
# aws configure set default.s3.multipart_threshold      256MB
# aws configure set default.s3.connect_timeout          60
# aws configure set default.s3.read_timeout             300
# aws configure set default.s3.max_bandwidth            1GB/s
# aws configure set default.retry_mode adaptive
# aws configure set default.max_attempts 5
# aws configure set default.cli_read_timeout 0
# aws configure set default.cli_connect_timeout 30
# aws configure set default.s3.payload_signing_enabled true

echo "=== OPTIMIZED SPLITTER STARTING ==="
echo "Target: ${S3_URI}"
echo "AWS CLI using default configuration"

# Quick connectivity test (minimal time spent)
echo "Testing S3 connectivity..."
if timeout 5 aws --endpoint "${ENDPOINT}" s3 ls s3://braingeneers/ >/dev/null 2>&1; then
    echo "SUCCESS: S3 connection verified"
else
    echo "WARNING: S3 test failed, proceeding anyway"
fi

###############################################################################
# 2. Target paths
###############################################################################
TARGET_DIR="/data"
APP_DATA_DIR="/app/data"

mkdir -p "${TARGET_DIR}"

# Keep downloads on the ephemeral /data volume but also expose them under
# /app/data so they're easy to find when the working directory is /app.
if [ ! -e "${APP_DATA_DIR}" ]; then
    ln -s "${TARGET_DIR}" "${APP_DATA_DIR}"
fi

FILE_NAME="$(basename "${S3_URI}")"
TARGET_PATH="${TARGET_DIR}/${FILE_NAME}"

# Ensure sufficient disk space
AVAILABLE_SPACE=$(df "${TARGET_DIR}" | awk 'NR==2 {print $4}')
echo "Available disk space: ${AVAILABLE_SPACE} KB"

###############################################################################
# 3. Ensure required tools are installed
###############################################################################
if ! command -v pv >/dev/null 2>&1; then
  echo "Installing pv for progress monitoring..."
  apt-get update -qq && apt-get install -y -qq pv
fi

###############################################################################
# 4. OPTIMIZED Download with progress monitoring
###############################################################################
echo "=== DOWNLOAD PHASE ==="
start_time=$(date +%s)

if [ -f "${TARGET_PATH}" ]; then
    echo "Found existing file at ${TARGET_PATH}; skipping download."
    download_time=0
else
    # Get object size for progress estimation
    BUCKET=$(echo "${S3_URI}" | cut -d/ -f3)
    KEY=$(echo "${S3_URI}" | cut -d/ -f4-)
    SIZE_BYTES=$(aws --endpoint "${ENDPOINT}" s3api head-object \
                     --bucket "${BUCKET}" --key "${KEY}" \
                     --query 'ContentLength' --output text 2>/dev/null || echo "")
    [[ "${SIZE_BYTES}" == "None" ]] && SIZE_BYTES=""

    if [[ -n "${SIZE_BYTES}" ]]; then
      pv_opts=(-s "${SIZE_BYTES}")
      size_gb=$(echo "scale=1; ${SIZE_BYTES}/1073741824" | bc)
      echo "File size: ${size_gb} GB"
    else
      pv_opts=()
      echo "File size: Unknown"
    fi

    # Download with optimized retry logic
    RETRY_COUNT=0
    SUCCESS=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        echo "Downloading ${FILE_NAME} (attempt $((RETRY_COUNT + 1))/${MAX_RETRIES})..."
        
        if aws --endpoint "${ENDPOINT}" s3 cp "${S3_URI}" - \
           | pv "${pv_opts[@]}" --name "Download" --eta --rate --bytes \
           > "${TARGET_PATH}"; then
            SUCCESS=1
            download_time=$(($(date +%s) - start_time))
            echo "SUCCESS: Download completed in ${download_time}s"
            break
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo "FAILED: Download failed. Attempt ${RETRY_COUNT}/${MAX_RETRIES}."
            rm -f "${TARGET_PATH}"  # Remove partial file
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                echo "Retrying in 5 seconds..."  # Reduced delay
                sleep 5
            fi
        fi
    done

    if [ $SUCCESS -eq 0 ]; then
        echo "FAILED: Failed to download ${S3_URI} after ${MAX_RETRIES} attempts"
        exit 1
    fi
fi

###############################################################################
# 5. Run the splitter (processing phase)
###############################################################################
echo "=== PROCESSING PHASE ==="
process_start=$(date +%s)
echo "Launching optimized splitter on ${S3_URI}"

echo "Using standard splitter with parallel processing..."
python splitter.py "${S3_URI}"

process_time=$(($(date +%s) - process_start))
echo "Processing completed in ${process_time}s"

###############################################################################
# 6. Upload phase (serial uploads)
###############################################################################
echo "=== UPLOAD PHASE ==="
upload_start=$(date +%s)

S3_SPLIT_PREFIX="$(to_cache_path "${S3_URI}")"
S3_SPLIT_DIR="$(dirname "${S3_SPLIT_PREFIX}")"

echo "Uploading split files from ${TARGET_DIR}/split_output to ${S3_SPLIT_DIR}/"
echo "Using serial uploads (aws CLI handles multipart concurrency)"

# Function to upload a single file with retry
upload_file() {
    local file="$1"
    local dest="$2"
    local base="$3"
    local file_num="$4"
    
    local retry_count=0
    local success=0
    
    echo "[$file_num] Starting upload: $base"
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        echo "[$file_num] aws --endpoint \"${ENDPOINT}\" s3 cp \"${file}\" \"${dest}\""
        if aws --endpoint "${ENDPOINT}" s3 cp "${file}" "${dest}"; then
            success=1
            echo "[$file_num] SUCCESS: $base uploaded"
            return 0
        else
            retry_count=$((retry_count + 1))
            echo "[$file_num] FAILED: Upload failed for $base (attempt $retry_count/$MAX_RETRIES)"
            if [ $retry_count -lt $MAX_RETRIES ]; then
                echo "[$file_num] Retrying in 3 seconds..."  # Reduced delay
                sleep 3
            fi
        fi
    done
    
    echo "[$file_num] FAILED: Upload failed permanently for $base"
    return 1
}

# Get list of files to upload
files_to_upload=("${TARGET_DIR}/split_output"/*.raw.h5)
total_files=${#files_to_upload[@]}
echo "Found ${total_files} files to upload"

# Upload files serially
file_num=0
success_count=0
failed_count=0

for file in "${files_to_upload[@]}"; do
    if [ ! -f "$file" ]; then
        echo "WARNING: File not found: $file"
        continue
    fi
    
    file_num=$((file_num + 1))
    base=$(basename "${file}")
    dest="${S3_SPLIT_DIR}/${base}"
    
    if upload_file "$file" "$dest" "$base" "$file_num"; then
        success_count=$((success_count + 1))
    else
        failed_count=$((failed_count + 1))
    fi
done

###############################################################################
# 7. Upload metadata to cache root (legacy sorter compatibility)
###############################################################################
if [ -f "${META_LOCAL}" ]; then
    CACHE_META_ROOT="$(to_cache_path "${META_ROOT}")"
    echo "Uploading metadata.json to cache root: ${CACHE_META_ROOT}/metadata.json"
    aws --endpoint "${ENDPOINT}" s3 cp "${META_LOCAL}" "${CACHE_META_ROOT}/metadata.json" || \
        echo "WARNING: Failed to upload metadata to ${CACHE_META_ROOT}/metadata.json"
else
    echo "Metadata file not found at ${META_LOCAL}; skipping metadata upload"
fi

upload_time=$(($(date +%s) - upload_start))
total_time=$(($(date +%s) - start_time))

echo "=== PERFORMANCE SUMMARY ==="
echo "Download time: ${download_time}s"
echo "Processing time: ${process_time}s" 
echo "Upload time: ${upload_time}s"
echo "Total time: ${total_time}s"
echo "Upload results: ${success_count} succeeded, ${failed_count} failed"

if [ $failed_count -eq 0 ]; then
    echo "SUCCESS: All files uploaded successfully in ${total_time}s"
    echo "Average upload speed: ~$((total_files * 4 / upload_time)) GB/min"
else
    echo "FAILED: Some uploads failed. Check the logs above."
    exit 1
fi
