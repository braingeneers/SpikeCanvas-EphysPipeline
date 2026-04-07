---
name: report-generator
description: Generates formatted sorting reports from completed pipeline outputs. Combines provenance data, quality metrics, and summary statistics into publication-ready markdown or HTML reports. Use when the user wants a summary of sorting results for a completed experiment.
---

# SpikeCanvas Report Generator

You are acting as the **Report Generator** for the SpikeCanvas platform. Your responsibilities are:
- Generating structured sorting reports from pipeline outputs
- Combining provenance, quality metrics, and summary statistics
- Creating publication-ready markdown reports
- Comparing results across recordings within an experiment

---

## Strict Boundary Rules

### File boundaries

Save all reports in a user-specified output directory (e.g., `./reports/`). Create it if it does not exist.

**You must not modify any source code, pipeline outputs, or S3 data.**

### Input sources

Reports are assembled from:
1. `_provenance.json` — Pipeline timing and attempt counts
2. `_phy.zip` — Spike sorting outputs (unit counts, firing rates, templates)
3. `_acqm.zip` — Quality metrics (SNR, ISI violations)
4. `metadata.json` — Experiment metadata (hardware, channels, sample rate)

---

## Report Generation

### Standard Sorting Report

```python
import numpy as np
import zipfile
import json
import os
from datetime import datetime


def generate_sorting_report(uuid, phy_zip_path, provenance_path=None,
                            metadata_path=None, output_dir="reports"):
    """
    Generate a markdown sorting report for a completed pipeline run.

    Parameters:
        uuid: experiment UUID
        phy_zip_path: path to the _phy.zip file
        provenance_path: optional path to _provenance.json
        metadata_path: optional path to metadata.json
        output_dir: directory to save the report

    Returns:
        str: path to the generated report
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load Phy data
    with zipfile.ZipFile(phy_zip_path, "r") as z:
        spike_times = np.load(z.open("spike_times.npy")).squeeze()
        spike_clusters = np.load(z.open("spike_clusters.npy")).squeeze()
        templates = np.load(z.open("templates.npy"))

        # Parse sampling rate
        fs = 20000.0
        if "params.py" in z.namelist():
            with z.open("params.py") as pf:
                for line in pf.read().decode().splitlines():
                    if "sample_rate" in line:
                        fs = float(line.split("=")[-1].strip())

    # Compute statistics
    cluster_ids = np.unique(spike_clusters)
    n_units = len(cluster_ids)
    n_spikes = len(spike_times)
    duration_sec = spike_times.max() / fs

    frs = []
    spike_counts = []
    for cid in cluster_ids:
        n = (spike_clusters == cid).sum()
        spike_counts.append(n)
        frs.append(n / duration_sec)
    frs = np.array(frs)
    spike_counts = np.array(spike_counts)

    # Load provenance if available
    provenance = None
    if provenance_path and os.path.exists(provenance_path):
        with open(provenance_path, "r") as f:
            provenance = json.load(f)

    # Load metadata if available
    metadata = None
    if metadata_path and os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

    # Build report
    rec_name = os.path.basename(phy_zip_path).replace("_phy.zip", "")
    lines = []

    lines.append(f"# Sorting Report — {rec_name}\n")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Curation outcome (most important — at the top)
    lines.append("## Curation Outcome\n")
    lines.append(f"- **Curated units**: {n_units}")
    lines.append(f"- **Total spikes**: {n_spikes:,}")
    lines.append(f"- **Mean firing rate**: {frs.mean():.2f} Hz")
    lines.append(f"- **Median firing rate**: {np.median(frs):.2f} Hz")
    lines.append(f"- **Median spikes/unit**: {int(np.median(spike_counts)):,}")
    lines.append(f"- **FR range**: [{frs.min():.2f}, {frs.max():.2f}] Hz\n")

    # Recording overview
    lines.append("## Recording Overview\n")
    lines.append(f"- **UUID**: `{uuid}`")
    lines.append(f"- **Recording**: `{rec_name}`")
    lines.append(f"- **Duration**: {duration_sec:.1f} s ({duration_sec/60:.1f} min)")
    lines.append(f"- **Channels**: {templates.shape[2]}")
    lines.append(f"- **Sample rate**: {fs:.0f} Hz")

    if metadata:
        notes = metadata.get("notes", "N/A")
        hw = "Unknown"
        # Try to extract hardware from experiments
        exps = metadata.get("ephys_experiments", {})
        if isinstance(exps, dict):
            for exp in exps.values():
                if isinstance(exp, dict):
                    hw = exp.get("hardware", "Unknown")
                    break
        elif isinstance(exps, list) and exps:
            hw = exps[0].get("hardware", "Unknown")
        lines.append(f"- **Hardware**: {hw}")
        lines.append(f"- **Notes**: {notes}")

    lines.append("")

    # Pipeline provenance
    if provenance:
        lines.append("## Pipeline Provenance\n")
        lines.append(f"- **Pipeline version**: `{provenance.get('pipeline_version', 'N/A')}`")

        timing = provenance.get("timing_seconds", {})
        if timing:
            lines.append(f"- **Download time**: {timing.get('download', 0):.0f} s")
            lines.append(f"- **Compute time**: {timing.get('compute', 0):.0f} s")
            lines.append(f"- **Upload time**: {timing.get('upload', 0):.0f} s")
            lines.append(f"- **Total wall time**: {timing.get('total', 0):.0f} s "
                         f"({timing.get('total', 0)/60:.1f} min)")

        attempts = provenance.get("kilosort_attempts", "N/A")
        lines.append(f"- **Kilosort attempts**: {attempts}")

        pre_curation = provenance.get("units_before_curation", "N/A")
        post_curation = provenance.get("units_after_curation", "N/A")
        if pre_curation != "N/A" and post_curation != "N/A":
            removed = pre_curation - post_curation
            lines.append(f"- **Pre-curation units**: {pre_curation}")
            lines.append(f"- **Post-curation units**: {post_curation} ({removed} removed)")

        curation_params = provenance.get("curation_params", {})
        if curation_params:
            lines.append(f"- **Curation thresholds**: SNR≥{curation_params.get('min_snr', '?')}, "
                         f"FR≥{curation_params.get('min_fr', '?')} Hz, "
                         f"ISI≤{curation_params.get('max_isi_viol', '?')}")
        lines.append("")

    # Unit quality distributions
    lines.append("## Unit Quality\n")
    lines.append("### Firing Rate Distribution\n")
    lines.append("| Statistic | Value |")
    lines.append("|---|---|")
    lines.append(f"| Mean | {frs.mean():.2f} Hz |")
    lines.append(f"| Median | {np.median(frs):.2f} Hz |")
    lines.append(f"| Std | {frs.std():.2f} Hz |")
    lines.append(f"| Min | {frs.min():.2f} Hz |")
    lines.append(f"| Max | {frs.max():.2f} Hz |")
    lines.append("")

    lines.append("### Spike Count Distribution\n")
    lines.append("| Statistic | Value |")
    lines.append("|---|---|")
    lines.append(f"| Mean | {spike_counts.mean():.0f} |")
    lines.append(f"| Median | {np.median(spike_counts):.0f} |")
    lines.append(f"| Min | {spike_counts.min()} |")
    lines.append(f"| Max | {spike_counts.max():,} |")
    lines.append(f"| Total | {spike_counts.sum():,} |")
    lines.append("")

    # Output files
    lines.append("## Output Files\n")
    lines.append(f"- `{rec_name}_phy.zip` — Kilosort/Phy sorting outputs")
    lines.append(f"- `{rec_name}_acqm.zip` — Auto-curation quality metrics")
    lines.append(f"- `{rec_name}_figure.zip` — Interactive HTML figures")
    lines.append(f"- `{rec_name}_provenance.json` — Pipeline timing metadata")
    lines.append("")

    # Write report
    report_text = "\n".join(lines)
    report_path = os.path.join(output_dir, f"{rec_name}_sorting_report.md")
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"Report saved: {report_path}")
    return report_path
```

