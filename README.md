# EphysPipeline

## Overview
EphysPipeline collects the algorithms and services used to run the Braingeneers electrophysiology workflow, from Kubernetes-hosted batch jobs to a full-featured web dashboard. The SpikeCanvas dashboard provides the user-facing entry point for dataset selection, job creation, parameter management, and monitoring across spike sorting, connectivity, and LFP tasks.【F:Services/MaxWell_Dashboard/README.md†L1-L66】

This repository contains the source code and supporting services described in the preprint “Multiscale Cloud-Based Pipeline for Neuronal Electrophysiology Analysis and Visualization” (bioRxiv, 2024). Read the paper at https://www.biorxiv.org/content/10.1101/2024.11.14.623530v2.

## Repository layout
### Algorithms
All algorithms follow the same three-step workflow:
1. **Load data from S3** – Download input data (raw recordings, spike-sorting results, or intermediate outputs)
2. **Process** – Apply the algorithm-specific computation (spike sorting, connectivity analysis, LFP filtering, curation, or visualization)
3. **Save results to S3** – Upload processed outputs back to S3 storage for downstream use or visualization

Individual algorithm implementations:
- **Ephys pipeline** – automation script that builds the spike-sorting Docker image and launches the accompanying Kubernetes job defined in `run_kilosort2.yaml`. Use it as a reference for running the full pipeline in cluster environments.【F:Algorithms/ephys_pipeline/run.sh†L1-L10】
- **Connectivity analysis** – `src/run_conn.py` downloads spike-sorting results from S3, applies default cross-correlogram parameters, and writes connectivity outputs back to storage, logging progress throughout the job.【F:Algorithms/connectivity/src/run_conn.py†L14-L119】
- **Local field potential (LFP)** – `src/run_lfp.py` loads Maxwell HDF5 recordings from S3, parses JSON parameter files to pick start/end windows, applies filtering/downsampling, and saves the processed segment back to derived storage paths.【F:Algorithms/local_field_potential/src/run_lfp.py†L128-L199】
- **SpikeInterface auto-curation** – `src/si_curation.py` runs a SpikeInterface-based quality-metric pass (SNR, ISI violations, firing rate, redundant units) with tunable defaults to prune low-quality units and persist cleaned waveforms.【F:Algorithms/si_curation_docker/src/si_curation.py†L30-L109】 Redundant-unit curation is computed for reporting but does not remove units (the other metrics drive removals).
- **Visualization jobs** – `src/viz.py` downloads curated or raw spike data from S3, converts it into spike trains, generates Plotly summaries plus single-unit plots, and re-uploads the packaged HTML/JSON artifacts.【F:Algorithms/visualization/src/viz.py†L28-L101】

### Services
- **SpikeCanvas dashboard (MaxWell_Dashboard)** – Dash-based web UI for selecting datasets by UUID, queuing pipeline jobs (spike sorting, auto-curation, visualization, functional connectivity, LFP subbands), adjusting parameter files, and exporting batches of jobs for execution.【F:Services/MaxWell_Dashboard/README.md†L1-L66】 The `start_dashboard.sh` script checks Python dependencies, sets `PYTHONPATH`, and runs `app.py` so the dashboard is reachable on port 8050.【F:Services/MaxWell_Dashboard/start_dashboard.sh†L3-L60】
- **MQTT job listener** – Schedules Kubernetes jobs in response to MQTT topics defined in an S3-hosted CSV, with built-in chaining so one job’s completion event can trigger the next.【F:Services/Spike_Sorting_Listener/README.md†L5-L35】【F:Services/Spike_Sorting_Listener/README.md†L23-L46】
  - **Job entry points** – The uploader publishes to `experiments/upload` (runs `run_sorting()`), while the dashboard Job Center publishes to `services/csv_job` after writing a CSV to `s3://braingeneers/services/mqtt_job_listener/csvs/`. Both paths end up in `mqtt_listener.py`, but the CSV path bypasses `run_sorting()` and launches jobs directly from the CSV rows.
