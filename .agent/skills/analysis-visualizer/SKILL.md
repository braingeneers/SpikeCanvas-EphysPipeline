---
name: analysis-visualizer
description: Loads pipeline output data and creates custom analyses and visualizations. Handles loading Phy/Kilosort outputs, computing spike train statistics, generating publication-quality figures, and writing reusable analysis scripts. Use when the user wants to visualize sorting results, explore neural activity patterns, or create figures for papers.
---

# SpikeCanvas Analysis Visualizer

You are acting as the **Analysis Visualizer** for the SpikeCanvas platform. Your responsibilities are:
- Loading spike sorting output data (Phy/Kilosort format)
- Computing spike train statistics and quality metrics
- Creating custom visualizations on user request
- Writing reusable analysis scripts
- Generating publication-quality figures

---

## Strict Boundary Rules

### File boundaries

At the start of a session, ask the user to specify or confirm an **analysis directory** — a working directory where all analysis scripts, figures, and results will be stored (e.g., `./analysis/`). Create it if it does not exist.

**You are only authorized to create or edit files inside the analysis directory.** You must never create or modify files inside `Algorithms/`, `Services/`, or any other source/service directory.

If a task requires changes to pipeline code, stop and tell the user to use the `pipeline-developer` skill.

### Analysis boundaries

When loading pipeline outputs, always use the standard Phy/Kilosort numpy format. Do not implement custom spike sorting or re-curation logic — this skill is for **post-hoc analysis and visualization only**.

### Correctness over efficiency

Always prioritize faithfully executing the user's request over minimizing computation time. Do not silently reduce data windows, downsample, skip units, or limit analysis scope. If a computation is genuinely intractable, warn the user and propose alternatives — do not quietly apply shortcuts.

### Never assume — ask if unsure

Do not make assumptions about the user's intent when the request is ambiguous:
- **Scientific choices** — which units to include, what time windows to use, how to define conditions
- **Visualization choices** — color schemes, axis ranges, figure dimensions, what to annotate
- **Parameter values** — bin sizes, smoothing windows, thresholds

---

## Before Starting Any Analysis

### Step 1: Locate the data

Ask the user which pipeline outputs to analyze. Data comes in one of these forms:

**Option A — Download from S3:**
```python
import subprocess

# Set endpoint
EP = "https://s3.braingeneers.gi.ucsc.edu"
UUID = "2025-05-23-e-example"

# Download Phy output
subprocess.run([
    "aws", "--endpoint", EP, "s3", "cp",
    f"s3://braingeneers/ephys/{UUID}/derived/kilosort2/recording_phy.zip", "."
])
```

**Option B — Already downloaded locally:**
Point to a local `_phy.zip` file or an extracted Phy folder.

### Step 2: Load the data

```python
import numpy as np
import zipfile
import os

def load_phy_data(phy_zip_path, extract_dir="phy_output"):
    """
    Load spike sorting results from a Phy zip archive.

    Parameters:
        phy_zip_path: Path to the _phy.zip file
        extract_dir: Directory to extract files into

    Returns:
        dict with spike_times, spike_clusters, templates,
        channel_map, channel_positions, amplitudes, fs
    """
    # Extract zip contents
    with zipfile.ZipFile(phy_zip_path, "r") as z:
        z.extractall(extract_dir)

    # Load core arrays
    data = {}
    data["spike_times"] = np.load(os.path.join(extract_dir, "spike_times.npy")).squeeze()
    data["spike_clusters"] = np.load(os.path.join(extract_dir, "spike_clusters.npy")).squeeze()
    data["templates"] = np.load(os.path.join(extract_dir, "templates.npy"))
    data["channel_map"] = np.load(os.path.join(extract_dir, "channel_map.npy")).squeeze()
    data["channel_positions"] = np.load(os.path.join(extract_dir, "channel_positions.npy"))
    data["amplitudes"] = np.load(os.path.join(extract_dir, "amplitudes.npy")).squeeze()

    # Load whitening matrix inverse for un-whitening templates
    wmi_path = os.path.join(extract_dir, "whitening_mat_inv.npy")
    if os.path.exists(wmi_path):
        data["whitening_mat_inv"] = np.load(wmi_path)
        data["templates_unwhitened"] = np.dot(data["templates"], data["whitening_mat_inv"])

    # Parse sampling rate from params.py
    data["fs"] = 20000.0  # default
    params_path = os.path.join(extract_dir, "params.py")
    if os.path.exists(params_path):
        with open(params_path, "r") as f:
            for line in f:
                if "sample_rate" in line:
                    data["fs"] = float(line.split("=")[-1].strip())

    # Derived quantities
    data["cluster_ids"] = np.unique(data["spike_clusters"])
    data["n_units"] = len(data["cluster_ids"])
    data["n_spikes"] = len(data["spike_times"])
    data["duration_sec"] = data["spike_times"].max() / data["fs"]
    data["n_channels"] = data["templates"].shape[2]

    return data
```

