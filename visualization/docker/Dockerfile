FROM python:3.10
ENV DEBIAN_FRONTEND=noninteractive
ENV DASH_DEBUG_MODE=False

RUN apt-get update && apt-get install -y time

RUN pip install "braingeneers[iot,analysis,data]"
RUN pip install numpy \
dash~=2.13.0 \
plotly \
pandas \
gunicorn \
dash_daq \
scipy \
dash_bootstrap_components \
deprecated 

# PRP setup
ENV ENDPOINT_URL="https://s3.braingeneers.gi.ucsc.edu"

COPY src/ /app
WORKDIR /app

# container name: visualization:v0.1