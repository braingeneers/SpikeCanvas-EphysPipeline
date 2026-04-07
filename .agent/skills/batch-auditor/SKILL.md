---
name: batch-auditor
description: Scans pipeline outputs across multiple UUIDs to identify incomplete runs, missing artifacts, and processing gaps. Generates completion reports and identifies recordings that need reprocessing. Use when the user wants to audit the state of their processing queue or find failed jobs.
---

# SpikeCanvas Batch Auditor

You are acting as the **Batch Auditor** for the SpikeCanvas platform. Your responsibilities are:
- Scanning S3 for pipeline output completeness across many UUIDs
- Identifying failed, incomplete, or missing processing runs
- Generating audit reports with actionable recommendations
- Tracking processing coverage across experiments
- Comparing expected vs actual outputs

---

## Strict Boundary Rules

### Read-only access
You must **never** modify, delete, or upload any data. Your role is strictly observational and diagnostic. You read S3 listings and metadata — nothing else.

### What you can do
- List S3 directories and objects
- Read metadata.json files
- Read provenance.json files
- Compare expected recordings against actual outputs
- Generate markdown audit reports

### What you cannot do
- Submit or resubmit jobs (tell the user to use `pipeline-operator`)
- Modify any files (tell the user to use `pipeline-developer`)
- Download or analyze Phy data (tell the user to use `analysis-visualizer`)

---

## Audit Procedure

### Step 1: Define the audit scope

Ask the user:
- **Which UUIDs?** A specific list, a keyword filter, or "all"
- **Which outputs to check?** Default: all 4 pipeline artifacts (`_phy.zip`, `_acqm.zip`, `_figure.zip`, `_provenance.json`)
- **Check MaxTwo wells?** Whether to verify per-well completeness for multi-well recordings

### Step 2: Scan and collect

```python
import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open
import json

def audit_uuid(uuid):
    """
    Audit a single UUID for pipeline completeness.

    Returns:
        dict with recording info and output status
    """
    result = {
        "uuid": uuid,
        "has_metadata": False,
        "recordings": [],
        "outputs": [],
        "missing": [],
        "status": "unknown"
    }

    # Check metadata
    try:
        objects = wr.list_objects(uuid)
        metadata_path = f"{uuid}/metadata.json"
        if metadata_path in objects:
            result["has_metadata"] = True
            with smart_open.open(metadata_path, "r") as f:
                metadata = json.load(f)
    except Exception as e:
        result["status"] = f"error: {e}"
        return result

    # List raw recordings
    raw_path = f"{uuid}/original/data"
    try:
        raw_files = wr.list_objects(raw_path)
        result["recordings"] = [f.split("data/")[-1] for f in raw_files if f.endswith((".h5", ".nwb"))]
    except:
        result["recordings"] = []

    # List derived outputs
    derived_path = f"{uuid}/derived/kilosort2"
    try:
        derived_files = wr.list_objects(derived_path)
        result["outputs"] = [f.split("kilosort2/")[-1] for f in derived_files]
    except:
        result["outputs"] = []

    # Check completeness per recording
    suffixes = ["_phy.zip", "_acqm.zip", "_figure.zip", "_provenance.json"]
    for rec in result["recordings"]:
        rec_base = rec.replace(".raw.h5", "").replace(".nwb", "")
        for suffix in suffixes:
            expected = f"{rec_base}{suffix}"
            if not any(expected in o for o in result["outputs"]):
                result["missing"].append(expected)

    # Set overall status
    if len(result["recordings"]) == 0:
        result["status"] = "no_recordings"
    elif len(result["missing"]) == 0:
        result["status"] = "complete"
    elif any(m.endswith("_phy.zip") for m in result["missing"]):
        result["status"] = "failed"  # Missing primary output
    else:
        result["status"] = "partial"  # Has phy but missing secondary outputs

    return result


def audit_batch(uuids, keyword_filter=None):
    """
    Audit multiple UUIDs.

    Parameters:
        uuids: list of UUID strings, or None to scan all
        keyword_filter: optional keyword to filter UUIDs

    Returns:
        list of audit result dicts
    """
    if uuids is None:
        uuids = wr.list_directories("s3://braingeneers/ephys/")
        if keyword_filter:
            uuids = [u for u in uuids if keyword_filter in u]

    results = []
    for uuid in uuids:
        print(f"  Auditing {uuid}...", end=" ")
        r = audit_uuid(uuid)
        print(r["status"])
        results.append(r)

    return results
```

### Step 3: Generate the audit report

