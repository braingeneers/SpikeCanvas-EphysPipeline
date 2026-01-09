# EphysPipeline (Maxwell Electrophysiology Pipeline)

EphysPipeline is the Braingeneers/Maxwell electrophysiology workflow: containerized algorithms, Kubernetes job orchestration, and the SpikeCanvas dashboard for end-to-end processing from raw recordings to curated analyses and visualizations.

## Objectives
- Provide a repeatable, scalable pipeline from raw data to curated outputs and figures.
- Run algorithm stages as containerized batch jobs on Kubernetes with S3-backed storage.
- Offer a dashboard for dataset selection, job submission, parameter management, and monitoring.
- Support institution-specific S3 deployments via a centralized configuration layer.
- Keep algorithms consistent via a shared path contract and helper utilities.

## Overview
This repository contains the source code and services described in the preprint "Multiscale Cloud-Based Pipeline for Neuronal Electrophysiology Analysis and Visualization" (bioRxiv, 2024): https://www.biorxiv.org/content/10.1101/2024.11.14.623530v2.

SpikeCanvas is the user-facing entry point for selecting datasets, creating jobs, and monitoring spike sorting, connectivity, curation, visualization, and LFP tasks.

## Repository layout
```
EphysPipeline/
|-- Algorithms/               # Core processing algorithms
|   |-- connectivity/         # Functional connectivity analysis
|   |-- kilosort2_simplified/ # Spike sorting with Kilosort2
|   |-- local_field_potential/ # LFP analysis and filtering
|   |-- si_curation_docker/   # Quality control and curation
|   `-- visualization/        # Data visualization tools
|-- Services/                 # Platform services and interfaces
|   |-- MaxWell_Dashboard/    # SpikeCanvas web dashboard
|   |-- Spike_Sorting_Listener/ # Job orchestration service
|   |-- job_scanner/          # Job monitoring and status tracking
|   |-- maxtwo_splitter/      # Data preprocessing and splitting
|   `-- parameters/           # Configuration templates
|-- performance/              # Benchmarking and optimization tools
`-- docker-compose.yml         # Local services stack
```

## Algorithms
All algorithms follow the same three-step workflow:
1. Load data from S3
2. Process the data
3. Save results back to S3

Key implementations:
- `Algorithms/kilosort2_simplified/`: spike sorting automation and Kilosort2 job launcher.
- `Algorithms/connectivity/`: connectivity analysis on spike sorting outputs.
- `Algorithms/local_field_potential/`: LFP filtering, windowing, and downsampling.
- `Algorithms/si_curation_docker/`: SpikeInterface-based quality metrics and auto-curation.
- `Algorithms/visualization/`: Plotly summaries and single-unit visualization bundles.

## Services
- `Services/MaxWell_Dashboard/`: SpikeCanvas dashboard (Dash web UI) for job submission and monitoring.
- `Services/Spike_Sorting_Listener/`: MQTT-driven job listener that schedules Kubernetes jobs and supports chaining.
- `Services/job_scanner/`: job completion monitoring and status reporting.
- `Services/maxtwo_splitter/`: preprocessing/splitting utilities and optimization guidance.
- `Services/parameters/`: JSON parameter defaults for connectivity, curation, LFP, and related stages.
- Operational deployments are typically orchestrated from https://github.com/braingeneers/mission_control.

## Quick start
### Run the dashboard locally (Python)
```bash
cd Services/MaxWell_Dashboard
./start_dashboard.sh
```
The dashboard runs at `http://127.0.0.1:8050/`. Hosted access is available at https://mxwdash.braingeneers.gi.ucsc.edu (request access in `#braingeneers-helpdesk`).

### Run the services stack (Docker Compose)
```bash
cp .env.template .env
docker-compose up -d
```
Edit `.env` to set your S3 bucket and credentials before starting services.

## Pipeline configuration layer
The pipeline is configurable for external institutions and alternate S3 buckets.

Configuration precedence:
1. Environment variables (highest)
2. Optional YAML file at `/app/config/pipeline.yaml` or `PIPELINE_CONFIG`
3. Embedded defaults (prefix `ephys`, bucket must be provided)

Common environment variables:
- `S3_BUCKET`, `S3_PREFIX`, `S3_INPUT_PREFIX`, `S3_OUTPUT_PREFIX`
- `AWS_REGION`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `SERVICE_ROOT`, `SERVICE_BUCKET`, `PARAMETER_BUCKET`
- `NRP_NAMESPACE`
- `ENDPOINT_URL`, `S3_ENDPOINT`

Helper usage (recommended):
```python
from Services.common.config import load_config, s3_uri
cfg = load_config()
root = cfg.root()  # e.g. s3://my-bucket/ephys/
data_path = s3_uri("2025-01-01-e-example", "original", "data", "rec0000.raw.h5")
derived_path = s3_uri("2025-01-01-e-example", "derived", "kilosort2")
```
Do not hardcode `s3://braingeneers/ephys/`. The test `Services/tests/test_no_hardcoded_bucket.py` enforces this.

## Data layout and path helpers
S3 path contract:
- Inputs live under `<session_uuid>/original/data/...`.
- Outputs live under `<session_uuid>/derived/<stage>/...`.

Common artifact suffixes:
- `_phy.zip` (spike sorting output)
- `_acqm.zip` (auto-curated spikes)
- `_figure.zip` (visualization bundle)
- `_conn.zip` (connectivity output)

Helper functions in `Services/common/path_utils.py`:
- `replace_original_to_derived(base_path, stage)`
- `normalize_acqm_source(input_path)`
- `make_artifact_path(session_uuid, stage, basename, suffix, subdir=None)`

## Configuration and deployment notes
- Use `.env.template` as the starting point for S3, AWS, and namespace settings.
- In Kubernetes, prefer ConfigMaps and IAM roles (IRSA) over static keys.
- The listener injects S3 settings into algorithm jobs; keep `NRP_NAMESPACE` aligned with your cluster.

## Performance and testing
- `performance/` includes speed tests and optimization notes.
- `Services/maxtwo_splitter/SPEED_OPTIMIZATION_GUIDE.md` documents tuning for large recordings.

## Documentation
- Dashboard: `Services/MaxWell_Dashboard/README.md`
- Listener: `Services/Spike_Sorting_Listener/README.md`
- Algorithm docs: each subdirectory in `Algorithms/`
