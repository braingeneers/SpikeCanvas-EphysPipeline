#!/usr/bin/env bash

REC_TIME=$(echo $1 | awk -F '/original/data/|/shared/' '{print $1}')
DATASET=$(echo $1 | awk -F '/original/data/|/shared/' '{print $2}')
DATA_NAME_FULL=$(echo ${DATASET} | awk -F '.raw.h5|.h5|.nwb' '{print $1}')

PHY=${REC_TIME}/derived/kilosort2/${DATA_NAME_FULL}_phy.zip
aws --endpoint $ENDPOINT_URL s3 cp ${PHY} /project/SpikeSorting/inter/sorted/kilosort2/phy.zip
aws --endpoint $ENDPOINT_URL s3 cp $1 /project/SpikeSorting/Trace

python kilosort2_simplified.py $DATA_NAME_FULL

cd /project/SpikeSorting/inter/sorted/curation/curated || exit
zip -0 qm.zip *
aws --endpoint $ENDPOINT_URL s3 cp qm.zip ${REC_TIME}/derived/kilosort2/${DATA_NAME_FULL}_acqm.zip

# upload the figure
cd /project/SpikeSorting/inter/sorted/figure || exit
zip -0 figure.zip *
aws --endpoint $ENDPOINT_URL s3 cp figure.zip ${REC_TIME}/derived/kilosort2/${DATA_NAME_FULL}_figure.zip