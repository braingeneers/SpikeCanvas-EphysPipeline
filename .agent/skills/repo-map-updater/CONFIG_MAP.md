# SpikeCanvas Configuration Map

> Last updated: 2026-04-06

All tunable parameters, paths, and configuration values across the SpikeCanvas platform.

---

## Image Tags

All pipeline image tags **must stay aligned** across these 4 locations:

| # | Location | File | Field | Current Value |
|---|---|---|---|---|
| 1 | Sorter template | `Services/Spike_Sorting_Listener/src/sorting_job_info.json` | `"image"` | `braingeneers/ephys_pipeline:v0.75` |
| 2 | K8s manifest | `Algorithms/ephys_pipeline/run_kilosort2.yaml` | `containers[0].image` | `braingeneers/ephys_pipeline:v0.75` |
| 3 | Splitter constant | `Services/Spike_Sorting_Listener/src/mqtt_listener.py` | `SPLITTER_IMAGE` | `braingeneers/maxtwo_splitter:v0.75` |
| 4 | Dashboard defaults | `Services/MaxWell_Dashboard/src/values.py` | `DEFAULT_JOBS` | `braingeneers/ephys_pipeline:v0.75` |

### Additional images (non-pipeline)

| Image | Version | Purpose | File |
|---|---|---|---|
| `surygeng/qm_curation` | `v0.2` | Auto-curation by quality metrics | `values.py` |
| `surygeng/visualization` | `v0.1` | Plotly visualization | `values.py` |
| `surygeng/connectivity` | `v0.1` | Functional connectivity analysis | `values.py` |
| `surygeng/local_field_potential` | `v0.1` | LFP subband analysis | `values.py` |

---

## Job Configuration (`sorting_job_info.json`)

```json
{
  "image": "braingeneers/ephys_pipeline:v0.75",
  "cpu_request": 12,
  "memory_request": "32Gi",
  "disk_request": "400Gi",
  "backoff_limit": 0,
  "gpu_request": 1,
  "gpu_resource": "nvidia.com/gpu",
  "whitelist_nodes": [
    "k8s-braingeneers-gpu-01.nrp-nautilus.io",
    "k8s-braingeneers-gpu-02.nrp-nautilus.io",
    "... (34 nodes total)"
  ]
}
```

| Field | Type | Purpose |
|---|---|---|
| `image` | string | Docker image for the sorter container |
| `cpu_request` | int | CPU cores requested |
| `memory_request` | string | Memory request (with unit suffix) |
| `disk_request` | string | Ephemeral storage request |
| `backoff_limit` | int | K8s retry count (0 = no retries) |
| `gpu_request` | int | Number of GPUs |
| `gpu_resource` | string | K8s GPU resource key |
| `whitelist_nodes` | list[str] | Node affinity whitelist (MATLAB stability) |

---

## Dashboard Job Defaults (`values.py`)

### Batch mode

| Field | Value |
|---|---|
| Image | `braingeneers/ephys_pipeline:v0.75` |
| Args | `./run.sh` |
| CPU | 12 |
| Memory | 32 Gi |
| Disk | 400 Gi |
| GPU | 1 |
| Params label | `pipeline` |

### Individual job types

| Index | Name | Image | Args | CPU | Mem | Disk | GPU | Params label |
|---|---|---|---|---|---|---|---|---|
| 0 | Ephys Pipeline | `braingeneers/ephys_pipeline:v0.75` | `./run.sh` | 12 | 32 | 400 | 1 | `pipeline` |
| 2 | Auto-Curation | `surygeng/qm_curation:v0.2` | `python si_curation.py` | 8 | 32 | 400 | 0 | `curation` |
| 3 | Visualization | `surygeng/visualization:v0.1` | `python viz.py` | 2 | 16 | 8 | 0 | `visualization` |
| 4 | Func. Connectivity | `surygeng/connectivity:v0.1` | `python run_conn.py` | 2 | 16 | 8 | 0 | `connectivity` |
| 5 | LFP Subbands | `surygeng/local_field_potential:v0.1` | `python run_lfp.py` | 4 | 64 | 64 | 0 | `lfp` |

Note: Index 1 is not used (removed standalone Kilosort option).

---

## Kilosort2 Parameters (`kilosort2_params.py`)

| Parameter | Default | Description |
|---|---|---|
| `detect_threshold` | 6 | Spike detection threshold (multiples of noise) |
| `projection_threshold` | [10, 4] | Template projection thresholds [initial, final] |
| `preclust_threshold` | 8 | Pre-clustering threshold |
| `car` | 1 | Common average referencing (1=enabled) |
| `minFR` | 0.1 | Minimum firing rate for template acceptance |
| `minfr_goodchannels` | 0.1 | Min FR for good channel detection |
| `freq_min` | 150 Hz | High-pass filter cutoff |
| `sigmaMask` | 30 | Spatial decay constant for channel masking |
| `nPCs` | 3 | Number of PCA components |
| `ntbuff` | 64 | Buffer overlap between batches |
| `nfilt_factor` | 4 | Template count factor |
| `NT` | 65600 | Batch size in samples |
| `keep_good_only` | False | Keep all clusters, not just "good" |
| `total_memory` | "2G" | Memory limit for binary operations |
| `n_jobs_bin` | 64 | Parallel jobs for binary file processing |
| `trange` | [0, inf] | Time range to sort (seconds) |

### Preprocessing

| Parameter | Value | Source |
|---|---|---|
| `band_min` | 300 Hz | `kilosort2_params.py` |
| `band_max` | 6000 Hz | `kilosort2_params.py` |

