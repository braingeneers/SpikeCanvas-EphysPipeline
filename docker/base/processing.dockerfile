# Base image for processing containers
FROM python:3.10

ENV DEBIAN_FRONTEND=noninteractive

# Processing-specific system dependencies
RUN apt-get update && apt-get install -y \
    time \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Processing-focused Python dependencies
RUN pip install --no-cache-dir \
    "spikeinterface==0.98.0" \
    "braingeneers[iot, analysis, data]" \
    numpy \
    scipy \
    h5py \
    matplotlib \
    seaborn \
    pandas \
    scikit-learn \
    numba \
    tbb \
    pynwb \
    kubernetes

# Install shared utilities
COPY shared/ /usr/local/lib/python3.10/site-packages/maxwell_shared/
ENV PYTHONPATH="/usr/local/lib/python3.10/site-packages:$PYTHONPATH"

# Processing configuration
ENV PROCESSING_TYPE="container"
ENV ENDPOINT_URL="https://braingeneers.gi.ucsc.edu"
WORKDIR /app
