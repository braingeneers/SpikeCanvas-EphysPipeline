# MaxTwo Automated Pipeline Implementation Summary

## Overview
This document summarizes the completed implementation of the automated MaxTwo electrophysiology recording pipeline that integrates with the existing MQTT listener service.

## Implementation Status: COMPLETE

### Core Components Implemented

#### 1. MaxTwo Detection Logic
- **File**: `mqtt_listener.py`
- **Function**: `is_maxtwo_recording(data_format: str, file_path: str) -> bool`
- **Logic**: Returns `True` when `data_format == "maxtwo"` AND file ends with `.raw.h5` or `.h5`
- **Default Behavior**: If `data_format` is not specified in MQTT message, defaults to `"maxone"`

#### 2. Pipeline Branching Logic
- **MaxTwo Pipeline**: Original recording → Splitter (1 job) → Watch & Fanout → 6 Sorter jobs
- **Non-MaxTwo Pipeline**: Direct spike sorting with `ephys_pipeline`
- **Integration Point**: Modified `run_sorting()` method in `JobMessage` class

#### 3. Well Validation Logic
- **Before Processing**: Checks if ALL 6 wells already have results before running splitter
- **Well Naming**: `well001`, `well002`, `well003`, `well004`, `well005`, `well006`
- **Result Paths**: `{base_name}_well{i:03d}_phy.zip`
- **Behavior**: Only skips splitter if ALL wells exist (not just ANY well)

#### 4. Configuration Management
- **Splitter Config**: `get_splitter_config()` returns hardcoded configuration
  ```python
  {
      "args": "./start_splitter.sh",
      "cpu_request": 8,
      "memory_request": 64,
      "disk_request": 400,
      "GPU": 0,
      "image": "surygeng/maxtwo_splitter:v0.1"
  }
  ```
- **Sorter Template**: `get_sorter_template()` loads from `sorting_job_info.json`

#### 5. Fanout Integration
- **File**: `splitter_fanout.py`
- **Function**: `spawn_splitter_fanout(uuid, experiment, splitter_cfg, sorter_tpl)`
- **Behavior**: 
  - Submits splitter job if it doesn't exist
  - Starts background watcher thread
  - When splitter succeeds, launches 6 sorter jobs for individual wells

#### 6. Shared Utilities
- **File**: `job_utils.py` (newly created)
- **Purpose**: Resolves circular import issues
- **Contents**: `JOB_PREFIX`, `DEFAULT_S3_BUCKET`, `NAMESPACE`, `format_job_name()`

### Data Format Support
The pipeline now supports the following data formats:
- `maxtwo`: 6-well MaxTwo recordings requiring splitting
- `maxtwo-split`: Pre-split MaxTwo wells (direct sorting)
- `maxone`: Single-well MaxOne recordings (direct sorting)
- `nwb`: NWB format recordings (direct sorting)

### File Extension Support
- MaxTwo recordings: `.raw.h5` and `.h5`
- All other formats: various extensions as supported by existing pipeline

## Key Code Changes

### 1. Modified `mqtt_listener.py`
```python
# Added MaxTwo detection and branching logic
if is_maxtwo_recording(fmt, file_path):
    # Check if ALL 6 wells exist
    all_wells_exist = True
    missing_wells = []
    for i in range(1, 7):
        well_result_path = result_path.replace(
            f"{exp}_phy.zip", 
            f"{base_exp}_well{i:03d}_phy.zip"
        )
        if not check_exist(well_result_path):
            all_wells_exist = False
            missing_wells.append(f"well{i:03d}")
    
    if overwrite or not all_wells_exist:
        # Use splitter fanout for MaxTwo recordings
        spawn_splitter_fanout(uuid, exp, splitter_cfg, sorter_tpl)
    else:
        logging.info("All MaxTwo well results exist. Moving on...")

elif fmt in ["maxone", "nwb", "maxtwo-split"]:
    # Regular single-file processing
    if overwrite or not check_exist(result_path):
        create_sort(exp, file_path)
```

