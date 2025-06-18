#!/bin/bash
# Build script for all pipeline components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Maxwell Ephys Pipeline Components${NC}"

# Build base image
echo -e "${YELLOW}Building base image...${NC}"
docker build -f docker/base.dockerfile -t maxwell_ephys_base:latest .

# Component list
components=("job_scanner" "kilosort" "curation" "lfp" "visualization")

# Build each component
for component in "${components[@]}"; do
    echo -e "${YELLOW}Building ${component}...${NC}"
    if [ -f "docker/components/${component}.dockerfile" ]; then
        docker build -f "docker/components/${component}.dockerfile" \
                     -t "maxwell_ephys_${component}:latest" \
                     --build-arg BASE_IMAGE=maxwell_ephys_base:latest .
        echo -e "${GREEN}✓ ${component} built successfully${NC}"
    else
        echo -e "${RED}✗ Dockerfile not found for ${component}${NC}"
    fi
done

echo -e "${GREEN}All components built successfully!${NC}"
