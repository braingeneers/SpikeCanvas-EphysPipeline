# SpikeCanvas Component Map

> Last updated: 2026-04-06

## Directory Structure

```
SpikeCanvas-EphysPipeline/
├── AGENTS.md                               # Agent guidance and repo conventions
├── README.md                               # Project overview and quick start
├── .agent/                                 # Agent skills and workflows
│   ├── skills/
│   │   ├── pipeline-operator/              # Job submission and monitoring
│   │   ├── pipeline-developer/             # Code modification and testing
│   │   ├── dashboard-operator/             # Dashboard UI operations
│   │   ├── data-investigator/              # S3 data inspection
│   │   └── repo-map-updater/               # This skill + maps
│   └── workflows/                          # Step-by-step operational workflows
│
├── Algorithms/
│   └── ephys_pipeline/                     # GPU-based spike sorting pipeline
│       ├── Dockerfile                      # Container build (MATLAB Runtime + Python)
│       ├── run_kilosort2.yaml              # K8s job manifest template
│       └── src/
│           ├── run.sh                      # Entrypoint: S3 download → sort → upload
│           ├── kilosort2_simplified.py     # Core pipeline logic (RunKilosort class)
│           ├── kilosort2_params.py         # Kilosort default parameters
│           ├── utils.py                    # Analysis utilities (STTC, templates, etc.)
│           ├── acqm.py                     # Auto-curation quality metrics
│           ├── figures.py                  # Plotly HTML figure generation
│           └── provenance.py               # Timing and metadata logging
│
├── Services/
│   ├── Spike_Sorting_Listener/             # MQTT job orchestration service
│   │   ├── Dockerfile
│   │   └── src/
│   │       ├── mqtt_listener.py            # MQTT handler + JobMessage class
│   │       ├── splitter_fanout.py          # MaxTwo split + fan-out logic
│   │       ├── k8s_kilosort2.py            # Kube class (K8s job builder)
│   │       ├── job_utils.py                # Job naming + S3 constants
│   │       ├── sorting_job_info.json       # Sorter job template (resources, image, whitelist)
│   │       └── job_type_table.json         # Image → human-readable name mapping
│   │
│   ├── MaxWell_Dashboard/                  # Dash web application
│   │   ├── Dockerfile
│   │   └── src/
│   │       ├── app.py                      # Dash entry point (multi-page)
│   │       ├── values.py                   # Constants, job configs, S3 paths
│   │       ├── utils.py                    # S3 upload, MQTT publish, metadata parsing
│   │       └── pages/
│   │           ├── home.py                 # Landing page (path: /)
│   │           ├── job_center.py           # Job configuration + submission
│   │           ├── status.py               # K8s pod status monitor
│   │           └── analytics.py            # Data visualization (interactive plots)
│   │
│   └── maxtwo_splitter/                    # MaxTwo well-splitting service
│       ├── Dockerfile
│       └── src/
│           ├── splitter.py                 # HDF5 well extraction logic
│           └── start_splitter.sh           # Entrypoint script
│
└── tests/                                  # Test suite
    ├── test_pipeline_exclusivity.py
    └── test_sequencing.py
```

---

## Component Overview

| Component | Directory | Purpose | Runtime |
|---|---|---|---|
| **Ephys Pipeline** | `Algorithms/ephys_pipeline/` | GPU spike sorting (Kilosort2), auto-curation, visualization | K8s Job (GPU) |
| **MQTT Listener** | `Services/Spike_Sorting_Listener/` | Job orchestration: receives MQTT → creates K8s jobs | Docker container |
| **MaxTwo Splitter** | `Services/maxtwo_splitter/` | Splits multi-well MaxTwo recordings into per-well files | K8s Job (CPU) |
| **SpikeCanvas Dashboard** | `Services/MaxWell_Dashboard/` | Web UI for job submission, monitoring, analytics | Docker container |

---

## Data Flow

