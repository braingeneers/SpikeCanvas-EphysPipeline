---
name: repo-map-updater
description: Generates and updates the component and configuration map files that document the SpikeCanvas platform architecture. Run after structural changes or when other skills cannot find their maps. Not intended for use during normal operations.
---

# SpikeCanvas Repo Map Updater

You are acting as the **Repo Map Updater** for the SpikeCanvas platform. Your sole responsibility is generating and maintaining the two reference map files that document the platform's architecture for other skills.

---

## When to Run

This skill should be invoked:
- After structural changes to the codebase (new files, renamed modules, new services)
- After changing image tags, job configs, or S3 paths
- When explicitly asked by the user
- When another skill reports that the maps are missing or stale

---

## Strict Boundary Rules

### Files you may create or modify

You may only create or modify these two files:
- `COMPONENT_MAP.md` — located at `.agent/skills/repo-map-updater/COMPONENT_MAP.md`
- `CONFIG_MAP.md` — located at `.agent/skills/repo-map-updater/CONFIG_MAP.md`

You must not modify any source code, tests, configs, or other files.

### Read-only access to source

You may read any file in the repository to understand the structure. You must not modify any source file.

---

## Map Files

| File | Purpose | Audience |
|---|---|---|
| `COMPONENT_MAP.md` | Architecture overview: directory tree, file roles, data flow, service interactions | All skills — fast orientation |
| `CONFIG_MAP.md` | All tunable parameters: job configs, S3 paths, MQTT topics, resource specs, K8s settings | `pipeline-operator` and `pipeline-developer` — source of truth for config |

Both files are consumed by all other skills as their primary reference for what exists in the platform.

---

## Procedure

### Step 1: Read the source

**First-time generation (files do not exist):** Read the full repository to understand the complete structure. Focus on:
- Top-level directory layout (`Algorithms/`, `Services/`, `tests/`)
- Every source file and its purpose
- Configuration files (JSON, YAML, Python constants)
- Docker and Kubernetes manifests
- S3 path patterns used in code
- MQTT topics and message schemas

**Updating existing files:** Use `git log` and `git diff` to identify what changed since the maps were last updated. Only read the source files that were affected.

### Step 2: Generate or update in order

**1. `COMPONENT_MAP.md` first.**

Structure:
```markdown
# SpikeCanvas Component Map

## Directory Structure
(annotated file tree)

## Component Overview
(table: component → directory → purpose → key files)

## Data Flow
(mermaid diagram or ASCII art showing request flow)

## Service Interactions
(which components talk to which, via what protocol)

## File Reference
(every source file with one-line description)
```

**2. `CONFIG_MAP.md` second.**

Structure:
```markdown
# SpikeCanvas Configuration Map

## Image Tags
(table: location → file → current tag)

## Job Configuration
(full schema of sorting_job_info.json)

## Dashboard Job Defaults
(from values.py DEFAULT_JOBS)

## Kilosort Parameters
(from kilosort2_params.py)

## Auto-Curation Defaults
(from utils.py DEFAULT_PARAM_LIST)

## S3 Paths
(table: path pattern → purpose → used by)

## MQTT Topics
(table: topic → publisher → subscriber → message schema)

## K8s Resources
(table: job type → CPU → memory → disk → GPU → node whitelist)

## Environment Variables
(any env vars referenced in code)
```

### Step 3: Preserve existing style (updates only)

When updating existing files:
- Match formatting already in each file
- Do not reformat unchanged sections
- Add a "Last updated" timestamp at the top

### Step 4: Return a summary

Return a concise summary of what was generated or changed. State if any file was skipped and why.

---

## Key Invariants to Document

These must always appear in the maps:

- Image tags must stay aligned across 4 locations
- MaxTwo wells are **1-indexed**
- Primary bucket: `braingeneers` / Cache bucket: `braingeneersdev`
- Pipeline has 3-stage Kilosort retry with fallback parameters
- Splitter jobs do NOT use GPU or node whitelist
- `edp-` prefix for all pipeline job names
- K8s namespace: `braingeneers`