### 2. Enhanced `splitter_fanout.py`
- Uses shared utilities from `job_utils.py`
- Proper job naming for Kubernetes compliance
- Background watching with automatic fanout

### 3. Created `job_utils.py`
- Centralized shared constants and functions
- Resolves circular import issues
- Consistent job naming across modules

## Logging and Monitoring

### Enhanced Logging
- Detailed logging for MaxTwo detection
- Missing wells reporting
- Pipeline decision explanations
- Job creation status

### Example Log Output
```
INFO: Experiment: M06359_D51_KOLFMO_632025
INFO: Data format: maxtwo
INFO: Detected MaxTwo recording: M06359_D51_KOLFMO_632025
INFO: Missing results for wells: well001, well003, well005
INFO: Starting MaxTwo splitter fanout for uuid, M06359_D51_KOLFMO_632025
```

## Docker Images Used
- **Splitter**: `surygeng/maxtwo_splitter:v0.1`
- **Sorter**: `braingeneers/ephys_pipeline:v0.72` (from sorting_job_info.json)

## Testing Recommendations

### 1. Unit Testing
```bash
# Test MaxTwo detection logic
python -c "
from mqtt_listener import is_maxtwo_recording
assert is_maxtwo_recording('maxtwo', 'test.raw.h5') == True
assert is_maxtwo_recording('maxone', 'test.raw.h5') == False
print('Detection logic tests passed')
"
```

### 2. Integration Testing
1. **Test with actual MaxTwo data**:
   - Send MQTT message with `data_format: "maxtwo"`
   - Verify splitter job is created
   - Verify 6 sorter jobs are created after splitter completes

2. **Test well existence checking**:
   - Create some but not all well results
   - Verify splitter still runs
   - Create all 6 well results
   - Verify splitter is skipped

3. **Test overwrite behavior**:
   - With `overwrite: true`, verify splitter always runs
   - With `overwrite: false`, verify well checking works

### 3. Error Scenarios
- Invalid data formats
- Missing configuration files
- Failed splitter jobs
- Network/S3 connectivity issues

## Next Steps

### 1. Deployment
- Deploy updated `mqtt_listener.py` to Kubernetes
- Ensure `sorting_job_info.json` and `job_type_table.json` are available
- Verify docker images are accessible

### 2. Monitoring
- Monitor MQTT listener logs for MaxTwo processing
- Track job success rates for splitter and sorter jobs
- Monitor S3 for expected output files

### 3. Performance Optimization
- Monitor resource usage of splitter jobs
- Optimize CPU/memory allocations if needed
- Consider parallel processing optimizations

### 4. Documentation Updates
- Update user documentation for MaxTwo support
- Document new data format options
- Create troubleshooting guide

## File Structure
```
Spike_Sorting_Listener/
├── src/
│   ├── mqtt_listener.py          # Modified - Main pipeline logic
│   ├── splitter_fanout.py        # Modified - MaxTwo fanout logic  
│   ├── job_utils.py              # Created - Shared utilities
│   ├── k8s_kilosort2.py          # Existing - Kubernetes interface
│   ├── sorting_job_info.json     # Existing - Sorter configuration
│   └── job_type_table.json       # Existing - Slack notifications
└── test/
    └── test_maxtwo_pipeline.py   # Created - Test suite
```

## Summary
The MaxTwo automated pipeline implementation is **COMPLETE** and ready for deployment. The solution:

- **Detects MaxTwo recordings** using `data_format` field  
- **Integrates with existing MQTT listener** seamlessly  
- **Supports all required data formats** (maxtwo, maxone, nwb, maxtwo-split)  
- **Handles both file extensions** (.raw.h5 and .h5)  
- **Ensures ALL 6 wells are processed** before skipping  
- **Provides comprehensive logging** for monitoring  
- **Resolves circular import issues** with shared utilities  
- **Follows existing code patterns** and best practices  

The implementation is robust, well-documented, and ready for production use.
