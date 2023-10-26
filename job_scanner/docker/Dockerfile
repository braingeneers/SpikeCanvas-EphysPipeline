FROM python:3.10
ENV DEBIAN_FRONTEND=noninteractive
ENV DASH_DEBUG_MODE=False

RUN python -m pip install --force-reinstall 'git+https://github.com/braingeneers/braingeneerspy.git#egg=braingeneerspy[iot,analysis,data]'

RUN pip install kubernetes \
    uuid \
    deprecated

# PRP setup
ENV ENDPOINT_URL="https://s3.braingeneers.gi.ucsc.edu"

COPY src/ /app
WORKDIR /app

# run
CMD ["python", "job_scanner.py"]

## job_scanner:v0.1