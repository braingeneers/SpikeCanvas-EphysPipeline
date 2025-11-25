FROM python:3.10
ENV DEBIAN_FRONTEND=noninteractive
ENV DASH_DEBUG_MODE=False

RUN pip install "braingeneers[iot, analysis, data]"
RUN pip install kubernetes \
    uuid \
    deprecated

# PRP setup
ENV ENDPOINT_URL="https://s3.braingeneers.gi.ucsc.edu"

COPY src/ /app
WORKDIR /app

# run
CMD ["python", "mqtt_listener.py"]

# surygeng/spike_sorting_listener:v0.1