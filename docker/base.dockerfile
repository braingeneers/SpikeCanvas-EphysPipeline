# Base Dockerfile for all ephys pipeline components
FROM python:3.10
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    time \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies - common to all components
RUN pip install --no-cache-dir \
    "spikeinterface==0.98.0" \
    "braingeneers[iot, analysis, data]" \
    numpy \
    deprecated \
    numba \
    tbb \
    h5py \
    scipy \
    glances \
    pynwb \
    kubernetes \
    pyyaml \
    pytest

# PRP setup
ENV ENDPOINT_URL="https://braingeneers.gi.ucsc.edu"

# Install core library
COPY maxwell_ephys_core/ /usr/local/lib/python3.10/site-packages/maxwell_ephys_core/

# Common utilities
COPY shared/ /shared/
WORKDIR /app
