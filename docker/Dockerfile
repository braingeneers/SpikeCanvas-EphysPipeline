FROM python:3.10
ENV DEBIAN_FRONTEND=noninteractive
ENV DASH_DEBUG_MODE=False
COPY ./src /app
WORKDIR /app

RUN python -m pip install --force-reinstall 'git+https://github.com/braingeneers/braingeneerspy.git#egg=braingeneerspy[all]'
RUN set -ex && \
    pip install -r requirements.txt

# PRP setup
ENV ENDPOINT_URL="https://s3-west.nrp-nautilus.io"

# run locally
EXPOSE 8050
CMD ["gunicorn", "-b", "0.0.0.0:8050", "--reload", "app:server"]