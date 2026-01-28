FROM python:3.12
ENV DEBIAN_FRONTEND=noninteractive
ENV DASH_DEBUG_MODE=False

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    time \
    libxt-dev \
    curl \
    git \
    wget \
    build-essential \
    awscli \
    zip \
    glances \
    pv \
    bc \
    coreutils \
    gawk \
    openssl \
    psmisc \
    && rm -rf /var/lib/apt/lists/* && \
    command -v /usr/bin/time

RUN pip install "braingeneers[iot,analysis,data]"
RUN pip install deprecated \ 
    matplotlib \
    tqdm \
    psutil

# PRP setup
ENV ENDPOINT_URL="https://s3.braingeneers.gi.ucsc.edu"

COPY src/ /app/
RUN chmod +x /app/start_splitter.sh /app/download_only.sh /app/splitter.py

WORKDIR /app

# surygeng/maxtwo_splitter:v0.1
