# MaxTwo Automated Pipeline Implementation - Complete

## Overview
Successfully implemented and **production-tested** automated MaxTwo electrophysiology recording pipeline that integrates splitter and spike sorting functionality into the existing MQTT listener service. All major bugs resolved and **connection stability issues fixed** - system is now working reliably.

## Latest Updates (June 16, 2025)

### CONNECTION STABILITY FIXES IMPLEMENTED
- **Fixed InvalidChunkLength errors**: Enhanced API connection management with fresh client creation per request
- **Progressive backoff strategy**: Intelligent retry logic that backs off progressively on consecutive failures  
- **Timeout protection**: Added 30-second timeouts to prevent hanging API calls
- **Error classification**: Better handling of connection vs. other API errors
- **Reduced API spam**: Smarter retry logic prevents overwhelming the Kubernetes API during outages

###  Technical Improvements
- `_safe_get_job_status()`: Robust job status retrieval with retry logic and connection management
- Progressive backoff: 30s → 60s → 90s → 120s (capped) for consecutive errors  
- Increased error tolerance: Max consecutive errors raised from 5 to 10
- Better logging: Progress tracking and error classification for easier debugging

## Implementation Summary

### 1. Core Components Implemented

#### A. MaxTwo Detection Logic
- **Function**: `is_maxtwo_recording(data_format: str, file_path: str) -> bool`
- **Logic**: Detects MaxTwo recordings by checking:
  - `data_format == "maxtwo"`
  - File extension is `.raw.h5` or `.h5`
- **Default Behavior**: If no `data_format` specified, defaults to `"maxone"`

#### B. Pipeline Branching
- **MaxTwo Pipeline**: Original → Splitter Job → Watch & Fanout → 6 Sorter Jobs
- **Non-MaxTwo Pipeline**: Direct spike sorting with `kilosort2_simplified`

#### C. Configuration Management
- **Splitter Config**: `get_splitter_config()` returns hardcoded Docker container settings
- **Sorter Template**: `get_sorter_template()` loads from `sorting_job_info.json`

#### D. Job Orchestration
- **Splitter Fanout**: `spawn_splitter_fanout()` submits splitter + background watcher
- **Result Validation**: Checks ALL 6 wells exist before skipping splitter

### 2. File Structure Changes

#### A. Created Files
```
/src/job_utils.py           # Shared utilities (resolves circular imports)
/test/test_maxtwo_pipeline.py    # Unit tests
/validate_logic.py          # Standalone validation script
```

#### B. Modified Files
```
/src/mqtt_listener.py       # Main MQTT listener with MaxTwo integration
/src/splitter_fanout.py     # Splitter job management and watcher
```

### 3. Data Format Support
- **maxtwo**: 6-well recordings requiring splitting → Splitter pipeline
- **maxone**: Single-well recordings → Direct sorting
- **nwb**: NeuroDataWithoutBorders format → Direct sorting  
- **maxtwo-split**: Pre-split well files → Direct sorting

### 4. Well Processing Logic
- **Well Naming**: `well000`, `well001`, ..., `well005`
- **Result Paths**: `{base_name}_well{i:03d}_phy.zip`
- **Validation**: Ensures ALL 6 wells processed before skipping
- **Missing Wells Logging**: Detailed logging of which wells need processing

### 5. Error Handling & Logging
- **Comprehensive Logging**: All pipeline decisions and missing wells logged
- **Robust Connection Management**: Automatic token refresh and API client recreation
- **Graceful Failure Recovery**: Thread-safe error handling with retry limits
- **Production Debugging**: Detailed status reporting and kubectl commands for manual intervention
- **Input Validation**: Comprehensive parameter and configuration validation

### 6. Threading & Concurrency
- **Thread-safe Design**: Each watcher thread has its own Kubernetes API client
- **Multiple Recording Support**: Concurrent processing of multiple MaxTwo recordings in same UUID
- **Non-blocking Execution**: Background threads don't interfere with main MQTT processing
- **Proper Thread Management**: Non-daemon threads ensure logging completion

## Key Features

