FROM python:3.10
ENV DEBIAN_FRONTEND=noninteractive
ENV DASH_DEBUG_MODE=False

# Set working directory first
WORKDIR /app

# Install braingeneers and requirements
RUN pip install --upgrade pip
# RUN pip install braingeneers['iot','analysis','data']
RUN pip install --force-reinstall git+https://github.com/braingeneers/braingeneerspy.git

# Copy and install requirements
COPY docker/requirements.txt ./requirements.txt
RUN set -ex && \
    pip install -r ./requirements.txt

# Copy scipy fix if needed
COPY docker/top_level.txt /usr/local/lib/python3.10/site-packages/scipy-1.10.1.dist-info/top_level.txt

# Copy source code
COPY src/ /app

# PRP setup
ENV ENDPOINT_URL="https://braingeneers.gi.ucsc.edu"

# Expose port
EXPOSE 8050

# Run command
CMD ["gunicorn", "--timeout", "1000", "--workers=1", "-b", "0.0.0.0:8050", "--reload", "app:server"]

# surygeng/maxwell_dashboard:v0.1