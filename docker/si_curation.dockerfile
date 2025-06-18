# Example: SI Curation specific Dockerfile
FROM maxwell_ephys_base:latest

# Component-specific dependencies (if any)
RUN pip install --no-cache-dir \
    additional_curation_deps

# Copy component code
COPY si_curation/ /app/
WORKDIR /app

ENTRYPOINT ["python", "si_curation.py"]
