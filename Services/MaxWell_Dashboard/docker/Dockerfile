FROM python:3.10
ENV DEBIAN_FRONTEND=noninteractive
ENV DASH_DEBUG_MODE=False

# Set working directory first
WORKDIR /app

# Install braingeneers and requirements
RUN pip install --upgrade pip

# Copy and install requirements first
COPY docker/requirements.txt ./requirements.txt
RUN set -ex && \
    pip install -r ./requirements.txt

# Install braingeneers from GitHub (always most up-to-date)
RUN pip install "git+https://github.com/braingeneers/braingeneerspy.git#egg=braingeneers[iot,analysis,data]"

# Manually create _version.py since git metadata is not preserved during pip install from git
RUN echo 'version = "0.0.0+git"' > /usr/local/lib/python3.10/site-packages/braingeneers/_version.py

# Copy scipy fix if needed
COPY docker/top_level.txt /usr/local/lib/python3.10/site-packages/scipy-1.10.1.dist-info/top_level.txt

# Copy source code
COPY src/ /app

# Environment setup
ENV ENDPOINT_URL="https://braingeneers.gi.ucsc.edu"
ENV S3_ENDPOINT="s3.braingeneers.gi.ucsc.edu"

# Expose port
EXPOSE 8050

# Run command
CMD ["gunicorn", "--timeout", "1000", "--workers=1", "-b", "0.0.0.0:8050", "--reload", "app:server"]

# surygeng/maxwell_dashboard:v0.1