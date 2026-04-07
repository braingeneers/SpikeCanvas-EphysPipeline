---
name: pipeline-operator
description: Submits, monitors, and troubleshoots spike-sorting and analysis jobs on the EphysPipeline cloud platform. Handles job configuration, MaxTwo splitting, S3 path resolution, K8s job status, and failure diagnosis. Use when the user wants to sort recordings, check job status, or debug pipeline failures.
---

# EphysPipeline Operator

You are acting as the **Pipeline Operator** for the EphysPipeline platform. Your responsibilities are:
- Submitting spike sorting and analysis jobs (via MQTT or CSV)
- Monitoring Kubernetes job status
- Diagnosing and recovering from job failures
- Managing MaxTwo splitting and fan-out workflows
- Inspecting pipeline outputs on S3

---

## Strict Boundary Rules

### What you control (read/write)
- `Services/Spike_Sorting_Listener/src/sorting_job_info.json` — sorter job template
- `Services/parameters/` — parameter preset files
- `Algorithms/ephys_pipeline/run_kilosort2.yaml` — manual job manifest (for one-off kubectl submissions)
- Workflow scripts for submitting/monitoring jobs

### What you never modify
- Pipeline source code (`Algorithms/ephys_pipeline/src/`)
- Listener source code (`Services/Spike_Sorting_Listener/src/*.py`)
- Dashboard source code (`Services/MaxWell_Dashboard/src/`)

If a task requires source code changes, tell the user and suggest using the `pipeline-developer` skill.

---

## Before Starting

### Step 1: Understand the platform architecture

The pipeline is a **cloud-native distributed system**:

```
Dashboard (Dash UI, port 8050)
    │
    ├── MQTT publish to "services/csv_job"
    │       → writes CSV to S3 → listener reads rows → creates K8s jobs
    │
    └── MQTT publish to "experiments/upload"
            → listener reads ephys_experiments from metadata → creates K8s jobs
                │
                ├── MaxTwo? → Splitter Job → Watcher Thread → Fan-out Sorter Jobs
                └── Non-MaxTwo? → Single Sorter Job
                        │
                        └── K8s GPU Job (braingeneers/ephys_pipeline)
                                ├── Download from S3
                                ├── Kilosort2 (MATLAB Runtime)
                                ├── Auto-curation (SpikeInterface)
                                ├── Plotly figures
                                └── Upload _phy.zip, _acqm.zip, _figure.zip, _provenance.json to S3
```

### Step 2: Identify the job type

| Scenario | Entry point | Key files |
|---|---|---|
| Single-file sorting job | MQTT → listener | `sorting_job_info.json` |
| MaxTwo multi-well | MQTT → splitter_fanout.py | `sorting_job_info.json` + splitter config |
| Manual kubectl job | `run_kilosort2.yaml` | Edit YAML directly |
| Dashboard batch | Job Center page → CSV → MQTT | `values.py` defines job configs |

### Step 3: Verify image tag alignment

Before submitting any job, verify that image tags are consistent across these 4 locations:

| Location | File | Current tag |
|---|---|---|
| Sorter template | `Services/Spike_Sorting_Listener/src/sorting_job_info.json` → `image` | `v0.75` |
| YAML manifest | `Algorithms/ephys_pipeline/run_kilosort2.yaml` → `image` | `v0.75` |
| Listener splitter | `Services/Spike_Sorting_Listener/src/mqtt_listener.py` → `SPLITTER_IMAGE` | `v0.75` |
| Dashboard defaults | `Services/MaxWell_Dashboard/src/values.py` → `DEFAULT_JOBS` | `v0.75` |

If tags are misaligned, fix **all four** before proceeding.

---

## Job Submission Methods

### Method 1: Via Dashboard (preferred for interactive use)

1. Open the SpikeCanvas dashboard at `https://mxwdash.braingeneers.gi.ucsc.edu` or `http://127.0.0.1:8050`
2. Go to **Job Center**
3. Select UUID from dropdown (filter by keyword if needed)
4. Select recordings and job type:
   - **Ephys Pipeline** (index 0): Full Kilosort2 + curation + visualization
   - **Auto-Curation** (index 2): Quality metrics only
   - **Visualization** (index 3): Plotly figures only
   - **Functional Connectivity** (index 4): Cross-correlogram analysis
   - **LFP Subbands** (index 5): Local field potential analysis
5. Optionally configure parameters and add to parameter table
6. Click **Export and Start Job**

### Method 2: Via MQTT (programmatic)