```
                                ┌─────────────────────────────────────┐
                                │        SpikeCanvas Dashboard        │
                                │   (Dash app on port 8050)           │
                                └──────────┬──────────────────────────┘
                                           │
                          ┌────────────────┤ MQTT "services/csv_job"
                          │                │ OR "experiments/upload"
                          ▼                │
                 ┌────────────────┐        │
                 │  MQTT Broker   │◄───────┘
                 └───────┬────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   MQTT Listener     │
              │  (mqtt_listener.py) │
              └──────┬──────────────┘
                     │
          ┌──────────┴──────────┐
          │ MaxTwo?             │ Standard?
          ▼                    ▼
  ┌──────────────┐    ┌──────────────────┐
  │ Splitter Job │    │ Sorter Job       │
  │ (CPU only)   │    │ (GPU required)   │
  └──────┬───────┘    └────────┬─────────┘
         │                     │
         ▼                     │
  ┌──────────────┐             │
  │ Watcher      │             │
  │ Thread       │             │
  │ (polls K8s)  │             │
  └──────┬───────┘             │
         │ on success          │
         ▼                     │
  ┌──────────────┐             │
  │ Fan-out:     │             │
  │ 1 job/well   │─────────────┘
  └──────────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  Ephys Pipeline     │
          │  Container          │
          │                     │
          │  1. S3 download     │
          │  2. Kilosort2       │
          │  3. Auto-curation   │
          │  4. Plotly figures   │
          │  5. S3 upload       │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  S3 Outputs         │
          │  _phy.zip           │
          │  _acqm.zip          │
          │  _figure.zip        │
          │  _provenance.json   │
          └─────────────────────┘
```

---

## Service Interactions

| From | To | Protocol | Topic/Path | Purpose |
|---|---|---|---|---|
| Dashboard | MQTT Broker | MQTT publish | `services/csv_job` | Trigger CSV-based job submission |
| Dashboard | S3 | HTTPS | `services/mqtt_job_listener/csvs/` | Upload job CSV |
| Listener | MQTT Broker | MQTT subscribe | `experiments/upload` | Receive upload notifications |
| Listener | MQTT Broker | MQTT subscribe | `services/csv_job` | Receive CSV job triggers |
| Listener | K8s API | REST | `braingeneers` namespace | Create/monitor jobs |
| Listener | S3 | HTTPS | CSVs, metadata, cache | Read job specs and check cache |
| Listener | MQTT Broker | MQTT publish | `telemetry/+/log/...` | Publish job telemetry |
| Pipeline | S3 | HTTPS (aws cli) | `braingeneers` + `braingeneersdev` | Download raw, upload results |
| Splitter | S3 | HTTPS | `braingeneersdev/cache/` | Upload split well files |
| Status Page | K8s API | REST | `braingeneers` namespace | List pod statuses |

---

## File Reference

### Algorithms/ephys_pipeline/src/

| File | Lines | Description |
|---|---|---|
| `run.sh` | ~312 | Entrypoint script: handles S3 paths, manages downloads with retries, calls Kilosort, packages and uploads results |
| `kilosort2_simplified.py` | ~435 | `RunKilosort` class: multi-attempt sorting with fallback params, auto-curation, figure generation |
| `kilosort2_params.py` | 46 | Default Kilosort2 parameters, MATLAB paths, filter settings |
| `utils.py` | ~396 | Analysis utilities: STTC, population firing rate, sparse rasters, Phy file reader |
| `acqm.py` | — | Auto-curation quality metrics computation |
| `figures.py` | — | Plotly HTML figure generation for pipeline outputs |

### Services/Spike_Sorting_Listener/src/

| File | Lines | Description |
|---|---|---|
| `mqtt_listener.py` | ~520 | `JobMessage` class: MQTT handler, metadata parsing, job routing (MaxTwo vs standard) |
| `splitter_fanout.py` | ~433 | MaxTwo orchestration: splitter job creation, watcher thread, fan-out to per-well sorter jobs |
| `k8s_kilosort2.py` | ~207 | `Kube` class: builds K8s Job specs with resources, affinity, and init containers |
| `job_utils.py` | 47 | `mk_job_name()` helper and S3 bucket constants |
| `sorting_job_info.json` | 46 | Template: image tag, resources, GPU, whitelist nodes |
| `job_type_table.json` | 9 | Image → human-readable name mapping |

### Services/MaxWell_Dashboard/src/

| File | Lines | Description |
|---|---|---|
| `app.py` | 47 | Dash application entry point with multi-page routing |
| `values.py` | 124 | All constants: MQTT topics, S3 paths, job defaults, parameter mappings |
| `utils.py` | 249 | S3 upload, MQTT publish, metadata parsing, K8s pod helpers |
| `pages/home.py` | 241 | Landing page with quick start guide and workflow overview |
| `pages/job_center.py` | 542 | Job configuration, parameter management, submission logic |
| `pages/status.py` | 105 | K8s pod status monitor with refresh button |
