---
description: How to check job status and troubleshoot failures
---

# Monitor Jobs

## Quick Status Check

```bash
# List all pipeline jobs (active and recent)
kubectl get jobs -n braingeneers | grep edp-

# List all pipeline pods with status
kubectl get pods -n braingeneers | grep edp-
```

## Stream Live Logs

```bash
# Follow logs from a running job
kubectl logs -f job/<job-name> -n braingeneers

# If multiple pods exist for a job, specify the pod
kubectl logs -f <pod-name> -n braingeneers

# Check init container logs (for download failures)
kubectl logs <pod-name> -n braingeneers -c init
```

## Diagnose Failures

```bash
# Get detailed pod status
kubectl describe pod <pod-name> -n braingeneers

# Get job events
kubectl describe job <job-name> -n braingeneers

# Check for OOM or eviction
kubectl get pod <pod-name> -n braingeneers -o jsonpath='{.status.containerStatuses[0].state}'
```

## Common Failure Patterns

| Pod Status | Likely Cause | Fix |
|---|---|---|
| `Pending` | No available GPU node matching affinity | Wait, or check whitelist in sorting_job_info.json |
| `Error` | Kilosort segfault on bad node | Re-submit; whitelist should exclude bad nodes |
| `OOMKilled` | Recording too large for 32 Gi memory | Increase memory_request in sorting_job_info.json |
| `ImagePullBackOff` | Wrong image tag or registry down | Verify image tag exists; check Docker Hub |
| `Completed` (but no outputs) | Pipeline exited 0 with low activity | Check for KILOSORT_FAILED_LOW_ACTIVITY.txt |

## Check Pipeline Outputs

```bash
# Verify outputs exist on S3
aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 ls \
    s3://braingeneers/ephys/<UUID>/derived/kilosort2/

# Download provenance for timing details
aws --endpoint https://s3.braingeneers.gi.ucsc.edu s3 cp \
    s3://braingeneers/ephys/<UUID>/derived/kilosort2/<name>_provenance.json .
cat *_provenance.json | python -m json.tool
```

## Using the Dashboard Status Page

1. Open SpikeCanvas dashboard
2. Navigate to **Status** page
3. Click **Refresh** to query K8s
4. Review pod status cards for each `edp-` prefixed job

## Cleanup Failed Jobs

```bash
# Delete a failed job
kubectl delete job <job-name> -n braingeneers

# Delete all completed/failed pipeline jobs (use with caution)
kubectl delete jobs -n braingeneers -l app=ephys-pipeline --field-selector status.successful=0
```