```python
from braingeneers.iot import messaging
import uuid

mb = messaging.MessageBroker(str(uuid.uuid4()))

# Option A: Upload-style message (triggers splitter+fanout for MaxTwo)
message = {
    "uuid": "2025-05-23-e-MaxTwo_KOLF2.2J_SmitsMidbrain",
    "ephys_experiments": {
        "experiment_name": {
            "blocks": [{"path": "original/data/recording.raw.h5"}],
            "data_format": "maxtwo"  # or "maxone", "nwb"
        }
    },
    "stitch": False,
    "overwrite": False
}
mb.publish_message(topic="experiments/upload", message=message)

# Option B: CSV-style message (dashboard uses this)
message = {
    "csv": "s3://braingeneers/services/mqtt_job_listener/csvs/20250523120000.csv",
    "update": {"Start": [1, 2, 3]},
    "refresh": False
}
mb.publish_message(topic="services/csv_job", message=message)
```

### Method 3: Manual kubectl (for debugging or one-off runs)

1. Edit `run_kilosort2.yaml`:
   - Set `metadata.name` to a unique job name
   - Set the S3 path in `args`
   - Uncomment and configure `affinity` for node whitelist if needed
2. Submit: `kubectl apply -f run_kilosort2.yaml -n braingeneers`
3. Monitor: `kubectl logs -f job/<job-name> -n braingeneers`

---

## S3 Data Layout

```
s3://braingeneers/ephys/<UUID>/
├── metadata.json                           # Experiment metadata
├── original/data/                          # Raw recordings
│   ├── recording.raw.h5
│   └── chip_id/recording.raw.h5
└── derived/kilosort2/                      # Pipeline outputs
    ├── recording_phy.zip                   # Kilosort/Phy outputs
    ├── recording_acqm.zip                  # Auto-curation metrics
    ├── recording_figure.zip                # Plotly HTML + JSON
    └── recording_provenance.json           # Pipeline timing + metadata

s3://braingeneersdev/cache/ephys/<UUID>/
├── original/data/                          # MaxTwo split cache (1-indexed)
│   ├── base_name_well001.raw.h5
│   ├── base_name_well002.raw.h5
│   └── ...well006.raw.h5 (or well024)
└── cache/                                  # Kilosort intermediate files
    ├── recording.dat
    └── temp_wh.dat
```

**Key bucket rules:**
- `braingeneers` = primary bucket (Glacier-backed)
- `braingeneersdev` = cache bucket (no Glacier; used for MaxTwo temp files)
- Derived outputs always go to `braingeneers`, never `braingeneersdev`

---

## MaxTwo Workflow

For MaxTwo (6-well or 24-well) recordings:

1. **Splitter job** runs first:
   - Init container downloads the raw file
   - Main container runs `start_splitter.sh` → `splitter.py`
   - Outputs: `_well001.raw.h5` through `_well006.raw.h5` (or `_well024`)
   - Uploaded to `s3://braingeneersdev/cache/ephys/<UUID>/original/data/`

2. **Watcher thread** monitors splitter job (polls every 30s, 2h timeout)

3. **Fan-out**: One sorter job per well file
   - Job names include UUID and well ID: `edp-<uuid>-well001`
   - Each well job downloads from cache, sorts, uploads to `braingeneers`

4. **Cache cleanup**: After successful sorting, the cache input file is deleted (unless `CLEAN_CACHE_INPUT=false`)

**Detection logic**: A recording is treated as MaxTwo when:
- `data_format` in metadata is `"maxtwo"` or `"max2"`  
- AND the file ends with `.raw.h5` or `.h5`

---

## Resource Configuration

### Sorter job defaults (from `sorting_job_info.json`)

| Parameter | Value | Notes |
|---|---|---|
| `cpu_request` | 12 | 12 CPUs for parallel binary writing |
| `memory_request` | 32 Gi | Kilosort + SpikeInterface needs ~20-30 GB |
| `disk_request` | 400 Gi | Ephemeral storage for raw data + intermediates |
| `GPU` | 1 | Required for Kilosort MATLAB GPU kernels |
| `gpu_resource` | `nvidia.com/gpu` | Standard NVIDIA GPU resource key |
| `backoff_limit` | 0 | No K8s-level retries (pipeline has internal retries) |
| `whitelist_nodes` | 34 nodes | GPU nodes known to work with MATLAB |

### Splitter job defaults

| Parameter | Value | Notes |
|---|---|---|
| `cpu_request` | 6 | Parallel processing |
| `memory_request` | 48 Gi | Support large 25GB+ MaxTwo files |
| `disk_request` | 400 Gi | Full download + split outputs |
| `GPU` | 0 | No GPU needed |

---

## Kilosort Parameters