### Retry fallback overrides

| Attempt | NT | detect_threshold | nfilt_factor | ntbuff |
|---|---|---|---|---|
| 1 (default) | 65600 | 6 | 4 | 64 |
| 2 (first retry) | scaled by length | 9 | 4 | 64 |
| 3 (second retry) | minimum | 9 | 2 | 32 |

---

## Auto-Curation Defaults (`utils.py`)

| Parameter | Default | Description |
|---|---|---|
| `min_snr` | 5 | Minimum signal-to-noise ratio |
| `min_fr` | 0.1 Hz | Minimum firing rate |
| `max_isi_viol` | 0.2 | Maximum ISI violation ratio |

Note: The variable is named `DEFAULT_PARAM_LIST` in the code.

### Pipeline-internal curation (kilosort2_simplified.py)

Uses `DEFUALT_PARAMS` (typo preserved):

| Parameter | Default | Description |
|---|---|---|
| `min_snr` | 3 | Minimum SNR (lower than utils.py default) |
| `min_fr` | 0.1 | Minimum firing rate |
| `max_isi_viol` | 0.5 | Maximum ISI violation (more permissive) |

---

## S3 Paths

| Pattern | Purpose | Used by |
|---|---|---|
| `s3://braingeneers/ephys/<UUID>/` | Root experiment directory | All components |
| `s3://braingeneers/ephys/<UUID>/metadata.json` | Experiment metadata | Dashboard, Listener |
| `s3://braingeneers/ephys/<UUID>/original/data/` | Raw recording files | Pipeline, Dashboard |
| `s3://braingeneers/ephys/<UUID>/derived/kilosort2/` | Pipeline output artifacts | Pipeline upload |
| `s3://braingeneersdev/cache/ephys/<UUID>/original/data/` | MaxTwo split well files | Splitter, Pipeline |
| `s3://braingeneers/services/mqtt_job_listener/csvs/` | Job submission CSVs | Dashboard, Listener |
| `s3://braingeneers/services/mqtt_job_listener/params/` | Parameter preset files | Dashboard, Pipeline |

### S3 Endpoint

```
https://s3.braingeneers.gi.ucsc.edu
```

---

## MQTT Topics

| Topic | Publisher | Subscriber | Message Schema |
|---|---|---|---|
| `experiments/upload` | External upload script | Listener | `{"uuid": str, "ephys_experiments": dict, "stitch": bool, "overwrite": bool}` |
| `services/csv_job` | Dashboard | Listener | `{"csv": str, "update": {"Start": [int]}, "refresh": bool}` |
| `telemetry/<uuid>/log/experiments/upload` | Listener | (monitoring) | Job status telemetry |

---

## K8s Resources

| Job Type | CPU | Memory | Disk | GPU | Node Whitelist |
|---|---|---|---|---|---|
| Ephys Pipeline (sorter) | 12 | 32 Gi | 400 Gi | 1 | Yes (34 nodes) |
| MaxTwo Splitter | 6 | 48 Gi | 400 Gi | 0 | **No** |
| Auto-Curation | 8 | 32 Gi | 400 Gi | 0 | No |
| Visualization | 2 | 16 Gi | 8 Gi | 0 | No |
| Connectivity | 2 | 16 Gi | 8 Gi | 0 | No |
| LFP Subbands | 4 | 64 Gi | 64 Gi | 0 | No |

### K8s Namespace

```
braingeneers
```

### Job Name Format

```
edp-<sanitized-experiment-name>
```
- Prefix: `edp-` (from `JOB_PREFIX` in values.py)
- Max length: 63 characters
- Characters: lowercase alphanumeric + hyphens only

---

## Environment Variables

| Variable | Used by | Purpose |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Pipeline, Dashboard | S3 authentication |
| `AWS_SECRET_ACCESS_KEY` | Pipeline, Dashboard | S3 authentication |
| `MQTT_BROKER` | Listener, Dashboard | MQTT broker address |
| `KUBECONFIG` | Listener, Status page | K8s API access |
| `CLEAN_CACHE_INPUT` | Pipeline | Whether to delete cache after sort (default: true) |

---

## Dashboard Constants (`values.py`)

| Constant | Value | Purpose |
|---|---|---|
| `TOPIC` | `"service/csv_job"` | MQTT topic |
| `TABLE_HEADERS` | 12 columns | CSV/DataTable schema |
| `LOCAL_CSV` | `"jobs.csv"` | Local fallback filename |
| `SERVICE_BUCKET` | `s3://braingeneers/services/mqtt_job_listener/csvs` | CSV upload target |
| `PARAMETER_BUCKET` | `s3://braingeneers/services/mqtt_job_listener/params` | Parameter files |
| `DEFAULT_BUCKET` | `s3://braingeneers/ephys/` | UUID listing root |
| `JOB_PREFIX` | `"edp-"` | K8s pod name filter |
| `NAMESPACE` | `"braingeneers"` | K8s namespace |
| `FINISH_FLAGS` | `["Succeeded", "Failed", "Unknown"]` | Terminal pod states |

### Table Headers (CSV Schema)

```
index, status, uuid, experiment, image, args, params,
cpu_request, memory_request, disk_request, GPU, next_job
```

### Job Parameter Fields

| Job Index | Parameters |
|---|---|
| 0 | (not yet available) |
| 2 | Minimum SNR, Minimum Firing Rate, Maximum ISI Violation |
| 3 | (not yet available) |
| 4 | Raster Bin Size, Cross-correlogram Window, Max Functional Latency, Max Poisson p |
| 5 | Analysis Start Time, Analysis End Time |
