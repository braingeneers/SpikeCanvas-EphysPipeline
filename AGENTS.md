# AGENTS.md — EphysPipeline repo guidance

This file captures stable repo structure, workflow expectations, and operational preferences distilled from ongoing work. It is intended for future agents working in this repo.

## Repo purpose and structure (high level)
- **Primary spike-sorting workflow** is the **Ephys Pipeline** under `Algorithms/ephys_pipeline/`.
- **Maxwell dashboard** web app lives under `Services/MaxWell_Dashboard/`.
- **Job orchestration** for spike sorting lives under `Services/Spike_Sorting_Listener/` (MQTT listener + job creation). Kubernetes manifests for pipeline jobs live alongside algorithms (e.g., `Algorithms/ephys_pipeline/run_kilosort2.yaml`).
- **Mission control deployment** lives in `../mission_control/` and manages the shared Docker Compose stack (dashboard, listeners, and related services). Update image tags there to roll out new versions.
- **Listener image dependency**: when changing spike-sorting image tags or job templates, rebuild/push `braingeneers/spike_sorting_listener` and update `mqtt-job-listener` in `../mission_control/docker-compose.yaml` so new jobs pick up the updated defaults.
- **MaxTwo splitting** (Maxwell 6/24‑well) is handled by `Services/maxtwo_splitter/` (separate from the pipeline).
- **Legacy**: `../Kilosort_docker` is deprecated; Ephys Pipeline is the single source of truth for spike sorting.

## Operational preferences (owner intent)
- **Single source of truth**: Ephys Pipeline is the primary spike sorter. Remove/avoid standalone Kilosort options in UI.
- **Consistency in image tags**: keep pipeline image tags aligned across services (listener, dashboard, job templates).
- **Clear job naming**: include **UUID** and **well index** in job/pod names for MaxTwo fanout (wells are 1‑indexed).
- **MaxTwo cache usage**: MaxTwo uses **braingeneersdev** cache for split files; derived outputs go to **braingeneers**.
- **Failure behavior**: pipeline should exit cleanly on failure and not try to upload missing artifacts.

## Data flow and S3 layout
- Raw: `s3://braingeneers/<uuid>/original/data/...`
- MaxTwo cache (split outputs): `s3://braingeneersdev/cache/ephys/<uuid>/original/data/*_wellNNN.raw.h5` (1‑indexed wells)
- Derived outputs: `s3://braingeneers/<uuid>/derived/kilosort2/`
- Pipeline output artifacts per recording:
  - `*_phy.zip` (Kilosort/Phy outputs)
  - `*_acqm.zip` (auto‑curation metrics)
  - `*_figure.zip` (plots/HTML summaries)

## MaxTwo (Maxwell 6‑well / 24‑well)
- **Splitter runs first** and should emit exactly 6 or 24 well files (1‑indexed `well001..`).
- **Fanout** should create one pipeline job per well; **non‑MaxTwo** datasets run a single pipeline job.
- The pipeline code should gracefully handle **multiple recording groups** in Maxwell H5 files.

## GPU scheduling and MATLAB stability
- **MATLAB/Kilosort segfaults** have occurred on some nodes.
- **Preferred mitigation**: apply a **node whitelist** for Ephys Pipeline jobs (not for splitter). Use the whitelist from the historical working tag (`v1.0-publication`) unless told otherwise.
- **Do not** apply the whitelist to the MaxTwo splitter (Python‑only workload).

## Image/versioning guidance
- Ephys Pipeline container image should be pushed to: `braingeneers/ephys_pipeline:<tag>`.
- When updating tags, ensure **all runtime references** are updated (listener job config, dashboard, manifests).
- Use the repo-root `Makefile` as the primary interface for image work. Prefer `make ephys-build TAG=<tag>`, `make ephys-push TAG=<tag>`, `make listener-build TAG=<tag>`, `make listener-push TAG=<tag>`, `make dashboard-build TAG=<tag>`, and `make dashboard-push TAG=<tag>` over raw `docker build` / `docker push` commands.
- Keep the Ephys Pipeline, Spike Sorting Listener, and MaxWell Dashboard image tags aligned unless there is a deliberate reason not to.

## Release/update workflow
- For an Ephys Pipeline release, first bump the pipeline tag in:
  `Algorithms/ephys_pipeline/run_kilosort2.yaml`,
  `Services/Spike_Sorting_Listener/src/sorting_job_info.json`,
  `Services/Spike_Sorting_Listener/src/job_type_table.json`,
  `Services/job_scanner/src/job_type_table.json`,
  `Services/MaxWell_Dashboard/src/values.py`,
  and `Services/MaxWell_Dashboard/src/k8s_kilosort2.py`.
- Build images from the repo root with `make release-build TAG=<tag>` or the narrower per-service targets if only one image changed.
- Push images from the repo root with `make release-push TAG=<tag>` after the build succeeds.
- After pushing, update `../mission_control/docker-compose.yaml` so `mqtt-job-listener` and `maxwell-dashboard` point at the new listener/dashboard tags, then validate mission control from that repo with its `make compose-validate` target before committing.
- Commit and push `EphysPipeline` and `../mission_control` separately so the image/tag change history stays clear.

## Dashboard expectations
- **Remove**/avoid the standalone “Spike Sorting (Kilosort2)” option in the dashboard. The Ephys Pipeline should be the visible entry point.
- Keep user‑facing labels aligned with actual job image names to reduce confusion.

## Common pitfalls to avoid
- Do not proceed to curation/plotting if Kilosort outputs are missing.
- If **zero units** remain after QC, skip ACQM/figure creation and **exit successfully** (do not error on missing zips).
- Ensure cache cleanup only happens after successful processing (avoid deleting cache on failure).

## Files to check first when changing pipeline behavior
- `Algorithms/ephys_pipeline/src/kilosort2_simplified.py` (main pipeline logic)
- `Algorithms/ephys_pipeline/src/run.sh` (S3 path handling and uploads)
- `Algorithms/ephys_pipeline/run_kilosort2.yaml` (job spec)
- `Services/Spike_Sorting_Listener/src/*` (job creation, fanout, image tags)
- `Services/MaxWell_Dashboard/src/*` (UI options, job params)
