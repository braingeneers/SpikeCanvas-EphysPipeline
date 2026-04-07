---
description: How to submit a spike sorting job via the SpikeCanvas platform
---

# Submit a Sorting Job

## Via Dashboard (Preferred)

1. Open the SpikeCanvas dashboard (`http://127.0.0.1:8050` or production URL)
2. Navigate to **Job Center**
3. Enter a keyword in the UUID filter to narrow results
4. Select the UUID from the dropdown
5. Review the metadata display to confirm correct experiment
6. Select recordings from the checklist (or click "Select All")
7. Check **Ephys Pipeline (Kilosort2, Auto-Curation, Visualization)** under "Select job"
8. (Optional) Load or configure parameters
9. Click **Add to Job Table** to stage the jobs
10. Review the job table at the bottom of the page
11. Click **Export and Start Job** to submit

## Via MQTT (Programmatic)

```python
from braingeneers.iot import messaging
import uuid as uuidgen

# Create message broker
mb = messaging.MessageBroker(str(uuidgen.uuid4()))

# Build upload message
message = {
    "uuid": "<YOUR_UUID>",
    "ephys_experiments": {
        "experiment_name": {
            "blocks": [{"path": "original/data/<recording>.raw.h5"}],
            "data_format": "maxone"  # or "maxtwo" for MaxTwo
        }
    },
    "stitch": False,
    "overwrite": False
}

# Publish to trigger job creation
mb.publish_message(topic="experiments/upload", message=message)
```

## Via kubectl (Manual)

```bash
# 1. Edit the job manifest
#    Set metadata.name, S3 path in args, and image tag
vim Algorithms/ephys_pipeline/run_kilosort2.yaml

# 2. Submit the job
kubectl apply -f Algorithms/ephys_pipeline/run_kilosort2.yaml -n braingeneers

# 3. Monitor logs
kubectl logs -f job/<job-name> -n braingeneers
```

## Verification

After submission, verify the job was created:

```bash
# Check job exists
kubectl get jobs -n braingeneers | grep edp-

# Check pod is running
kubectl get pods -n braingeneers | grep edp-
```

Or use the Status page in the dashboard (click Refresh).
