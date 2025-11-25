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
  - Spike Sorting (Kilosort2)
  - Auto-Curation (Quality Metrics)
  - Visualization
  - Functional Connectivity
  - Local Field Potential Subbands

## 3. Parameter Settings

### Setting Parameters
- **Set new parameters**: This section allows you to set parameters for the selected job. Input the parameter file name and values in the text areas provided.

### Loading Parameter Files
- **Select a job to load parameter file**: Choose a job to load the corresponding parameter file. The parameters will display in the text area.

### Current Parameter Setting
- **Parameter Table**: View and manage the current parameter settings in a table. You can add or remove parameter files as needed.

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

This manual provides a detailed guide to using the Job Center Webpage. Follow the instructions in each section to efficiently manage and execute your data processing jobs.