- **MaxTwo handling** – The listener submits a dedicated MaxTwo splitter job before launching sorter jobs. The splitter job runs a download-only init container, then performs the split/upload in the main container; it exits quickly if the dataset is not `maxtwo`/`max2`. When the splitter completes, sorter jobs fan out over cached split files in `s3://braingeneersdev/cache/ephys/<UUID>/original/data/` (legacy cache paths under `original/split/` are still recognized), and the sorter script falls back to the standard `braingeneers` bucket for non-MaxTwo data.
  - **Well indexing** – MaxTwo split outputs are 1-indexed (`well001`–`well006` or `well001`–`well024`) to match Maxwell’s well labels.
  - **Cache bucket policy** – The primary `braingeneers` bucket is backed up to AWS Glacier, so MaxTwo splitter outputs are always written to the `braingeneersdev` bucket. The cache keys mirror the primary bucket layout (same `cache/ephys/<UUID>/...` structure) to make lookup and debugging predictable while avoiding Glacier storage for temporary splits.
- **Job scanner** – Notes on the job-scanner service describe how completion timestamps are derived from Kubernetes pod conditions to avoid start/end times being reported as identical, improving dashboard status accuracy.【F:Services/job_scanner/TIMESTAMP_FIX_SUMMARY.md†L1-L120】
- **MaxTwo splitter** – Optimization guide for the splitter service, detailing parallel uploads, multiprocessing, and resource tuning to reduce end-to-end runtime from hours to under an hour for large recordings.【F:Services/maxtwo_splitter/SPEED_OPTIMIZATION_GUIDE.md†L1-L103】
- **Parameter presets** – JSON defaults for pipeline components (e.g., connectivity, curation, LFP) live under `Services/parameters/`, providing starting values such as cross-correlogram bin sizes and auto-curation thresholds.【F:Services/parameters/connectivity/params_default.json†L1-L4】【F:Services/parameters/curation/params_default.json†L1-L1】【F:Services/parameters/lfp/params_default.json†L1-L4】
- **Mission Control deployment** – The operational instances of these services are orchestrated from the [braingeneers/mission_control](https://github.com/braingeneers/mission_control) repository, which provides Docker Compose configurations for launching the dashboard, listeners, and supporting components as a cohesive stack.

### Performance
- **speed_test** – Utilities for stress-testing Kubernetes batch throughput, including a script that times launching and tracking 100 spike-sorting jobs and logs completion status to JSON for later analysis.【F:performance/speed_test/test.py†L1-L111】

## Quick start
1. Install Python with Dash and the other listed dependencies, then run the dashboard launcher:
   ```bash
   cd Services/MaxWell_Dashboard
   ./start_dashboard.sh
   ```
   The script will verify or install required packages, set `PYTHONPATH`, and start the Dash app on `http://127.0.0.1:8050/`. Stop the server with `Ctrl+C` when finished.【F:Services/MaxWell_Dashboard/start_dashboard.sh†L3-L60】
   Authorized users can also access the hosted dashboard at https://mxwdash.braingeneers.gi.ucsc.edu; request access in the `#braingeneers-helpdesk` Slack channel to be added.
2. Use the Job Center to submit spike sorting, connectivity, curation, visualization, or LFP jobs, and monitor their status in the dashboard’s Status Monitor page.【F:Services/MaxWell_Dashboard/README.md†L36-L66】 Job definitions can also be triggered programmatically through the MQTT job listener for automated workflows.【F:Services/Spike_Sorting_Listener/README.md†L5-L35】
3. For production deployments, use the Docker Compose stack in the mission control repository to bring up the dashboard and listeners together, ensuring consistent configuration across services.

## Parameter management
Reusable parameter JSON files reside in `Services/parameters/`. For example, connectivity jobs default to a 1 ms bin size with a 50 ms window and 5 ms functional latency, while auto-curation defaults to a minimum signal-to-noise ratio of 5 and minimum firing rate of 0.1 Hz.【F:Services/parameters/connectivity/params_default.json†L1-L4】【F:Services/parameters/curation/params_default.json†L1-L1】 Update or copy these files when you need custom settings for new jobs.
