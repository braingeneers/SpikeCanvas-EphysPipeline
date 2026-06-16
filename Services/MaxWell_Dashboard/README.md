# SpikeCanvas - Electrophysiology Data Processing & Analysis Platform

**SpikeCanvas** is a comprehensive web-based dashboard for neural data processing, spike sorting, quality control, and advanced analytics. This platform supports multiple electrophysiology recording formats and provides an intuitive interface for managing complex data processing workflows.

## Overview
SpikeCanvas provides a complete suite of tools for electrophysiology data analysis, from raw neural recordings to publication-ready visualizations. The platform includes automated spike sorting, quality control, connectivity analysis, and interactive data exploration capabilities.

## Main Sections
1. [Dataset Selection](#1-dataset-selection)
2. [Job Selection](#2-job-selection)
3. [Parameter Settings](#3-parameter-settings)
4. [Job Management](#4-job-management)

## 1. Dataset Selection

### Dropdown
- **Dataset (UUID)**: Use the dropdown menu to select a dataset by its UUID. The dropdown will populate with available datasets.

### Filter UUID by Keyword
- **Filter UUID by Keyword**: Enter keywords in the text area to filter the list of datasets. The filtered datasets will appear in the dropdown.

### Metadata Display
- **Metadata**: After selecting a dataset, its metadata will display in the read-only text area below the dataset selection section.

## 2. Job Selection

### Batch Job Options
- **Batch Process with Standard Pipeline**: Select this option to add a batch job with a standard pipeline.
- **Clear All Selected**: Select this option to reset and clear all selected jobs and recordings.

### Recording Selection
- **Recording**: Select recordings from the list. Options include:
  - **Select All**: Select all available recordings.
  - **Reset**: Clear all selected recordings.

### Job Checklist
- **Select Job**: Choose from the following job options:
  - Ephys Pipeline (Kilosort2, Auto-Curation, Visualization)
  - Auto-Curation (Quality Metrics)
  - Visualization
  - Functional Connectivity
  - Local Field Potential Subbands

## 3. Parameter Settings

### Customizing Default Values
- **Customize default values**: Use this section when you want normal defaults plus a few custom overrides. Select exactly one job, give the custom values a name, fill only the values you want to override, and click **Save Custom Values**.
- Blank fields are not saved. The pipeline uses its defaults for any value you leave blank.

For **Ephys Pipeline (Kilosort2, Auto-Curation, Visualization)**, most custom values control the auto-curation step that runs after Kilosort2. Advanced Kilosort values are also available for targeted sorter workarounds. The dashboard saves only the values you filled in under:

```text
s3://braingeneers/services/mqtt_job_listener/params/pipeline/params_<saved-name>.json
```

The Ephys Pipeline reads the JSON keys below:

| Dashboard field | JSON key | Effect |
| --- | --- | --- |
| Minimum SNR (rms) | `min_snr` | Exclude units with signal-to-noise ratio below this value |
| Minimum Firing Rate (Hz) | `min_fr` | Exclude units with firing rate below this value |
| Maximum ISI Violation Rate (fraction) | `max_isi_viol` | Exclude units with ISI violation rate above this value; enter as a fraction, so `0.5` means 50% |
| Kilosort Detection Threshold | `detect_threshold` | Advanced Kilosort2 spike-detection threshold applied before sorting |

For example, to exclude putative neuronal units with ISI violation rates above `0.5`, firing rates below `0.1` Hz, and SNR below your chosen threshold, select **Ephys Pipeline**, enter a saved custom values name such as `kd_fusion_qc`, enter:

```json
{
  "min_snr": 3,
  "min_fr": 0.1,
  "max_isi_viol": 0.5
}
```

through the dashboard fields, and click **Save Custom Values**. The dashboard will create `params_kd_fusion_qc.json` in the `pipeline` parameter folder. The saved name is the suffix used after `params_`; for example, entering `kd_fusion_qc` creates `params_kd_fusion_qc.json`.

Leave **Kilosort Detection Threshold** blank for normal pipeline behavior. For targeted MaxTwo wells that hit Kilosort2 template-optimization index errors, raising this value can reduce low-confidence detections enough for the job to finish or cleanly mark a low-activity well. In local testing on `2026-03-12-e-KD_fusion_and_control`, well004 completed with `detect_threshold=7`, while well005 cleanly exited through the low-activity marker path with `detect_threshold=7.5`.

### Using Saved Custom Values
- **Use saved custom values**: Use this section when you want to reuse saved values or choose a default file. Selecting a file previews its JSON contents in the textbox.
- The preview textbox is read-only. It does not edit, override, or save values. To change values, save a new set of custom values.

### Current Parameter Setting
- **Parameter Table**: View and manage the current parameter settings in a table. You can add or remove parameter files as needed.

### Applying Parameters to a Job
1. Select the dataset UUID and recording(s).
2. Select **Ephys Pipeline (Kilosort2, Auto-Curation, Visualization)**.
3. Either save custom values with **Save Custom Values**, or choose an existing entry under **Use saved custom values**.
4. Click **Use Selected Values**. Confirm that the table has `pipeline` in the job column and the selected saved values in the saved values column.
5. Click **Add to Job Table**. The job table row should show `pipeline/<parameter-file>` in the `params` column.
6. Click **Export and Start Job**.

Use the recording checklist and **Add to Job Table** path for custom Ephys Pipeline parameters. The **Batch Process with Standard Pipeline** shortcut creates standard pipeline rows directly and does not attach parameter-table selections.

For MaxTwo datasets, the listener starts one splitter job first and then fans out one Ephys Pipeline job per well. The selected `pipeline/<parameter-file>` setting is copied into the sorter template, so every well job receives the same parameter file.

If the `params` column is empty or points to a missing file, the Ephys Pipeline uses its built-in curation defaults: `min_snr=3`, `min_fr=0.1`, and `max_isi_viol=0.5`, and the default Kilosort detection threshold of `6`.

## 4. Job Management

### Add to Job Table
- **Add to Job Table**: After selecting jobs and parameters, click this button to add them to the job table.

### Export and Start Job
- **Export and Start Job**: When all jobs are configured, click this button to export the job settings and start the job.

### Job Table
- **Job Table**: View all added jobs in a table. You can manage job status, UUID, experiment details, and parameters. Rows can be deleted if necessary.

## Callback Functions
### Updating the Job Table
- The job table updates dynamically based on user input and selected options.

### Displaying Metadata
- Metadata for the selected dataset is displayed when a UUID is chosen from the dropdown.

### Managing Parameters
- Parameters can be set, saved, and loaded dynamically based on user selections and inputs.

## Troubleshooting
- Ensure all required fields are filled before adding jobs to the table.
- If metadata does not display, verify the dataset UUID and try again.
- Parameters should be set carefully to ensure jobs run correctly.
- For Ephys Pipeline jobs, verify the Status Monitor parameter path points at `.../params/pipeline/params_<file-name>.json`. If it does not, re-add the parameter file to the Parameter Table before adding the job row.

This manual provides a detailed guide to using the Job Center Webpage. Follow the instructions in each section to efficiently manage and execute your data processing jobs.