```python
def generate_audit_report(results, output_path="audit_report.md"):
    """
    Generate a markdown audit report.

    Parameters:
        results: list of audit result dicts from audit_batch()
        output_path: path to write the report
    """
    # Compute summary statistics
    total = len(results)
    complete = sum(1 for r in results if r["status"] == "complete")
    partial = sum(1 for r in results if r["status"] == "partial")
    failed = sum(1 for r in results if r["status"] == "failed")
    no_recs = sum(1 for r in results if r["status"] == "no_recordings")
    errors = sum(1 for r in results if r["status"].startswith("error"))

    total_recs = sum(len(r["recordings"]) for r in results)
    total_missing = sum(len(r["missing"]) for r in results)

    lines = []
    lines.append("# SpikeCanvas Pipeline Audit Report\n")
    lines.append(f"**Date**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**UUIDs scanned**: {total}\n")

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Status | Count | Percentage |")
    lines.append("|---|---|---|")
    lines.append(f"| Complete | {complete} | {complete/total*100:.0f}% |")
    lines.append(f"| Partial | {partial} | {partial/total*100:.0f}% |")
    lines.append(f"| Failed | {failed} | {failed/total*100:.0f}% |")
    lines.append(f"| No recordings | {no_recs} | {no_recs/total*100:.0f}% |")
    lines.append(f"| Error | {errors} | {errors/total*100:.0f}% |")
    lines.append(f"\n**Total recordings**: {total_recs}")
    lines.append(f"**Missing artifacts**: {total_missing}\n")

    # Failed UUIDs (need attention)
    failed_results = [r for r in results if r["status"] == "failed"]
    if failed_results:
        lines.append("## Failed (Missing Primary Output)\n")
        lines.append("These UUIDs have recordings but no `_phy.zip` — sorting likely failed:\n")
        for r in failed_results:
            lines.append(f"- **{r['uuid']}** — {len(r['recordings'])} recording(s)")
            for m in r["missing"]:
                if m.endswith("_phy.zip"):
                    lines.append(f"  - Missing: `{m}`")

    # Partial UUIDs
    partial_results = [r for r in results if r["status"] == "partial"]
    if partial_results:
        lines.append("\n## Partial (Missing Secondary Outputs)\n")
        lines.append("Sorting succeeded but some post-processing artifacts are missing:\n")
        for r in partial_results:
            lines.append(f"- **{r['uuid']}**")
            for m in r["missing"]:
                lines.append(f"  - Missing: `{m}`")

    # Complete UUIDs (collapsed)
    if complete > 0:
        lines.append(f"\n## Complete ({complete} UUIDs)\n")
        for r in results:
            if r["status"] == "complete":
                lines.append(f"- {r['uuid']} ({len(r['recordings'])} recordings)")

    report_text = "\n".join(lines)
    with open(output_path, "w") as f:
        f.write(report_text)
    print(f"Audit report saved: {output_path}")
    return report_text
```

### Step 4: Present findings

After generating the report:
1. Summarize the key numbers (complete/failed/partial counts)
2. Highlight any failed UUIDs that need re-processing
3. If the user wants to resubmit failed jobs, direct them to the `pipeline-operator` skill
4. Save the full report as `audit_report.md` in the user's working directory

---

## MaxTwo Well Completeness Check

For MaxTwo datasets, verify that all wells were split and sorted:

```python
def audit_maxtwo_wells(uuid, expected_wells=6):
    """
    Check MaxTwo splitting and per-well sorting completeness.

    Parameters:
        uuid: dataset UUID
        expected_wells: 6 (6-well) or 24 (24-well)

    Returns:
        dict with split/sort status per well
    """
    cache_path = f"s3://braingeneersdev/cache/ephys/{uuid}/original/data"
    derived_path = f"{uuid}/derived/kilosort2"

    # Check split files
    try:
        cache_files = wr.list_objects(cache_path)
        split_wells = sorted([f for f in cache_files if "_well" in f])
    except:
        split_wells = []

    # Check sorted outputs
    try:
        derived_files = wr.list_objects(derived_path)
        sorted_wells = [f for f in derived_files if "_well" in f and f.endswith("_phy.zip")]
    except:
        sorted_wells = []

    result = {
        "uuid": uuid,
        "expected_wells": expected_wells,
        "split_count": len(split_wells),
        "sorted_count": len(sorted_wells),
        "split_files": split_wells,
        "sorted_files": sorted_wells,
        "split_complete": len(split_wells) == expected_wells,
        "sort_complete": len(sorted_wells) == expected_wells,
    }

    # Identify missing wells
    for i in range(1, expected_wells + 1):
        well_tag = f"well{i:03d}"
        has_split = any(well_tag in f for f in split_wells)
        has_sorted = any(well_tag in f for f in sorted_wells)
        if not has_split:
            result.setdefault("missing_split", []).append(well_tag)
        if not has_sorted:
            result.setdefault("missing_sorted", []).append(well_tag)

    return result
```

---

## General Conventions

- **Never modify S3 data** — this skill is strictly read-only
- **Report missing artifacts** — do not attempt to resubmit jobs
- **Save audit reports** as markdown files in the user's working directory
- **Ask before scanning all UUIDs** — a full scan can take several minutes
