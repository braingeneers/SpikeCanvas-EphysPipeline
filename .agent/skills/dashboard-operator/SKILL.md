---
name: dashboard-operator
description: Uses and modifies the SpikeCanvas web dashboard. Handles page layout, callback logic, job submission UI, status monitoring, and analytics visualization. Use when the user wants to update the dashboard, add UI features, or troubleshoot dashboard issues.
---

# SpikeCanvas Dashboard Operator

You are acting as the **Dashboard Operator** for the SpikeCanvas web interface. Your responsibilities are:
- Understanding and modifying the Dash-based multi-page application
- Adding new UI components, pages, or callback interactions
- Configuring job types, parameters, and submission workflows
- Troubleshooting dashboard display and callback issues

---

## Strict Boundary Rules

### Files you control (read/write)
- `Services/MaxWell_Dashboard/src/app.py` — Application entry point
- `Services/MaxWell_Dashboard/src/pages/` — Page modules (one file per page)
- `Services/MaxWell_Dashboard/src/utils.py` — Shared utility functions
- `Services/MaxWell_Dashboard/src/values.py` — Configuration constants and job defaults
- `Services/MaxWell_Dashboard/src/assets/` — Static CSS/JS/images

### Files you must not modify
- Pipeline source code (`Algorithms/ephys_pipeline/src/`)
- Listener source code (`Services/Spike_Sorting_Listener/src/`)
- Any production infrastructure files

If a task requires changes outside the dashboard directory, tell the user and suggest the `pipeline-developer` skill.

---

## Architecture

### Application structure

SpikeCanvas is a **Dash multi-page application** using `dash-bootstrap-components`:

```
Services/MaxWell_Dashboard/src/
├── app.py                  # Entry point; dash.Dash() with pages
├── values.py               # Shared constants, job configs, S3 paths
├── utils.py                # Helpers: S3 upload, MQTT publish, metadata parsing
├── pages/
│   ├── home.py             # Landing page with quick start guide
│   ├── job_center.py       # Job configuration and submission
│   ├── status.py           # K8s job status monitor
│   ├── analytics.py        # Data visualization (if present)
│   └── __init__.py
├── assets/                 # Static files served by Dash
└── start_dashboard.sh      # Shell script to launch the app
```

Each page uses `dash.register_page(__name__)` and exports a `layout` variable.

### Key dependencies

| Package | Purpose |
|---|---|
| `dash` | Core web framework |
| `dash-bootstrap-components` | Bootstrap-based layout components |
| `braingeneers.utils.s3wrangler` | S3 listing and object access |
| `braingeneers.utils.smart_open_braingeneers` | S3 file read/write |
| `braingeneers.iot.messaging` | MQTT message broker |
| `kubernetes` | K8s API client for status page |

### JWT Monkey-Patch

The dashboard applies a monkey-patch to `messaging.MessageBroker.jwt_service_account_token` to prevent shadows database access during MQTT publishing. This patch is in `utils.py` and **must be preserved** — removing it will cause authentication failures.

---

## Pages Deep-Dive

### Home Page (`pages/home.py`)

- Registered at path `/`
- Static layout: Quick start guide, module descriptions, processing workflow, tips
- No callbacks — purely informational

### Job Center (`pages/job_center.py`)

The primary interactive page. Layout components:

| Component | ID | Purpose |
|---|---|---|
| UUID dropdown | `dropdown` | Select dataset from S3 listing |
| Keyword filter | `textarea_filter_uuid` | Filter UUIDs by text search |
| Metadata display | `textarea_metadata` | Show parsed metadata.json |
| Batch mode | `batch_job` | "Batch Process" or "Clear All" radio |
| Recording checklist | `checklist_recs` | Select individual recordings |
| Job type checklist | `select_jobs` | Choose processing pipeline(s) |
| Parameter fields | `set_parameter` | Dynamic parameter inputs per job type |
| Parameter table | `parameter_table` | Track chosen parameter files |
| Job table | `job_table` | DataTable of configured jobs |
| Start button | `job_start_btn` | Submit all jobs in table |

**Callback chain for job submission:**
1. `drop_down()` — Populates UUID dropdown from S3
2. `display_recordings()` — Lists recordings for selected UUID
3. `show_parameters_to_job()` — Shows parameter fields for selected job type
4. `update_job_table_recs()` — Adds jobs to the table
5. `save_and_start_jobs()` — Writes CSV to S3 → publishes MQTT message

**Job types (from `values.py`):**

| Index | Job | Image | GPU |
|---|---|---|---|
| 0 | Ephys Pipeline | `braingeneers/ephys_pipeline:v0.75` | 1 |
| 2 | Auto-Curation | `surygeng/qm_curation:v0.2` | 0 |
| 3 | Visualization | `surygeng/visualization:v0.1` | 0 |
| 4 | Functional Connectivity | `surygeng/connectivity:v0.1` | 0 |
| 5 | LFP Subbands | `surygeng/local_field_potential:v0.1` | 0 |

Note: Index 1 is not used (gap in the numbering).

