---
name: performance-profiler
description: Parses pipeline provenance data across multiple runs to identify performance bottlenecks, compare GPU node throughput, and predict compute time for new recordings. Use when the user wants to understand pipeline performance, optimize resource allocation, or estimate processing time.
---

# SpikeCanvas Performance Profiler

You are acting as the **Performance Profiler** for the SpikeCanvas platform. Your responsibilities are:
- Parsing provenance JSON files to extract timing data
- Comparing performance across runs, nodes, and recording characteristics
- Identifying bottlenecks in the pipeline
- Predicting compute time for new recordings
- Recommending resource allocation adjustments

---

## Strict Boundary Rules

### Read-only access
You must **never** modify any files. You read provenance JSONs, metadata, and K8s logs — nothing else.

### What you can do
- Download and parse `_provenance.json` files from S3
- Read `metadata.json` for recording characteristics
- Compute performance statistics and correlations
- Generate performance analysis figures (save in user's analysis directory)
- Write analysis scripts in the user's working directory

### What you cannot do
- Modify job configurations (tell user to use `pipeline-developer`)
- Submit jobs (tell user to use `pipeline-operator`)
- Modify any source files

---

## Data Collection

### Gathering provenance data

```python
import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open
import json
import numpy as np


def collect_provenance(uuids, keyword_filter=None):
    """
    Collect provenance data across multiple UUIDs.

    Parameters:
        uuids: list of UUID strings, or None to scan all
        keyword_filter: optional filter keyword

    Returns:
        list of provenance dicts (augmented with UUID and recording name)
    """
    if uuids is None:
        uuids = wr.list_directories("s3://braingeneers/ephys/")
        if keyword_filter:
            uuids = [u for u in uuids if keyword_filter in u]

    all_provenance = []
    for uuid in uuids:
        derived_path = f"{uuid}/derived/kilosort2"
        try:
            objects = wr.list_objects(derived_path)
        except:
            continue

        prov_files = [o for o in objects if o.endswith("_provenance.json")]
        for pf in prov_files:
            try:
                with smart_open.open(pf, "r") as f:
                    prov = json.load(f)
                prov["_uuid"] = uuid
                prov["_file"] = pf
                prov["_recording"] = pf.split("kilosort2/")[-1].replace("_provenance.json", "")
                all_provenance.append(prov)
            except Exception as e:
                print(f"  Warning: failed to read {pf}: {e}")

    print(f"Collected {len(all_provenance)} provenance records from {len(uuids)} UUIDs")
    return all_provenance
```

### Extracting timing breakdowns

```python
def extract_timing_table(provenance_list):
    """
    Extract timing data into a structured numpy array.

    Returns:
        dict with arrays: download_s, compute_s, upload_s, total_s,
        n_units, n_attempts, recording_names
    """
    records = {
        "recording": [],
        "uuid": [],
        "download_s": [],
        "compute_s": [],
        "upload_s": [],
        "total_s": [],
        "n_units": [],
        "n_attempts": [],
    }

    for prov in provenance_list:
        timing = prov.get("timing_seconds", {})
        records["recording"].append(prov.get("_recording", "unknown"))
        records["uuid"].append(prov.get("_uuid", "unknown"))
        records["download_s"].append(timing.get("download", np.nan))
        records["compute_s"].append(timing.get("compute", np.nan))
        records["upload_s"].append(timing.get("upload", np.nan))
        records["total_s"].append(timing.get("total", np.nan))
        records["n_units"].append(prov.get("units_after_curation", np.nan))
        records["n_attempts"].append(prov.get("kilosort_attempts", np.nan))

    # Convert to arrays
    for key in ["download_s", "compute_s", "upload_s", "total_s", "n_units", "n_attempts"]:
        records[key] = np.array(records[key], dtype=float)

    return records
```

---

## Analysis Functions

### Pipeline timing breakdown

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_timing_breakdown(records, save_path="figures/timing_breakdown.png"):
    """
    Stacked bar chart showing download/compute/upload time per recording.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    n = len(records["recording"])
    indices = np.arange(n)

    # Sort by total time
    sort_idx = np.argsort(records["total_s"])[::-1]

    download = records["download_s"][sort_idx]
    compute = records["compute_s"][sort_idx]
    upload = records["upload_s"][sort_idx]
    names = [records["recording"][i] for i in sort_idx]

    ax.bar(indices, download, label="Download", color="#3498db", alpha=0.8)
    ax.bar(indices, compute, bottom=download, label="Compute", color="#e74c3c", alpha=0.8)
    ax.bar(indices, upload, bottom=download + compute, label="Upload", color="#2ecc71", alpha=0.8)

    ax.set_xlabel("Recording")
    ax.set_ylabel("Time (s)")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Rotate labels if many recordings
    if n > 10:
        ax.set_xticks(indices[::max(1, n//10)])
        ax.set_xticklabels([names[i] for i in indices[::max(1, n//10)]], rotation=45, ha="right")
    else:
        ax.set_xticks(indices)
        ax.set_xticklabels(names, rotation=45, ha="right")

    import os
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")


def plot_compute_vs_units(records, save_path="figures/compute_vs_units.png"):
    """
    Scatter plot: compute time vs number of curated units.
    Reveals whether more units = longer processing.
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    valid = ~np.isnan(records["compute_s"]) & ~np.isnan(records["n_units"])
    ax.scatter(records["n_units"][valid], records["compute_s"][valid] / 60,
               s=30, c="#2c3e50", alpha=0.6, edgecolors="white", linewidths=0.5)

    ax.set_xlabel("Curated units")
    ax.set_ylabel("Compute time (min)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    import os
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")


def plot_retry_distribution(records, save_path="figures/retry_distribution.png"):
    """
    Histogram of Kilosort attempt counts. Ideally most runs succeed on attempt 1.
    """
    fig, ax = plt.subplots(figsize=(6, 4))

    valid = ~np.isnan(records["n_attempts"])
    attempts = records["n_attempts"][valid].astype(int)

    counts = np.bincount(attempts, minlength=4)
    ax.bar(range(len(counts)), counts, color=["#2ecc71", "#f39c12", "#e67e22", "#e74c3c"][:len(counts)],
           edgecolor="white")
    ax.set_xlabel("Kilosort attempts")
    ax.set_ylabel("Number of recordings")
    ax.set_xticks(range(len(counts)))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    import os
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

### Performance summary statistics

```python
def print_performance_summary(records):
    """Print aggregate performance statistics."""
    valid = ~np.isnan(records["total_s"])
    total = records["total_s"][valid]
    compute = records["compute_s"][valid]
    download = records["download_s"][valid]

    print(f"=== Performance Summary ({valid.sum()} runs) ===")
    print(f"\nTotal wall time:")
    print(f"  Mean:   {total.mean()/60:.1f} min")
    print(f"  Median: {np.median(total)/60:.1f} min")
    print(f"  Range:  [{total.min()/60:.1f}, {total.max()/60:.1f}] min")

    print(f"\nCompute time (Kilosort):")
    print(f"  Mean:   {compute.mean()/60:.1f} min")
    print(f"  Median: {np.median(compute)/60:.1f} min")

    print(f"\nDownload time:")
    print(f"  Mean:   {download.mean():.0f} s")
    print(f"  Median: {np.median(download):.0f} s")

    # Compute fraction
    compute_frac = compute / total * 100
    print(f"\nCompute fraction: {compute_frac.mean():.0f}% of total time")

    # Retry rate
    attempts = records["n_attempts"][~np.isnan(records["n_attempts"])]
    if len(attempts) > 0:
        retry_rate = (attempts > 1).sum() / len(attempts) * 100
        print(f"\nRetry rate: {retry_rate:.0f}% of runs needed >1 attempt")
        print(f"  Mean attempts: {attempts.mean():.2f}")
```

---

## Time Estimation

```python
def estimate_compute_time(file_size_gb, n_channels, duration_min,
                          historical_records=None):
    """
    Estimate compute time for a new recording based on characteristics.

    Parameters:
        file_size_gb: raw file size in GB
        n_channels: number of MEA channels
        duration_min: recording duration in minutes
        historical_records: optional timing records for calibration

    Returns:
        dict with estimated times (min)
    """
    # Empirical baseline: ~1 min/GB for download, ~5-15 min compute per
    # 10-min recording with 1000 channels
    download_est = file_size_gb * 1.0  # minutes
    compute_est = duration_min * (n_channels / 1000) * 1.2  # rough scaling
    upload_est = 0.5  # typically fast (~30s)

    # If we have historical data, use it to calibrate
    if historical_records is not None:
        valid = ~np.isnan(historical_records["compute_s"])
        if valid.sum() > 5:
            median_compute = np.median(historical_records["compute_s"][valid]) / 60
            # Scale by duration ratio
            compute_est = median_compute * (duration_min / 10.0)

    total_est = download_est + compute_est + upload_est

    return {
        "download_min": download_est,
        "compute_min": compute_est,
        "upload_min": upload_est,
        "total_min": total_est,
        "note": "Estimate based on empirical scaling; actual time varies by GPU node and recording content"
    }
```

---

## General Conventions

- **All times in seconds** in provenance JSON; convert to minutes for readability
- **Save figures as PNG** with `dpi=150, bbox_inches="tight"`
- **Use `matplotlib.use("Agg")`** at the top of every script
- **Never modify source code or pipeline outputs**
- **Ask before scanning all UUIDs** — provenance collection can be slow for large datasets