### 1. Backward Compatibility
- Existing MaxOne/NWB pipelines unchanged
- Default behavior maintains current functionality  
- No breaking changes to existing workflows
- Changed to `else:` condition for maximum compatibility

### 2. Resource Efficiency
- Only processes missing wells (intelligent skipping)
- Efficient Kube object reuse (single object per job)
- Configurable resource allocation per container type
- API rate limiting with delays between job creations

### 3. Monitoring & Debugging
- Detailed logging for all pipeline decisions
- Clear identification of missing well results
- Slack notifications for job status updates
- Manual debugging commands provided on timeout
- Failed wells tracking and reporting

### 4. Scalability & Reliability
- Parallel processing of 6 wells after splitting
- Kubernetes-native job management with proper error handling
- S3-based result validation
- Consecutive error counting prevents infinite loops
- Connection recovery with automatic retries
- Poll-based job monitoring (more stable than streaming)

## Validation Results

### Logic Testing 
 MaxTwo detection correctly identifies format + extension combinations  
 Job naming follows Kubernetes constraints (≤63 chars, alphanumeric + hyphens)  
 Pipeline routing logic correctly branches based on data format  
 Well path generation follows expected naming convention  
 Filename handling correctly extracts full experiment names with extensions

### Integration Testing 
 Shared utilities resolve circular import issues  
 Configuration functions return proper Docker settings  
 File structure maintains existing patterns  
 Threading architecture supports multiple concurrent recordings

### Production Testing 
 **Real MaxTwo data processing verified**  
 **Connection error recovery working correctly**  
 **Splitter and sorter jobs created successfully**  
 **Thread-safe operation confirmed with multiple recordings**  
 **Kubernetes API error handling validated**  
 **Poll-based monitoring more stable than streaming**

## Critical Issues Resolved

### 1. Fixed UUID Variable Conflict 
- **Problem**: Local variable `uuid` shadowed Python's `uuid` module
- **Solution**: Renamed to `uuid_param` in internal functions
- **Impact**: Eliminated mysterious import/execution errors

### 2. Fixed Empty Configuration Error 
- **Problem**: `Kube` constructor called with empty `{}` config
- **Solution**: Pass complete configuration with all required fields
- **Impact**: Eliminated "KeyError: 'cpu_request'" errors

### 3. Fixed Connection Instability 
- **Problem**: Kubernetes streaming watch causing "InvalidChunkLength" errors
- **Solution**: Replaced with robust poll-based monitoring with retry logic
- **Impact**: Eliminated thread crashes and improved reliability

### 4. Fixed Job Creation Logic 
- **Problem**: Premature sorter job launching before splitter completion
- **Solution**: Proper sequencing with job status validation
- **Impact**: Ensured correct pipeline execution order

### 5. Enhanced Error Recovery 
- **Problem**: No graceful handling of API failures
- **Solution**: Consecutive error counting, automatic token refresh, local API clients
- **Impact**: Production-ready reliability

## Deployment Instructions

### 1. Prerequisites
- Existing MQTT listener service running
- `maxtwo_splitter:v0.1` Docker image available
- `kilosort2_simplified` Docker image available
- Kubernetes cluster with sufficient resources

### 2. Deployment Steps
```bash
# 1. Deploy updated source files
kubectl cp src/job_utils.py <pod>:/app/src/
kubectl cp src/mqtt_listener.py <pod>:/app/src/
kubectl cp src/splitter_fanout.py <pod>:/app/src/

# 2. Restart MQTT listener service
kubectl delete pod <mqtt-listener-pod>  # Will auto-restart

# 3. Monitor logs for MaxTwo detection
kubectl logs -f <mqtt-listener-pod>
```

### 3. Testing with Real Data 
**Successfully tested with real MaxTwo recording:**
```json
{
  "uuid": "2025-06-03-e-MaxTwo_Test",
  "stitch": "False", 
  "overwrite": "False",
  "ephys_experiments": {
    "D57_KOLF2.2J_SmitsMidbrain_6OHDA_T2_72hr_connected": {
      "data_format": "maxtwo",
      "blocks": [{"path": "original/data/D57_KOLF2.2J_SmitsMidbrain_6OHDA_T2_72hr_connected.raw.h5"}]
    }
  }
}
```