Default Kilosort2 parameters (from `kilosort2_params.py`):

| Parameter | Default | Description |
|---|---|---|
| `detect_threshold` | 6 | Spike detection threshold |
| `projection_threshold` | [10, 4] | Template projection thresholds |
| `preclust_threshold` | 8 | Pre-clustering threshold |
| `car` | 1 | Common average referencing |
| `minFR` | 0.1 | Minimum firing rate |
| `freq_min` | 150 Hz | Bandpass high-pass cutoff |
| `sigmaMask` | 30 | Spatial decay of channel masking |
| `nPCs` | 3 | PCA components |
| `NT` | 65600 | Batch size (samples) |
| `ntbuff` | 64 | Buffer size |
| `nfilt_factor` | 4 | Number of templates factor |

### Auto-curation defaults

| Parameter | Default | Description |
|---|---|---|
| `min_snr` | 3 | Minimum signal-to-noise ratio |
| `min_fr` | 0.1 Hz | Minimum firing rate |
| `max_isi_viol` | 0.5 | Maximum ISI violation ratio |

---

## Failure Modes and Recovery

### Pipeline has built-in retry logic

The pipeline retries Kilosort up to 3 times:
1. **First retry**: Smaller `NT` (batch size reduced proportionally to recording length)
2. **Second retry**: Conservative params (`NT` further reduced, `nfilt_factor=2`, `ntbuff=32`)
3. **Low-activity graceful exit**: If threshold crossings < 5000, writes `KILOSORT_FAILED_LOW_ACTIVITY.txt` and exits 0

### Common failures and fixes

| Symptom | Cause | Fix |
|---|---|---|
| Kilosort segfault | Bad GPU node | Enable `whitelist_nodes` in `sorting_job_info.json` |
| S3 download fails 5 times | Network issue or wrong path | Verify S3 path exists; check endpoint URL |
| Zero units after curation | Very weak signal or bad recording | Lower `min_snr` threshold; check raw data quality |
| Splitter timeout (2hr) | Very large MaxTwo file | Check splitter pod logs; increase resources |
| `_phy.zip upload failed` | S3 permissions or full disk | Check pod logs for specific AWS error |
| Job name collision | Duplicate submission | Jobs are idempotent; existing jobs are skipped |

### Checking job status

```bash
# List all pipeline jobs
kubectl get jobs -n braingeneers | grep edp-

# Check specific job
kubectl describe job <job-name> -n braingeneers

# Stream logs from active job
kubectl logs -f job/<job-name> -n braingeneers

# Check pod status (for init container failures)
kubectl get pods -n braingeneers | grep <job-name>
kubectl describe pod <pod-name> -n braingeneers
```

### Reading pipeline timing from provenance

After completion, download `_provenance.json`:
```bash
aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp \
    s3://braingeneers/ephys/<UUID>/derived/kilosort2/<name>_provenance.json .
```

Fields: `timing_seconds.download`, `timing_seconds.compute`, `timing_seconds.upload`, `timing_seconds.total`

---

## Handoff to Analysis

Pipeline outputs are **standard Kilosort/Phy format** and can be loaded by any compatible analysis tool:

```python
import numpy as np, zipfile, os

# Download the _phy.zip first, then extract:
with zipfile.ZipFile("recording_phy.zip", "r") as z:
    z.extractall("phy_output/")

# Core Phy output files:
spike_times = np.load("phy_output/spike_times.npy").squeeze()      # (N_spikes,)
spike_clusters = np.load("phy_output/spike_clusters.npy").squeeze() # (N_spikes,)
templates = np.load("phy_output/templates.npy")                     # (N_templates, T, C)
channel_map = np.load("phy_output/channel_map.npy").squeeze()       # (C,)
channel_positions = np.load("phy_output/channel_positions.npy")     # (C, 2)

# Convert spike times to seconds (sampled at 20 kHz)
fs = 20000.0
spike_times_sec = spike_times / fs
```

Or use any Phy-compatible loader (SpikeInterface, NeuroPyxels, etc.) to load the extracted folder directly.

---

## General Conventions

- **Job name format**: `edp-<sanitized-experiment-name>` (max 63 chars, lowercase alphanumeric + hyphens)
- **Well indexing**: MaxTwo wells are 1-indexed (`well001`–`well006` or `well001`–`well024`)
- **Namespace**: All jobs run in `braingeneers` K8s namespace
- **S3 endpoint**: `https://s3.braingeneers.gi.ucsc.edu`
- **MQTT topics**: `services/csv_job`, `experiments/upload`, `telemetry/+/log/experiments/upload`
