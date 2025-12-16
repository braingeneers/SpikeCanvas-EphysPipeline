# MQTT Job Listener Documentation

## Introduction

This service listens for experiment metadata on MQTT and launches the spike sorting pipeline on Kubernetes. The original version of this document described a legacy "jobs.csv" file that lived in S3; that mechanism is no longer used by the current codebase.

## How jobs are scheduled today

* The listener subscribes to `experiments/upload` and related telemetry topics. When an upload message arrives, it walks the embedded `ephys_experiments` metadata and schedules spike-sorting work for each recording. MaxTwo recordings fan out into splitter + sorter jobs when needed; other formats go straight to sorting.
* Job resource requirements (CPU, memory, disk, GPU, args, etc.) now come from JSON templates that live with the source: `sorting_job_info.json` for sorter pods and `get_splitter_config()` inside the listener for MaxTwo splitting. The code formats Kubernetes-safe job names, builds the pod spec, and submits jobs via the `Kube` helper rather than reading a CSV from S3.

The only remaining CSV handling in the code is for pipeline coordination files passed explicitly via MQTT (`services/csv_job`), not for defining job types. The S3 `jobs.csv` referenced by the old documentation is not used.

## Software architecture

The service is implemented in Python and centers on two helpers:

* `MQTTJobListener` parses incoming messages and decides whether to launch sorting directly or trigger a CSV-driven job update for pipeline bookkeeping.
* `Kube` (in `k8s_kilosort2.py`) constructs and submits Kubernetes `Job` objects with the requested resources and environment needed to access Braingeneers S3.

Logging is pushed to S3 and Slack notifications are emitted for job lifecycle events.

## Administration and Maintenance

The application runs as a Docker process on our server. It's included in the standard Docker compose script, which can be found in the Mission_Control repository.

### Updating the MQTT Job Listener

To update the MQTT Job Listener, modify the source code and rebuild the Docker image. The updated image should then be deployed via the Docker compose script.

### Error handling

Errors and exceptions during job execution are logged and can be inspected for troubleshooting. It's important to regularly check these logs to ensure the application is functioning correctly.

## Where Kubernetes job manifests live now

Kubernetes manifests for the underlying algorithms live alongside the code for each stage of the pipeline under `Algorithms/*/k8s/`. For example, the Kilosort2 job template is in `Algorithms/kilosort2_simplified/run_kilosort2.yaml` and LFP, connectivity, and visualization jobs have similar manifests under their respective `k8s` directories.

Please review the Mission Control deployment for image packaging, but use this repository for the authoritative job definitions.
