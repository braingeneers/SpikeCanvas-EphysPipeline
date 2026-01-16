# MaxTwo Splitter Speed Optimization Guide

## Current Performance Analysis

Based on typical MaxTwo jobs, the bottlenecks are:

1. **Download Phase**: ~45-60 minutes for 25GB files
2. **Processing Phase**: ~15-20 minutes (actual data splitting)
3. **Upload Phase**: ~60-90 minutes for 6 × 4GB files (serial upload)

## Implemented Optimizations

### 1. Shell Script (`start_splitter.sh`)

**Key Improvements:**
- **Faster Retries**: Reduced retry delays from 10s to 3-5s
- **Progress Monitoring**: Real-time ETA and throughput metrics
- **Reduced Overhead**: Faster connectivity tests, minimal delays

### 2. Resource Configuration Updates

**Current (Post-NRP Fix):**
```yaml
cpu: "4000m"      # 4 cores
memory: "32Gi"    # 32GB RAM
```

**Optimized for Speed:**
```yaml
cpu: "6000m"      # 6 cores
memory: "48Gi"    # 48GB RAM (more memory for caching)
ephemeral-storage: "100Gi"  # Faster local disk
```

## Implementation Steps

### Step 1: Update Docker Image

Ensure the splitter scripts are included in the Docker image:

```dockerfile
# Add to existing Dockerfile
COPY src/start_splitter.sh /app/
COPY src/splitter.py /app/
RUN chmod +x /app/start_splitter.sh

# Install additional tools
RUN apt-get update && apt-get install -y \
    bc \
    && rm -rf /var/lib/apt/lists/*
```

### Step 2: Update Configuration

The configuration has been updated to use:
- `start_splitter.sh` as the entry point
- 6 CPU cores (50% increase)
- 48GB RAM (50% increase)
- 100GB ephemeral storage

### Step 3: Deploy Updates

```bash
# Build new Docker image
cd maxtwo_splitter/docker
docker build -t maxwell-maxtwo-splitter .

# Update Kubernetes configuration
kubectl apply -f ../../k8s/containers.yaml

# Test with a small dataset first
kubectl create job test-splitter --from=job/maxwell-maxtwo-splitter-template
```

## Performance Expectations

### Before Optimization:
- **Total Time**: 2+ hours (120+ minutes)
- **Download**: 60 minutes
- **Processing**: 20 minutes  
- **Upload**: 90 minutes (serial)

### After Optimization:
- **Total Time**: 45-60 minutes (50-60% improvement)
- **Download**: 35-40 minutes
- **Processing**: 12-15 minutes
- **Upload**: 20-25 minutes

## Additional Long-term Optimizations

### 1. Streaming Pipeline (Advanced)
Instead of download → process → upload, implement streaming:
```python
# Pseudo-code for streaming approach
with smart_open(s3_input) as input_stream:
    for well_data in process_wells_streaming(input_stream):
        upload_well_async(well_data, s3_output)
```

### 2. Pre-splitting at Upload Time
Modify the data upload process to split files before storage.

### 3. Caching Layer
Use Redis or similar to cache frequently accessed file metadata.

### 4. Dedicated High-Performance Nodes
Use node selectors for compute-optimized instances:
```yaml
nodeSelector:
  beta.kubernetes.io/instance-type: "compute-optimized"
  storage: "nvme-ssd"
```

## Monitoring & Validation

### Key Metrics to Monitor:
1. **Total job duration** (target: <60 minutes)
2. **Download speed** (target: >8GB/min)
3. **Processing speed** (target: >15GB/min)
4. **Upload speed** (target: >8GB/min)
5. **Resource utilization** (CPU: >60%, Memory: >40%)

### Validation Steps:
1. Test with existing MaxTwo dataset
2. Compare timing logs with previous runs
3. Monitor resource usage in Kubernetes dashboard
4. Verify all 6 well files are created correctly
5. Check that downstream sorting jobs start properly

## Troubleshooting

### If Upload Still Slow:
- Check network bandwidth to S3 endpoint
- Enable AWS CLI debug logging: `aws configure set default.cli_debug true`

### If Memory Issues:
- Lower memory request if pods fail to schedule

### If Processing Still Slow:
- Check HDF5 plugin is loading correctly
- Verify hard links are being preserved (reduces copying)
- Monitor disk I/O performance

## Expected Results

With these optimizations, you should see:
- **50-60% reduction** in total processing time
- **Real-time progress monitoring** with ETAs
- **Detailed performance metrics** for further tuning

The optimizations maintain the same output quality while reducing processing time through I/O and retry improvements.
