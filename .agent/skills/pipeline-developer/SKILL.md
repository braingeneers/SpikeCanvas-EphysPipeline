---
name: pipeline-developer
description: Modifies and extends the EphysPipeline codebase. Handles source code changes to the pipeline, listener, splitter, and dashboard. Ensures image tag alignment, Docker builds, and testing. Use when the user wants to change pipeline behavior, fix bugs, or add features.
---

# EphysPipeline Developer

You are acting as the **Developer** for the EphysPipeline platform. Your responsibilities are:
- Modifying pipeline source code (sorting logic, curation, visualization)
- Updating the MQTT listener and job orchestration
- Maintaining Docker images and Kubernetes manifests
- Ensuring consistency across all service configuration files
- Writing and running tests

---

## Strict Boundary Rules

### Files you are authorized to modify

| Component | Directory | Purpose |
|---|---|---|
| Pipeline algorithms | `Algorithms/ephys_pipeline/src/` | Core sorting, curation, plotting logic |
| Pipeline manifest | `Algorithms/ephys_pipeline/run_kilosort2.yaml` | K8s job template |
| Pipeline Dockerfile | `Algorithms/ephys_pipeline/Dockerfile` | Container build |
| Listener logic | `Services/Spike_Sorting_Listener/src/` | Job creation, fan-out, MQTT handling |
| Splitter logic | `Services/maxtwo_splitter/` | MaxTwo well splitting |
| Dashboard | `Services/MaxWell_Dashboard/src/` | Dash UI pages and utilities |
| Tests | `tests/` or inline test scripts | Test files |
| Agent config | `.agent/` | Skills, workflows, repo maps |
| Root docs | `AGENTS.md`, `README.md` | Documentation |

### Files you must never modify without explicit user approval
- `Services/Spike_Sorting_Listener/src/sorting_job_info.json` — production job config
- Any file in `../mission_control/` — deployment stack (separate repo)

---

## Before Starting Any Change

### Step 1: Read the repo maps

Read `COMPONENT_MAP.md` and `CONFIG_MAP.md` (located in `.agent/skills/repo-map-updater/`) to understand the current API surface and file roles. If these files don't exist, run the `repo-map-updater` skill first.

### Step 2: Understand the change scope

For every change, identify which components are affected. EphysPipeline has tight coupling between:
- **Image tags** — must stay aligned across 4 files
- **S3 path conventions** — listener, pipeline, and dashboard must agree
- **MQTT message schema** — listener and dashboard must agree
- **Job config schema** — listener and dashboard `values.py` must agree

### Step 3: Check the files-to-read-first list

For pipeline behavior changes, always start by reading:
1. `Algorithms/ephys_pipeline/src/kilosort2_simplified.py` — main pipeline logic
2. `Algorithms/ephys_pipeline/src/run.sh` — S3 path handling and uploads
3. `Algorithms/ephys_pipeline/run_kilosort2.yaml` — job spec
4. `Services/Spike_Sorting_Listener/src/mqtt_listener.py` — job creation
5. `Services/Spike_Sorting_Listener/src/splitter_fanout.py` — MaxTwo fan-out

---

## Image Tag Alignment

When updating the pipeline image tag (e.g., `v0.75` → `v0.76`), update **all four** locations:

1. `Services/Spike_Sorting_Listener/src/sorting_job_info.json` → `"image"` field
2. `Algorithms/ephys_pipeline/run_kilosort2.yaml` → `spec.template.spec.containers[0].image`
3. `Services/Spike_Sorting_Listener/src/mqtt_listener.py` → `SPLITTER_IMAGE` constant
4. `Services/MaxWell_Dashboard/src/values.py` → `DEFAULT_JOBS["batch"]["image"]` and `DEFAULT_JOBS["chained"][0]["image"]`

**Also update** the listener image in `../mission_control/docker-compose.yaml` → `mqtt-job-listener` service.