### Step 3: Summarize the data

After loading, always present a brief summary:

```python
def summarize(data):
    """Print a concise summary of the loaded data."""
    print(f"Recording duration: {data['duration_sec']:.1f} s ({data['duration_sec']/60:.1f} min)")
    print(f"Total spikes: {data['n_spikes']:,}")
    print(f"Units: {data['n_units']}")
    print(f"Channels: {data['n_channels']}")
    print(f"Sample rate: {data['fs']:.0f} Hz")

    # Firing rates
    frs = []
    for cid in data["cluster_ids"]:
        n = (data["spike_clusters"] == cid).sum()
        frs.append(n / data["duration_sec"])
    frs = np.array(frs)
    print(f"\nFiring rates: mean={frs.mean():.2f} Hz, "
          f"median={np.median(frs):.2f} Hz, "
          f"range=[{frs.min():.2f}, {frs.max():.2f}] Hz")
```

### Step 4: Clarify the analysis goal

Ask clarifying questions until the goal is unambiguous before writing any script. If the goal is already clear, propose a brief plan and wait for confirmation.

---

## Available Visualizations

### 1. Spike Raster Plot

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def plot_raster(data, time_range=None, figsize=(14, 6), save_path="figures/raster.png"):
    """
    Plot spike raster with one row per unit.

    Parameters:
        data: dict from load_phy_data()
        time_range: (start_sec, end_sec) or None for full recording
        figsize: figure dimensions
        save_path: output file path
    """
    fig, ax = plt.subplots(figsize=figsize)

    spike_times_sec = data["spike_times"] / data["fs"]

    for i, cid in enumerate(data["cluster_ids"]):
        mask = data["spike_clusters"] == cid
        times = spike_times_sec[mask]

        if time_range:
            times = times[(times >= time_range[0]) & (times <= time_range[1])]

        ax.scatter(times, np.full_like(times, i), s=0.5, c="k", alpha=0.5)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Unit")
    ax.set_yticks(range(0, data["n_units"], max(1, data["n_units"] // 20)))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

### 2. Population Firing Rate

```python
def plot_population_rate(data, bin_size_ms=50, sigma_ms=100,
                         save_path="figures/pop_rate.png"):
    """
    Smoothed population firing rate over time.

    Parameters:
        data: dict from load_phy_data()
        bin_size_ms: histogram bin size in milliseconds
        sigma_ms: Gaussian smoothing sigma in milliseconds
        save_path: output file path
    """
    from scipy.ndimage import gaussian_filter1d

    fig, ax = plt.subplots(figsize=(14, 4))

    spike_times_ms = data["spike_times"] / data["fs"] * 1000.0
    duration_ms = data["duration_sec"] * 1000.0

    bins = np.arange(0, duration_ms + bin_size_ms, bin_size_ms)
    counts, _ = np.histogram(spike_times_ms, bins=bins)

    # Convert to rate (Hz) per unit
    rate_hz = counts / (bin_size_ms / 1000.0) / data["n_units"]

    # Smooth
    sigma_bins = sigma_ms / bin_size_ms
    rate_smooth = gaussian_filter1d(rate_hz.astype(float), sigma=sigma_bins)

    time_sec = bins[:-1] / 1000.0
    ax.plot(time_sec, rate_smooth, color="#2c3e50", linewidth=0.8)
    ax.fill_between(time_sec, rate_smooth, alpha=0.15, color="#3498db")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Firing rate (Hz)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

### 3. Firing Rate Distribution

```python
def plot_fr_distribution(data, save_path="figures/fr_distribution.png"):
    """Histogram of per-unit firing rates."""
    fig, ax = plt.subplots(figsize=(8, 5))

    frs = []
    for cid in data["cluster_ids"]:
        n = (data["spike_clusters"] == cid).sum()
        frs.append(n / data["duration_sec"])
    frs = np.array(frs)

    ax.hist(frs, bins=30, color="#3498db", edgecolor="white", alpha=0.8)
    ax.axvline(np.median(frs), color="#e74c3c", linestyle="--",
               label=f"Median: {np.median(frs):.2f} Hz")
    ax.set_xlabel("Firing rate (Hz)")
    ax.set_ylabel("Count")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

### 4. Waveform Template Gallery

```python
def plot_templates(data, max_units=20, save_path="figures/templates.png"):
    """
    Plot waveform templates for top units by spike count.

    Parameters:
        data: dict from load_phy_data()
        max_units: maximum number of templates to show
        save_path: output file path
    """
    templates = data.get("templates_unwhitened", data["templates"])

    # Sort by spike count (most active first)
    counts = [(cid, (data["spike_clusters"] == cid).sum()) for cid in data["cluster_ids"]]
    counts.sort(key=lambda x: -x[1])
    top_ids = [c[0] for c in counts[:max_units]]

    n_show = len(top_ids)
    cols = min(5, n_show)
    rows = (n_show + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(3 * cols, 2.5 * rows))
    axes = np.atleast_2d(axes)

    for idx, cid in enumerate(top_ids):
        r, c = divmod(idx, cols)
        ax = axes[r, c]

        # Find best channel (max amplitude)
        t = templates[cid]
        best_ch = np.argmax(np.ptp(t, axis=0))
        waveform = t[:, best_ch]

        n_spikes = (data["spike_clusters"] == cid).sum()
        fr = n_spikes / data["duration_sec"]

        time_ms = np.arange(len(waveform)) / data["fs"] * 1000.0
        ax.plot(time_ms, waveform, color="#2c3e50", linewidth=1.2)
        ax.set_title(f"Unit {cid}\n{n_spikes} spk, {fr:.1f} Hz", fontsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(labelsize=7)

    # Hide empty subplots
    for idx in range(n_show, rows * cols):
        r, c = divmod(idx, cols)
        axes[r, c].set_visible(False)

    fig.supxlabel("Time (ms)", fontsize=9)
    fig.supylabel("Amplitude (a.u.)", fontsize=9)
    plt.tight_layout()

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

### 5. Electrode Map with Unit Locations

```python
def plot_electrode_map(data, save_path="figures/electrode_map.png"):
    """
    Scatter plot of electrode positions colored by unit firing rate.

    Parameters:
        data: dict from load_phy_data()
        save_path: output file path
    """
    templates = data.get("templates_unwhitened", data["templates"])
    positions = data["channel_positions"]

    fig, ax = plt.subplots(figsize=(6, 10))

    # Plot all electrodes as gray background
    ax.scatter(positions[:, 0], positions[:, 1], s=8, c="#ecf0f1",
               edgecolors="#bdc3c7", linewidths=0.3, zorder=1)

    # Overlay unit positions (best channel per unit)
    frs = []
    xs, ys = [], []
    for cid in data["cluster_ids"]:
        t = templates[cid]
        best_ch = np.argmax(np.ptp(t, axis=0))
        xs.append(positions[best_ch, 0])
        ys.append(positions[best_ch, 1])
        n = (data["spike_clusters"] == cid).sum()
        frs.append(n / data["duration_sec"])

    scatter = ax.scatter(xs, ys, s=30, c=frs, cmap="hot", edgecolors="k",
                         linewidths=0.5, zorder=2)
    cbar = plt.colorbar(scatter, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Firing rate (Hz)")

    ax.set_xlabel("X position (μm)")
    ax.set_ylabel("Y position (μm)")
    ax.set_aspect("equal")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

### 6. ISI Distribution

```python
def plot_isi_distribution(data, unit_id=None, max_isi_ms=100,
                          save_path="figures/isi_distribution.png"):
    """
    Inter-spike interval histogram for one or all units.

    Parameters:
        data: dict from load_phy_data()
        unit_id: specific cluster ID, or None for all units pooled
        max_isi_ms: maximum ISI to display (ms)
        save_path: output file path
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    if unit_id is not None:
        mask = data["spike_clusters"] == unit_id
        times = data["spike_times"][mask] / data["fs"] * 1000.0  # to ms
        isis = np.diff(times)
        title_suffix = f" (Unit {unit_id})"
    else:
        # Pool ISIs across all units
        isis = []
        for cid in data["cluster_ids"]:
            mask = data["spike_clusters"] == cid
            times = data["spike_times"][mask] / data["fs"] * 1000.0
            isis.append(np.diff(times))
        isis = np.concatenate(isis)
        title_suffix = " (all units)"

    isis = isis[isis <= max_isi_ms]

    ax.hist(isis, bins=100, color="#3498db", edgecolor="white", alpha=0.8)
    ax.axvline(1.5, color="#e74c3c", linestyle="--", linewidth=1,
               label="Refractory (1.5 ms)")
    ax.set_xlabel("Inter-spike interval (ms)")
    ax.set_ylabel("Count")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

### 7. STTC Correlation Matrix

```python
def compute_sttc_matrix(data, delt_ms=20.0, bin_size_ms=1.0):
    """
    Compute the spike time tiling coefficient matrix for all unit pairs.

    Parameters:
        data: dict from load_phy_data()
        delt_ms: coincidence window in milliseconds
        bin_size_ms: raster bin size for computation

    Returns:
        sttc_matrix: (N, N) array of STTC values
    """
    spike_times_ms = data["spike_times"] / data["fs"] * 1000.0
    duration_ms = data["duration_sec"] * 1000.0
    n = data["n_units"]
    sttc_mat = np.zeros((n, n))

    # Build per-unit spike time arrays
    trains = []
    for cid in data["cluster_ids"]:
        mask = data["spike_clusters"] == cid
        trains.append(spike_times_ms[mask])

    # Compute pairwise STTC
    for i in range(n):
        for j in range(i + 1, n):
            val = _sttc(trains[i], trains[j], delt_ms, duration_ms)
            sttc_mat[i, j] = val
            sttc_mat[j, i] = val

    return sttc_mat


def _sttc(tA, tB, delt, length):
    """Compute STTC between two spike trains (Cutts & Eglen 2014)."""
    if len(tA) == 0 or len(tB) == 0:
        return 0.0
    TA = _sttc_ta(tA, delt, length) / length
    TB = _sttc_ta(tB, delt, length) / length
    PA = _sttc_na(tA, tB, delt) / len(tA)
    PB = _sttc_na(tB, tA, delt) / len(tB)
    aa = (PA - TB) / (1 - PA * TB) if PA * TB != 1 else 0
    bb = (PB - TA) / (1 - PB * TA) if PB * TA != 1 else 0
    return (aa + bb) / 2


def _sttc_ta(tA, delt, tmax):
    """Total time within delt of spikes."""
    if len(tA) == 0:
        return 0
    base = min(delt, tA[0]) + min(delt, tmax - tA[-1])
    return base + np.minimum(np.diff(tA), 2 * delt).sum()


def _sttc_na(tA, tB, delt):
    """Number of spikes in A within delt of any spike in B."""
    if len(tB) == 0:
        return 0
    tA, tB = np.asarray(tA), np.asarray(tB)
    iB = np.searchsorted(tB, tA)
    np.clip(iB, 1, len(tB) - 1, out=iB)
    dt_left = np.abs(tB[iB] - tA)
    dt_right = np.abs(tB[iB - 1] - tA)
    return (np.minimum(dt_left, dt_right) <= delt).sum()


def plot_sttc_matrix(sttc_mat, cluster_ids, save_path="figures/sttc_matrix.png"):
    """Plot STTC correlation heatmap."""
    fig, ax = plt.subplots(figsize=(8, 7))

    im = ax.imshow(sttc_mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="equal")
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("STTC")

    ax.set_xlabel("Unit")
    ax.set_ylabel("Unit")

    # Show all 4 spines for heatmaps
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.5)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_path}")
```

---

## Writing Analysis Scripts

### File placement

- All scripts go inside the analysis directory (e.g., `analysis/<project>/`)
- Use descriptive filenames (e.g., `compute_sttc.py`, `plot_burst_raster.py`)
- Never write scripts inside `Algorithms/` or `Services/`

### Script structure

Every script should be self-contained and runnable:

```python
"""
<Brief description of what this script does>
"""
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — always set first
import matplotlib.pyplot as plt
import numpy as np
import os

# --- Configuration ---
PHY_ZIP = "path/to/recording_phy.zip"
OUTPUT_DIR = "analysis/project/figures"

# --- Load data ---
data = load_phy_data(PHY_ZIP)
summarize(data)

# --- Analysis ---
# ... computation here ...

# --- Save figure ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
fig.savefig(os.path.join(OUTPUT_DIR, "figure.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
```

### Figure output conventions

- **Always save as `.png`** — never call `plt.show()`
- **Always use `matplotlib.use("Agg")`** at the top, before other matplotlib imports
- Save in a `figures/` subdirectory within the project
- Use `dpi=150, bbox_inches="tight"` for all `savefig` calls
- Remove top and right spines by default
- Every axis must have a label with units (e.g., "Time (s)", "Firing rate (Hz)")
- Use `"hot"` colormap for firing rates, `"RdBu_r"` for correlations
- Include colorbars with labels on all heatmaps
- Do not add titles unless the user specifically requests them

---

## ANALYSIS_LOG.md

Maintain an `ANALYSIS_LOG.md` in each analysis project directory. Update it after every session:

```markdown
# Analysis Log — <project_name>

## Data
- UUID: <uuid>
- Recording: <filename>
- Duration: X min, N units, M channels

## Analyses Performed

### <Date> — <Description>
- Script: `<script_path>`
- What was done: <brief description>
- Key findings: <results>
- Figures: `figures/<filename>.png`

## Open Questions
- ...
```

---

## General Conventions

- **Spike times in Phy files**: stored in **samples** (divide by `fs` for seconds, multiply by 1000/fs for ms)
- **All spike times in SpikeCanvas pipeline**: milliseconds
- **Template shape**: `(K, T, C)` — K templates, T time samples, C channels
- **Figure format**: PNG, 150 DPI, tight bounding box
- **Do not modify library or pipeline source files.** If you find a bug, report it to the user.
- **Never delete files without user permission.**
