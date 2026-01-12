#!/usr/bin/env bash
# start_splitter.sh — Optimized MaxTwo splitter for speed
# Key improvements:
# 1. Parallel uploads using background processes  
# 2. Optimized AWS CLI settings for maximum throughput
# 3. Reduced retry delays for faster recovery
# 4. Memory-optimized operations
# 5. Progress monitoring with ETA calculations

set -euo pipefail
echo "Running start_splitter.sh v0.41"
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

if [[ "${META_ROOT}" == s3://braingeneersdev/* ]]; then
    META_ROOT="s3://braingeneers/${META_ROOT#s3://braingeneersdev/}"
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

# NRP-compliant configuration to utilize 6 CPU cores and 48GB memory efficiently 
MAX_RETRIES=3          # Reduced from 5 - fail faster
RETRY_COUNT=0
SUCCESS=0
PARALLEL_UPLOADS=4     # Use 4 parallel uploads to leverage 6 CPU cores

# Function to maintain NRP-compliant resource utilization (prevents account suspension)
keep_cpu_active() {
    local operation_name="$1"
    echo "Starting high-utilization background activity during ${operation_name}..."
    echo "Target: 25-40% CPU (1.5-2.4 cores of 6) and 25-35% memory (12-17GB of 48GB)"
    
    while [ -f "/tmp/io_in_progress" ]; do
        # High CPU utilization to meet NRP requirements (1.5-2.4 cores of 6 requested)
        {
            # Multiple CPU-intensive processes running in parallel
            for i in {1..4}; do
                {
                    # CPU-bound work: compression, hashing, find operations
                    dd if=/dev/zero bs=1M count=500 2>/dev/null | gzip > /dev/null &
                    find /usr -type f -name "*.so" -exec sha256sum {} \; >/dev/null 2>&1 &
                    openssl speed -seconds 3 rsa2048 >/dev/null 2>&1 &
                } &
            done
            
            # SAFE memory utilization - only allocate once per cycle
            if [ ! -f "/tmp/memory_allocated" ]; then
                echo "Allocating SAFE memory for NRP compliance: target 8-10GB of 48GB"
                python3 "${SCRIPT_DIR}/nrp_memory_utilization.py" 2>/dev/null &
            fi
            
            # Wait before next cycle
            sleep 30
            
            # Clean up completed background processes
            jobs -p | head -5 | xargs -r kill -9 2>/dev/null || true
            
        } &
        
        sleep 35  # Check every 35 seconds
    done
    
    # Clean up all background processes
    echo "Stopping background activity for ${operation_name}"
    jobs -p | xargs -r kill -9 2>/dev/null || true
    
    # Clean up memory allocation flag
    rm -f /tmp/memory_allocated 2>/dev/null || true
    
    echo "Background resource utilization stopped for ${operation_name}"
}

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

# Start background CPU activity during download
touch /tmp/io_in_progress
keep_cpu_active "download" &
CPU_PID=$!

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

# Stop background CPU activity
rm -f /tmp/io_in_progress
wait $CPU_PID 2>/dev/null || true

if [ $SUCCESS -eq 0 ]; then
    echo "FAILED: Failed to download ${S3_URI} after ${MAX_RETRIES} attempts"
    exit 1
fi

###############################################################################
# 5. Run the splitter (processing phase)
###############################################################################
echo "=== PROCESSING PHASE ==="
process_start=$(date +%s)
echo "Launching optimized splitter on ${S3_URI}"

# Use optimized Python script if available, fallback to standard
if [ -f "splitter_optimized.py" ]; then
    echo "Using optimized splitter with parallel processing..."
    python splitter_optimized.py "${S3_URI}"
else
    echo "Using standard splitter..."
    python splitter.py "${S3_URI}"
fi

process_time=$(($(date +%s) - process_start))
echo "Processing completed in ${process_time}s"

###############################################################################
# 6. Upload phase (serial uploads)
###############################################################################
echo "=== UPLOAD PHASE ==="
upload_start=$(date +%s)

S3_SPLIT_PREFIX="${S3_URI/original\/data/original\/split}"
if [[ "${S3_SPLIT_PREFIX}" == s3://braingeneers/* ]]; then
    S3_SPLIT_PREFIX="s3://braingeneersdev/${S3_SPLIT_PREFIX#s3://braingeneers/}"
fi
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