### Batch Report (Multiple Recordings)

```python
def generate_batch_report(uuid, phy_zip_paths, provenance_paths=None,
                          output_dir="reports"):
    """
    Generate a summary report across multiple recordings in one UUID.

    Parameters:
        uuid: experiment UUID
        phy_zip_paths: list of paths to _phy.zip files
        provenance_paths: optional list of paths to _provenance.json files
        output_dir: directory to save the report
    """
    os.makedirs(output_dir, exist_ok=True)

    all_stats = []
    for i, phyzip in enumerate(phy_zip_paths):
        with zipfile.ZipFile(phyzip, "r") as z:
            st = np.load(z.open("spike_times.npy")).squeeze()
            sc = np.load(z.open("spike_clusters.npy")).squeeze()
            fs = 20000.0

        cids = np.unique(sc)
        dur = st.max() / fs
        frs = [(sc == c).sum() / dur for c in cids]
        rec_name = os.path.basename(phyzip).replace("_phy.zip", "")

        all_stats.append({
            "recording": rec_name,
            "units": len(cids),
            "spikes": len(st),
            "duration_min": dur / 60,
            "mean_fr": np.mean(frs),
            "median_fr": np.median(frs),
        })

    # Build summary table
    lines = []
    lines.append(f"# Batch Sorting Report — {uuid}\n")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Recordings**: {len(all_stats)}\n")

    lines.append("## Per-Recording Summary\n")
    lines.append("| Recording | Units | Spikes | Duration (min) | Mean FR (Hz) | Median FR (Hz) |")
    lines.append("|---|---|---|---|---|---|")

    for s in all_stats:
        lines.append(f"| {s['recording']} | {s['units']} | {s['spikes']:,} | "
                     f"{s['duration_min']:.1f} | {s['mean_fr']:.2f} | {s['median_fr']:.2f} |")

    # Aggregate
    total_units = sum(s["units"] for s in all_stats)
    total_spikes = sum(s["spikes"] for s in all_stats)
    lines.append(f"\n**Total units**: {total_units}")
    lines.append(f"**Total spikes**: {total_spikes:,}")

    report_text = "\n".join(lines)
    report_path = os.path.join(output_dir, f"{uuid}_batch_report.md")
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"Batch report saved: {report_path}")
    return report_path
```

---

## General Conventions

- **Reports are markdown** — easy to read, version-control, and convert to HTML/PDF
- **Curation outcome first** — the most important information goes at the top
- **Include units** — always specify Hz, ms, s, etc.
- **Never modify pipeline outputs** — reports are generated from read-only data
- **Save reports in the user's directory** — not inside `Algorithms/` or `Services/`
