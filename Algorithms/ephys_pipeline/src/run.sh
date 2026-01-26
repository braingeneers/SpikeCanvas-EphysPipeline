#!/usr/bin/env bash
# run.sh - Kilosort2 pipeline entrypoint

# Define the number of retries
MAX_RETRIES=5
RETRY_COUNT=0
SUCCESS=0

REC_TIME=$(echo "$1" | awk -F '/original/(data|split)/|/shared/' '{print $1}')
DATASET=$(echo "$1" | awk -F '/original/(data|split)/|/shared/' '{print $2}')

DATA_NAME_FULL=$(echo "${DATASET}" | awk -F '.raw.h5|.h5|.nwb' '{print $1}')
OUT_REC_TIME="${REC_TIME}"
if [[ "${OUT_REC_TIME}" == s3://braingeneersdev/* ]]; then
    OUT_REC_TIME="s3://braingeneers/${OUT_REC_TIME#s3://braingeneersdev/}"
fi
CACHE_REC_TIME="${REC_TIME}"
if [[ "${CACHE_REC_TIME}" == s3://braingeneers/* ]]; then
    CACHE_REC_TIME="s3://braingeneersdev/${CACHE_REC_TIME#s3://braingeneers/}"
elif [[ "${CACHE_REC_TIME}" != s3://braingeneersdev/* ]]; then
    CACHE_REC_TIME="s3://braingeneersdev/${CACHE_REC_TIME#s3://}"
fi

if [[ "${DATA_NAME_FULL}" == *"/"* ]]; then
    CHIP_ID=$(echo "${DATA_NAME_FULL}" | awk -F '/' '{print $1}')"/"
    DATA_NAME=$(echo "${DATA_NAME_FULL}" | awk -F '/' '{print $2}')
else
    CHIP_ID=""
    DATA_NAME=${DATA_NAME_FULL}
fi

BASE_EXPERIMENT=$(echo "${DATA_NAME}" | sed -E 's/_well[0-9]{3}$//')
META_REC_TIME="${REC_TIME}"
if [[ "${META_REC_TIME}" == s3://braingeneersdev/* ]]; then
    META_REC_TIME="s3://braingeneers/${META_REC_TIME#s3://braingeneersdev/}"
fi

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
DATA_FORMAT=""
if [[ -f /project/SpikeSorting/metadata.json ]]; then
    DATA_FORMAT=$(BASE_EXPERIMENT="${BASE_EXPERIMENT}" python3 - <<'PY'
import json
import os

meta_path = "/project/SpikeSorting/metadata.json"
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
fi

RAW_S3_PATH="$1"
if [[ "${DATA_FORMAT}" == "maxtwo" ]]; then
    RAW_S3_PATH="${RAW_S3_PATH/s3:\/\/braingeneers\//s3:\/\/braingeneersdev/}"
    echo "MaxTwo dataset detected, using cache path: ${RAW_S3_PATH}"
fi

echo "Downloading raw data file: ${RAW_S3_PATH}"
aws --endpoint $ENDPOINT_URL s3 cp ${RAW_S3_PATH} /project/SpikeSorting/Trace

echo "Starting Kilosort2 processing..."
python kilosort2_simplified.py $DATA_NAME

echo "Uploading results..."
cd /project/SpikeSorting/inter/sorted/kilosort2 || exit

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
fi

# upload curation file, there is no separate log for the qm.zip, info are kept the to the main log
# zip this file to make sure the same s3 file structure as before
cd /project/SpikeSorting/inter/sorted/curation/curated || exit
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
fi

# upload the figure
cd /project/SpikeSorting/inter/sorted/figure || exit
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
fi

if [[ "$1" == s3://braingeneersdev/* ]]; then
    echo "Cleaning cache input: $1"
    aws --endpoint "$ENDPOINT_URL" s3 rm "$1" || echo "WARNING: Failed to delete cache input $1"
fi

echo "Kilosort2 pipeline completed."