### 4. Production Workflow Verified 
1.  MQTT listener detects MaxTwo format correctly
2.  Checks for existing well results (`*_well000_phy.zip` through `*_well005_phy.zip`)
3.  Starts splitter job with proper configuration
4.  Background watcher monitors splitter job with robust error handling
5.  Spawns 6 parallel sorter jobs after splitter completion
6.  Results stored in standard kilosort2 output location
7.  Multiple recordings in same UUID processed concurrently

## Monitoring & Troubleshooting

### 1. Success Log Patterns 
```
"=== spawn_splitter_fanout called ==="
"Creating splitter job with name: edp-{name}-split"  
"Splitter Job {name} submitted successfully"
"Started watcher thread for job {name}"
"Starting watcher for splitter job: {name}"
"[{name}] Succeeded → fan-out sorters"
"Sorter job creation complete: X created, Y skipped, Z failed"
```

### 2. Error Patterns & Solutions 
```
# Connection Issues (RESOLVED)
"API error checking job" → Automatic retry with token refresh
"InvalidChunkLength" → Replaced streaming with polling
"Too many consecutive errors" → Gives up gracefully after 5 attempts

# Configuration Issues (RESOLVED)  
"'cpu_request'" → Fixed by providing complete job config
"Failed to create splitter job" → Check Docker image availability

# Threading Issues (RESOLVED)
"Error in spawn_splitter_fanout" → Enhanced error handling and validation
```

### 3. Manual Debugging Commands 
```bash
# Check splitter job status
kubectl get job edp-{experiment-name}-split -n braingeneers

# Check sorter job status  
kubectl get jobs -l app=edp -n braingeneers | grep {experiment-name}

# View job logs
kubectl logs job/edp-{experiment-name}-split -n braingeneers
kubectl logs job/edp-{experiment-name}-well000 -n braingeneers

# Check MQTT listener logs
kubectl logs -f deployment/mqtt-listener -n braingeneers

# List active watcher threads
kubectl exec deployment/mqtt-listener -n braingeneers -- ps aux | grep python
```

## Implementation Status: **PRODUCTION READY** 

### Recently Completed (June 16, 2025) 
- [x]  **Connection Stability**: Fixed InvalidChunkLength and connection timeout issues
- [x]  **Progressive Backoff**: Intelligent retry strategy prevents API spam during outages  
- [x]  **Error Recovery**: Enhanced error classification and handling for different failure types
- [x]  **Timeout Protection**: Added request timeouts to prevent hanging connections
- [x]  **Connection Management**: Fresh API client creation per request eliminates state issues

### Previously Completed 
- [x]  MaxTwo detection and pipeline branching
- [x]  Splitter job orchestration with proper configuration 
- [x]  Background thread monitoring with robust error handling
- [x]  Sorter job fanout for all 6 wells
- [x]  Result path validation for ALL wells
- [x]  Integration with existing MQTT listener
- [x]  **Fixed all critical bugs (UUID conflict, config errors, connection issues)**
- [x]  **Production tested with real MaxTwo data**
- [x]  **Thread-safe implementation with multiple recording support**
- [x]  **Enhanced error recovery and monitoring**
- [x]  **Comprehensive input validation**

### Performance Verified 
- [x]  **Handles multiple MaxTwo recordings concurrently**
- [x]  **Robust connection recovery from network issues**
- [x]  **Graceful handling of partial failures**
- [x]  **Efficient resource utilization with object reuse**
- [x]  **Production-grade logging and debugging support**

## Future Enhancements (Optional)
- [ ] Add configurable timeout values for different job types
- [ ] Implement retry logic for failed sorter jobs
- [ ] Add Prometheus metrics for monitoring
- [ ] Create troubleshooting guide for operators
- [ ] Add automated cleanup of old completed jobs

---

**Implementation Status**:  **PRODUCTION READY**  
**Validation Status**:  **PASSED ALL TESTS**  
**Ready for Production**:  **YES - SUCCESSFULLY DEPLOYED**  

The MaxTwo automated pipeline is fully implemented, tested, and working reliably in production. All critical bugs have been resolved and the system handles real MaxTwo data processing successfully.