### Status Page (`pages/status.py`)

- Queries K8s API (`client.CoreV1Api().list_namespaced_pod`) on refresh
- Filters pods by prefix `edp-` (from `JOB_PREFIX` in values.py)
- Displays: status, job type, data path, parameter path, start/end times
- Uses `IMG_JOB_LOOPUP` dict to resolve image names to human-readable labels

---

## Configuration Constants (`values.py`)

| Constant | Value | Purpose |
|---|---|---|
| `TOPIC` | `"service/csv_job"` | MQTT topic for job submission |
| `TABLE_HEADERS` | 12 fields | CSV and DataTable column schema |
| `SERVICE_BUCKET` | `s3://braingeneers/services/mqtt_job_listener/csvs` | CSV upload location |
| `PARAMETER_BUCKET` | `s3://braingeneers/services/mqtt_job_listener/params` | S3 parameter file store |
| `DEFAULT_BUCKET` | `s3://braingeneers/ephys/` | Root path for UUID listing |
| `JOB_PREFIX` | `"edp-"` | K8s pod name prefix filter |
| `NAMESPACE` | `"braingeneers"` | K8s namespace |
| `FINISH_FLAGS` | `["Succeeded", "Failed", "Unknown"]` | Terminal pod states |
| `DEFAULT_JOBS` | dict | Default resource requests per job type |
| `JOB_PARAMETERS` | dict | Parameter fields shown in UI per job type |
| `CONVERT_TO_READABLE` / `CONVERT_TO_JSON` | dicts | Bidirectional key name mapping |
| `IMG_JOB_LOOPUP` | dict | Image → human-readable job name mapping |

---

## MQTT & CSV Job Protocol

The dashboard submits jobs through a CSV-based protocol:

1. **Build job table**: User selects recordings + job types → rows populate `job_table`
2. **Export to S3**: `utils.upload_to_s3()` writes rows as CSV to `SERVICE_BUCKET`
3. **MQTT trigger**: `utils.mqtt_start_job()` publishes to `services/csv_job`:
   ```json
   {
     "csv": "s3://braingeneers/services/mqtt_job_listener/csvs/20250523120000.csv",
     "update": {"Start": [1, 2, 3]},
     "refresh": false
   }
   ```
4. **Listener picks up**: Downloads CSV, extracts job rows, creates K8s jobs

CSV columns: `index`, `status`, `uuid`, `experiment`, `image`, `args`, `params`, `cpu_request`, `memory_request`, `disk_request`, `GPU`, `next_job`

---

## Adding a New Job Type

To add a new analysis job (e.g., "Burst Detection"):

1. **`values.py`**: Add entry to `DEFAULT_JOBS["chained"]` with:
   - `image`: Docker image for the analysis
   - `args`: Container entrypoint command
   - Resource requests (`cpu_request`, `memory_request`, `disk_request`, `GPU`)
   - `params_label`: S3 subdirectory for parameter files
   - `next_job`: `"None"` or index of chained follow-up job

2. **`values.py`**: Add entry to `JOB_PARAMETERS` with the parameter field labels

3. **`values.py`**: Add entry to `IMG_JOB_LOOPUP` mapping image → display name

4. **`values.py`**: Add entries to `CONVERT_TO_READABLE` and `CONVERT_TO_JSON` for any new parameter keys

5. **`job_center.py`**: Add checklist option in `select_jobs` with the new index

6. **`job_type_table.json`** (listener side): Add image → name mapping so listener recognizes the job type

---

## Running Locally

```bash
# From the dashboard src directory
cd Services/MaxWell_Dashboard/src

# Option 1: Direct
python app.py
# Dashboard runs at http://127.0.0.1:8050

# Option 2: Shell script
./start_dashboard.sh
```

**Required environment variables:**
- AWS/S3 credentials (for `braingeneers` bucket access)
- MQTT broker connection (for job submission)
- K8s kubeconfig (for status page)

---

## Known Issues

| Issue | Details |
|---|---|
| Typo in `IMG_JOB_LOOPUP` | Should be `IMG_JOB_LOOKUP` — functional but confusing |
| Global `out_str` in `utils.py` | `format_dict_textarea()` uses `global out_str` — not thread-safe |
| No index 1 | `DEFAULT_JOBS["chained"]` jumps from 0 to 2 — gap from removed standalone KS2 option |
| Bare `except:` on status page | `except:` clause on K8s config reload should catch specific exceptions |
| `sys.path.append('..')` | `job_center.py` uses path hack; could be replaced with proper package imports |

---

## Code Style

- **Framework**: Dash with `dbc` (Bootstrap) components
- **Callbacks**: Use `@callback` decorator with explicit `Input`, `Output`, `State`
- **Context**: Use `ctx.triggered_id` to distinguish multiple triggers
- **IDs**: All component IDs must be unique strings (or pattern-matching dicts for dynamic components)
- **Layout**: Use `dbc.Container`, `dbc.Row`, `dbc.Col`, `dbc.Card` for consistent layout
- **Comments**: All code must be properly commented (per workspace rule)
