#!/usr/bin/env bash

REC_TIME=$(echo $1 | awk -F '/original/data/|/shared/' '{print $1}')
DATASET=$(echo $1 | awk -F '/original/data/|/shared/' '{print $2}')
DATA_NAME_FULL=$(echo ${DATASET} | awk -F '.raw.h5|.h5|.nwb' '{print $1}')

if [[ $DATA_NAME_FULL == *"/"* ]]; then
    CHIP_ID=$(echo $DATA_NAME_FULL | awk -F '/' '{print $1}')"/"
    DATA_NAME=$(echo $DATA_NAME_FULL | awk -F '/' '{print $2}')
else
    CHIP_ID=""
    DATA_NAME=${DATA_NAME_FULL}
fi

# download metadata.json to local
aws --endpoint $ENDPOINT_URL s3 cp ${REC_TIME}/metadata.json /project/SpikeSorting/metadata.json
aws --endpoint $ENDPOINT_URL s3 cp $1 /project/SpikeSorting/Trace

python kilosort2_simplified.py $DATA_NAME

cd /project/SpikeSorting/inter/sorted/kilosort2 || exit
aws --endpoint $ENDPOINT_URL s3 cp recording.dat s3://braingeneersdev/cache/${DATA_NAME}/recording.dat
aws --endpoint $ENDPOINT_URL s3 cp temp_wh.dat s3://braingeneersdev/cache/${DATA_NAME}/temp_wh.dat
rm *.dat
zip -r ${DATA_NAME}_phy.zip *
aws --endpoint $ENDPOINT_URL s3 cp ${DATA_NAME}_phy.zip ${REC_TIME}/derived/kilosort2/${CHIP_ID}${DATA_NAME}_phy.zip
# aws --endpoint $ENDPOINT_URL s3 cp ${DATA_NAME}_phy.zip ${REC_TIME}/derived/parameters/${CHIP_ID}${DATA_NAME}_phy.zip

# upload curation file, there is no separate log for the qm.zip, info are kept the to the main log
# zip this file to make sure the same s3 file structure as before
cd /project/SpikeSorting/inter/sorted/curation/curated || exit
zip -r qm.zip *
aws --endpoint $ENDPOINT_URL s3 cp qm.zip ${REC_TIME}/derived/kilosort2/${CHIP_ID}${DATA_NAME}_acqm.zip
# aws --endpoint $ENDPOINT_URL s3 cp qm.zip ${REC_TIME}/derived/parameters/${CHIP_ID}${DATA_NAME}_acqm.zip

# upload the figure
cd /project/SpikeSorting/inter/sorted/figure || exit
zip -r figure.zip *
aws --endpoint $ENDPOINT_URL s3 cp figure.zip ${REC_TIME}/derived/kilosort2/${CHIP_ID}${DATA_NAME}_figure.zip
# aws --endpoint $ENDPOINT_URL s3 cp figure.zip ${REC_TIME}/derived/parameters/${CHIP_ID}${DATA_NAME}_figure.zip

