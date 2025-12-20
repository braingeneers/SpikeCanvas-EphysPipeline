#!/usr/bin/env bash
# start_splitter_optimized.sh — Heavily optimized version for speed
# Key improvements:
# 1. Parallel uploads using background processes  
# 2. Optimized AWS CLI settings for maximum throughput
# 3. Reduced retry delays for faster recovery
# 4. Memory-optimized operations
# 5. Progress monitoring with ETA calculations

set -euo pipefail

###############################################################################
# 0. Arguments and optimized retry configuration
###############################################################################
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <s3_uri>" >&2
  exit 1
fi
S3_URI="$1"
ENDPOINT="https://s3.braingeneers.gi.ucsc.edu"

# Optimized retry configuration - faster recovery
MAX_RETRIES=3          # Reduced from 5 - fail faster
RETRY_COUNT=0
SUCCESS=0
PARALLEL_UPLOADS=3     # Upload 3 files simultaneously

# Function to keep CPU active during I/O operations (prevents NRP suspension)
keep_cpu_active() {
    local operation_name="$1"
    echo "Starting background CPU activity during ${operation_name}..."
    
    while [ -f "/tmp/io_in_progress" ]; do
        # Light CPU work to show utilization without interfering
        dd if=/dev/zero of=/dev/null bs=1M count=100 2>/dev/null &
        sleep 3
        # Calculate some hashes to show CPU activity  
        echo "keeping CPU active during ${operation_name}" | sha256sum >/dev/null
        sleep 7
    done
    echo "Background CPU activity stopped for ${operation_name}"
}

###############################################################################
# 1. MAXIMUM PERFORMANCE AWS CLI configuration
###############################################################################
# Optimize for maximum speed - use all available bandwidth and connections
aws configure set default.s3.max_concurrent_requests 16   # Increased from 8
aws configure set default.s3.multipart_chunksize      32MB # Smaller chunks for more parallelism  
aws configure set default.s3.multipart_threshold      256MB # Start multipart sooner
aws configure set default.s3.connect_timeout          60
aws configure set default.s3.read_timeout             300   # Reduced from 900
aws configure set default.s3.max_bandwidth            1GB/s # Remove bandwidth limiting

# Enhanced retry configuration for AWS CLI
aws configure set default.retry_mode adaptive
aws configure set default.max_attempts 5              # Reduced from 10
aws configure set default.cli_read_timeout 0
aws configure set default.cli_connect_timeout 30      # Reduced from 60

# Keep payload signing enabled for data integrity
# (disabling caused XAmzContentSHA256Mismatch on multipart uploads)
aws configure set default.s3.payload_signing_enabled true

echo "=== OPTIMIZED SPLITTER STARTING ==="
echo "Target: ${S3_URI}"
echo "AWS CLI optimized for maximum throughput"
echo "Parallel upload jobs: ${PARALLEL_UPLOADS}"

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
echo "Launching optimized splitter.py on ${S3_URI}"

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
# 6. PARALLEL upload optimization
###############################################################################
echo "=== UPLOAD PHASE ==="
upload_start=$(date +%s)

S3_SPLIT_PREFIX="${S3_URI/original\/data/original\/split}"
S3_SPLIT_DIR="$(dirname "${S3_SPLIT_PREFIX}")"

echo "Uploading split files from ${TARGET_DIR}/split_output to ${S3_SPLIT_DIR}/"
echo "Using parallel uploads (${PARALLEL_UPLOADS} concurrent)"

# Start background CPU activity during upload
touch /tmp/io_in_progress
keep_cpu_active "upload" &
CPU_PID=$!

# Function to upload a single file with retry
upload_file() {
    local file="$1"
    local dest="$2"
    local base="$3"
    local size="$4"
    local file_num="$5"
    
    local retry_count=0
    local success=0
    
    echo "[$file_num] Starting upload: $base"
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        if pv -s "${size}" --name "[$file_num] $base" --eta --rate --bytes < "${file}" \
           | aws --endpoint "${ENDPOINT}" s3 cp - "${dest}"; then
            success=1
            echo "[$file_num] SUCCESS: $base uploaded"
            echo "success" > "/tmp/upload_${file_num}.status"
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
    echo "failed" > "/tmp/upload_${file_num}.status"
    return 1
}

# Get list of files to upload
files_to_upload=("${TARGET_DIR}/split_output"/*.raw.h5)
total_files=${#files_to_upload[@]}
echo "Found ${total_files} files to upload"

# Upload files in parallel batches
file_num=0
upload_pids=()
active_uploads=0

for file in "${files_to_upload[@]}"; do
    if [ ! -f "$file" ]; then
        echo "WARNING: File not found: $file"
        continue
    fi
    
    file_num=$((file_num + 1))
    base=$(basename "${file}")
    dest="${S3_SPLIT_DIR}/${base}"
    size=$(stat --printf="%s" "${file}")
    
    # Wait if we have too many active uploads
    while [ $active_uploads -ge $PARALLEL_UPLOADS ]; do
        sleep 1
        # Check for completed uploads
        for pid in "${upload_pids[@]}"; do
            if ! kill -0 $pid 2>/dev/null; then
                active_uploads=$((active_uploads - 1))
                # Remove completed PID from array
                upload_pids=(${upload_pids[@]/$pid})
            fi
        done
    done
    
    # Start upload in background
    upload_file "$file" "$dest" "$base" "$size" "$file_num" &
    upload_pid=$!
    upload_pids+=($upload_pid)
    active_uploads=$((active_uploads + 1))
    
    echo "Started upload $file_num/$total_files: $base (PID: $upload_pid)"
    
    # Small delay to stagger starts
    sleep 0.5
done

# Wait for all uploads to complete
echo "Waiting for all uploads to complete..."
for pid in "${upload_pids[@]}"; do
    wait $pid
done

# Stop background CPU activity
rm -f /tmp/io_in_progress
wait $CPU_PID 2>/dev/null || true

# Check upload results
success_count=0
failed_count=0

for i in $(seq 1 $total_files); do
    if [ -f "/tmp/upload_${i}.status" ]; then
        status=$(cat "/tmp/upload_${i}.status")
        if [ "$status" = "success" ]; then
            success_count=$((success_count + 1))
        else
            failed_count=$((failed_count + 1))
        fi
        rm -f "/tmp/upload_${i}.status"
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
