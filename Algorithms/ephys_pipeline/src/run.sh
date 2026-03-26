#!/usr/bin/env bash
# run.sh - Kilosort2 pipeline entrypoint

# Define the number of retries
MAX_RETRIES=5
RETRY_COUNT=0
SUCCESS=0
# Allow disabling cache cleanup during development (set CLEAN_CACHE_INPUT=false to disable)
CLEAN_CACHE_INPUT=${CLEAN_CACHE_INPUT:-true}

REC_TIME=$(echo "$1" | awk -F '/original/(data|split)/|/shared/' '{print $1}')
DATASET=$(echo "$1" | awk -F '/original/(data|split)/|/shared/' '{print $2}')

DATA_NAME_FULL=$(echo "${DATASET}" | awk -F '.raw.h5|.h5|.nwb' '{print $1}')
to_public_path() {
    local uri="$1"
    if [[ "${uri}" == s3://braingeneersdev/cache/ephys/* ]]; then
        echo "s3://braingeneers/ephys/${uri#s3://braingeneersdev/cache/ephys/}"
    elif [[ "${uri}" == s3://braingeneersdev/ephys/* ]]; then
        echo "s3://braingeneers/ephys/${uri#s3://braingeneersdev/ephys/}"
    else
        echo "${uri}"
    fi
}

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

OUT_REC_TIME="$(to_public_path "${REC_TIME}")"
CACHE_REC_TIME="$(to_cache_path "${REC_TIME}")"

if [[ "${DATA_NAME_FULL}" == *"/"* ]]; then
    CHIP_ID=$(echo "${DATA_NAME_FULL}" | awk -F '/' '{print $1}')"/"
    DATA_NAME=$(echo "${DATA_NAME_FULL}" | awk -F '/' '{print $2}')
else
    CHIP_ID=""
    DATA_NAME=${DATA_NAME_FULL}
fi

BASE_EXPERIMENT=$(echo "${DATA_NAME}" | sed -E 's/_well[0-9]{3}$//')
META_REC_TIME="$(to_public_path "${REC_TIME}")"

# Configure AWS CLI for better resource utilization
aws configure set default.s3.max_concurrent_requests 8   # Higher concurrency for 12 CPUs
aws configure set default.s3.multipart_chunksize 32MB    # Balanced chunk size
aws configure set default.s3.max_bandwidth 200MB/s       # Reasonable bandwidth limit

# download metadata.json to local
echo "Downloading metadata.json..."
echo "Metadata source: ${META_REC_TIME}/metadata.json"

if ! aws --endpoint $ENDPOINT_URL s3 cp ${META_REC_TIME}/metadata.json /project/SpikeSorting/metadata.json; then
    echo "WARNING: Failed to download metadata from ${META_REC_TIME}/metadata.json"
fi

# download raw data to local
DATASET_PATH=""
if [[ "$1" == *"/original/data/"* ]]; then
    DATASET_PATH="original/data/${1#*'/original/data/'}"
elif [[ "$1" == *"/original/split/"* ]]; then
    DATASET_PATH="original/split/${1#*'/original/split/'}"
elif [[ "$1" == *"/shared/"* ]]; then
    DATASET_PATH="shared/${1#*'/shared/'}"
else
    DATASET_PATH="${DATASET}"
fi
DATA_FORMAT=""
if [[ -f /project/SpikeSorting/metadata.json ]]; then
    DATA_FORMAT=$(DATASET_PATH="${DATASET_PATH}" python3 - <<'PY'
import json
import os
import posixpath
import re

meta_path = "/project/SpikeSorting/metadata.json"
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
fi

RAW_S3_PATH="$1"
if [[ "${DATA_FORMAT}" == "maxtwo" ]]; then
    RAW_S3_PATH="$(to_cache_path "${RAW_S3_PATH}")"
    echo "MaxTwo dataset detected, using cache path: ${RAW_S3_PATH}"
fi

echo "Downloading raw data file: ${RAW_S3_PATH}"
DOWNLOAD_START=$(date +%s)

# retry download up to MAX_RETRIES times (matches upload retry pattern)
RETRY_COUNT=0
SUCCESS=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    aws --endpoint $ENDPOINT_URL s3 cp ${RAW_S3_PATH} /project/SpikeSorting/Trace
    if [ $? -eq 0 ]; then
        SUCCESS=1
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Download from ${RAW_S3_PATH} failed. Attempt $RETRY_COUNT/$MAX_RETRIES. Retrying..."
    sleep 5
done

if [ $SUCCESS -ne 1 ]; then
    echo "ERROR: S3 download failed after $MAX_RETRIES attempts."
    exit 1
fi

DOWNLOAD_END=$(date +%s)
DOWNLOAD_ELAPSED=$((DOWNLOAD_END - DOWNLOAD_START))
echo "TIMING: S3 download completed in ${DOWNLOAD_ELAPSED}s"

echo "Starting Kilosort2 processing..."
COMPUTE_START=$(date +%s)
DATASET_PATH="${DATASET_PATH}" python kilosort2_simplified.py $DATA_NAME
KS_STATUS=$?
COMPUTE_END=$(date +%s)
COMPUTE_ELAPSED=$((COMPUTE_END - COMPUTE_START))
echo "TIMING: Kilosort2 compute completed in ${COMPUTE_ELAPSED}s (exit code: ${KS_STATUS})"
if [ $KS_STATUS -ne 0 ]; then
    echo "ERROR: Kilosort2 processing failed with exit code ${KS_STATUS}"
    exit $KS_STATUS
fi

UPLOAD_START=$(date +%s)
echo "Uploading results..."
cd /project/SpikeSorting/inter/sorted/kilosort2 || {
    echo "ERROR: Expected output folder not found: /project/SpikeSorting/inter/sorted/kilosort2"
    exit 1
}

# Upload cache files
aws --endpoint $ENDPOINT_URL s3 cp recording.dat ${CACHE_REC_TIME}/cache/recording.dat
aws --endpoint $ENDPOINT_URL s3 cp temp_wh.dat ${CACHE_REC_TIME}/cache/temp_wh.dat
rm *.dat

# Create and upload main results
zip -r ${DATA_NAME}_phy.zip *
DEST="${OUT_REC_TIME}/derived/kilosort2/${CHIP_ID}${DATA_NAME}_phy.zip"

# retry 5 times if the upload fails
RETRY_COUNT=0
SUCCESS=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    aws --endpoint "$ENDPOINT_URL" s3 cp ${DATA_NAME}_phy.zip "$DEST"
    if [ $? -eq 0 ]; then
        SUCCESS=1
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Upload to $DEST failed. Attempt $RETRY_COUNT/$MAX_RETRIES. Retrying..."
    sleep 5 # Wait for 5 seconds before retrying
done

if [ $SUCCESS -eq 1 ]; then
    echo "_phy.zip uploaded successfully."
else
    echo "_phy.zip failed to upload after $MAX_RETRIES attempts."
    exit 1
fi

# upload curation file if present
CURATION_DIR="/project/SpikeSorting/inter/sorted/curation/curated"
if [ -d "$CURATION_DIR" ] && compgen -G "${CURATION_DIR}/*" > /dev/null; then
    cd "$CURATION_DIR" || exit
    zip -r qm.zip *

    # retry 5 times if the upload fails
    DEST="${OUT_REC_TIME}/derived/kilosort2/${CHIP_ID}${DATA_NAME}_acqm.zip"
    RETRY_COUNT=0
    SUCCESS=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        aws --endpoint "$ENDPOINT_URL" s3 cp qm.zip "$DEST"
        if [ $? -eq 0 ]; then
            SUCCESS=1
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "Upload to $DEST failed. Attempt $RETRY_COUNT/$MAX_RETRIES. Retrying..."
        sleep 5 # Wait for 5 seconds before retrying
    done

    if [ $SUCCESS -eq 1 ]; then
        echo "_acqm.zip uploaded successfully."
    else
        echo "_acqm.zip failed to upload after $MAX_RETRIES attempts."
        exit 1
    fi
else
    echo "No curation outputs found; skipping _acqm.zip upload."
fi

# upload the figure if present
FIGURE_DIR="/project/SpikeSorting/inter/sorted/figure"
if [ -d "$FIGURE_DIR" ] && compgen -G "${FIGURE_DIR}/*" > /dev/null; then
    cd "$FIGURE_DIR" || exit
    zip -r figure.zip *
    DEST="${OUT_REC_TIME}/derived/kilosort2/${CHIP_ID}${DATA_NAME}_figure.zip"

    # retry 5 times if the upload fails
    RETRY_COUNT=0
    SUCCESS=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        aws --endpoint "$ENDPOINT_URL" s3 cp figure.zip "$DEST"
        if [ $? -eq 0 ]; then
            SUCCESS=1
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "Upload to $DEST failed. Attempt $RETRY_COUNT/$MAX_RETRIES. Retrying..."
        sleep 5 # Wait for 5 seconds before retrying
    done

    if [ $SUCCESS -eq 1 ]; then
        echo "_figure.zip uploaded successfully."
    else
        echo "_figure.zip failed to upload after $MAX_RETRIES attempts."
        exit 1
    fi
else
    echo "No figure outputs found; skipping _figure.zip upload."
fi

if [[ "$1" == s3://braingeneersdev/* && "${CLEAN_CACHE_INPUT}" == "true" ]]; then
    echo "Cleaning cache input: $1"
    aws --endpoint "$ENDPOINT_URL" s3 rm "$1" || echo "WARNING: Failed to delete cache input $1"
elif [[ "$1" == s3://braingeneersdev/* ]]; then
    echo "Skipping cache cleanup for $1 (CLEAN_CACHE_INPUT=${CLEAN_CACHE_INPUT})"
fi

UPLOAD_END=$(date +%s)
UPLOAD_ELAPSED=$((UPLOAD_END - UPLOAD_START))
PIPELINE_TOTAL=$((UPLOAD_END - DOWNLOAD_START))
echo "TIMING: S3 upload completed in ${UPLOAD_ELAPSED}s"
echo "TIMING: Total pipeline wall-clock: ${PIPELINE_TOTAL}s (download: ${DOWNLOAD_ELAPSED}s, compute: ${COMPUTE_ELAPSED}s, upload: ${UPLOAD_ELAPSED}s)"

# Write provenance record for this pipeline run
# Captures input/output paths, timing, and execution environment
PROVENANCE_FILE="/tmp/provenance.json"
cat > "$PROVENANCE_FILE" << EOF
{
    "pipeline": "kilosort2",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "input_s3_path": "${RAW_S3_PATH}",
    "output_s3_prefix": "${OUT_REC_TIME}/derived/kilosort2/",
    "data_format": "${DATA_FORMAT}",
    "hostname": "$(hostname)",
    "image": "${PIPELINE_IMAGE:-unknown}",
    "kilosort_exit_code": ${KS_STATUS},
    "timing_seconds": {
        "download": ${DOWNLOAD_ELAPSED},
        "compute": ${COMPUTE_ELAPSED},
        "upload": ${UPLOAD_ELAPSED},
        "total": ${PIPELINE_TOTAL}
    },
    "artifacts_uploaded": [
        "${CHIP_ID}${DATA_NAME}_phy.zip"
    ]
}
EOF

# Upload provenance alongside results
PROV_DEST="${OUT_REC_TIME}/derived/kilosort2/${CHIP_ID}${DATA_NAME}_provenance.json"
aws --endpoint "$ENDPOINT_URL" s3 cp "$PROVENANCE_FILE" "$PROV_DEST" || echo "WARNING: Failed to upload provenance record"
echo "Provenance record uploaded to ${PROV_DEST}"

echo "Kilosort2 pipeline completed."