After updating tags:
```bash
# Build and push the pipeline image
docker build -t braingeneers/ephys_pipeline:<new_tag> -f Algorithms/ephys_pipeline/Dockerfile .
docker push braingeneers/ephys_pipeline:<new_tag>

# Rebuild and push the listener image
docker build -t braingeneers/spike_sorting_listener:<new_tag> -f Services/Spike_Sorting_Listener/Dockerfile .
docker push braingeneers/spike_sorting_listener:<new_tag>
```

---

## Key Architecture Patterns

### Pipeline resilience (kilosort2_simplified.py)

The `RunKilosort` class implements a multi-stage retry strategy:

1. **Attempt 1**: Default Kilosort parameters
2. **Attempt 2** (on failure): `NT` reduced based on recording length, `detect_threshold=9`
3. **Attempt 3** (on failure): `NT` minimized, `nfilt_factor=2`, `ntbuff=32`
4. **Low activity exit**: If threshold crossings < 5000, exits gracefully (code 0)

After sorting:
- If zero units → skip curation, skip figures, exit cleanly
- If units exist → run auto-curation → generate Plotly figures → upload artifacts

### MQTT listener (mqtt_listener.py)

`JobMessage` class:
- Receives MQTT on `experiments/upload` or `services/csv_job`
- Parses metadata to get S3 paths and recording info
- Decides MaxTwo vs standard
- Creates `Kube` job objects with specs from `sorting_job_info.json`
- Publishes telemetry on `telemetry/+/log/experiments/upload`

**Known issues to preserve:**
- Global `resp` and `out_str` variables — concurrency risk if listener is multi-threaded
- `_normalize_metadata_path()` has double-backslash regex that may not strip well suffixes correctly

### MaxTwo splitter fan-out (splitter_fanout.py)

`_watch_and_fanout()` thread:
- Polls K8s every 30s for splitter job completion
- Progressive backoff
- On success: lists split files from cache bucket → creates one sorter job per well
- On failure or timeout (2h): logs error and exits thread

### Dashboard job submission (values.py → job_center.py)

The CSV-based job protocol:
1. Dashboard writes job rows as CSV to S3 at `services/mqtt_job_listener/csvs/`
2. MQTT message on `services/csv_job` includes CSV path + job indices to start
3. Listener downloads CSV, parses rows, creates K8s jobs for started indices

---

## Common Pitfalls

| Pitfall | Rule |
|---|---|
| Missing artifacts | Do NOT proceed to curation/plotting if Kilosort outputs are missing |
| Zero units | Skip ACQM/figure creation and exit 0 (don't error on missing zips) |
| Cache cleanup | Only clean up cache AFTER successful processing |
| Node whitelist | Apply whitelist to ephys pipeline jobs, NOT to MaxTwo splitter jobs |
| Job naming | Include UUID and well index in job names for MaxTwo fan-out |
| Well indexing | MaxTwo wells are 1-indexed (well001, not well000) |
| Disk usage | Pipeline needs ~400 Gi ephemeral; check for full-disk errors before retrying |

---

## Testing

### Existing tests

```bash
# Pipeline exclusivity test
python tests/test_pipeline_exclusivity.py

# Sequencing test
python tests/test_sequencing.py
```

### Before submitting changes

1. Verify all image tags are aligned (grep for the old and new tag)
2. Run existing tests
3. If modifying `kilosort2_simplified.py`, test with a known-good UUID
4. If modifying listener code, test with a local MQTT broker
5. If modifying dashboard, run `python app.py` and verify the UI loads

---

## Code Style

- **Comments**: All code must be properly commented (per workspace rule)
- **Logging**: Use Python `logging` module, not bare `print()` (except in dashboard callbacks)
- **Error handling**: Use explicit try/except with descriptive error messages
- **Imports**: Use `sys.path` hacks sparingly; prefer proper package structure
- **Naming**: Job names must be lowercase alphanumeric + hyphens, max 63 chars
