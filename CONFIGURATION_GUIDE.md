# SpikeCanvas Configuration Guide

This guide explains how to configure and use the SpikeCanvas with your institution's S3 storage and credentials.

> ** New to the pipeline?** Start with [QUICK_START.md](QUICK_START.md) for a simple desktop setup using the interactive `configure.py` script. This guide is for advanced configuration, Kubernetes deployment, and developer integration.

## Table of Contents
- [Overview](#overview)
- [Quick Start for Deployment](#quick-start-for-deployment)
- [Configuration Methods](#configuration-methods)
- [Using Configuration in Code](#using-configuration-in-code)
- [Configuration Reference](#configuration-reference)
- [Testing Your Configuration](#testing-your-configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

The pipeline uses environment variables for configuration, allowing each institution to deploy with their own S3 buckets and credentials without modifying code. Configuration flows from a `.env` file through Docker Compose to all services and algorithm jobs.

### Configuration Flow

```
.env file (your institution's config)
  ↓
Docker Compose (loads and propagates env vars)
  ↓
Service Containers (dashboard, listener, scanner)
  ↓
Listener spawns Kubernetes jobs
  ↓
Algorithm Containers (kilosort2, connectivity, etc.)
  ↓
Access your institution's S3 bucket
```

---

## Quick Start for Deployment

### Step 1: Create Configuration File

```bash
cd SpikeCanvas-EphysPipeline
cp .env.template .env
```

### Step 2: Edit Configuration

```bash
vim .env
```

**Minimum required configuration:**

```bash
# S3 Storage
S3_BUCKET=your-institution-bucket    # e.g., ucdavis-neural
S3_PREFIX=ephys                      # Base path prefix

# AWS Credentials (choose ONE method)

# Method 1: Access Keys (not recommended for production)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-west-2

# Method 2: AWS Profile (uses ~/.aws/credentials)
# AWS_PROFILE=your-profile-name
```

### Step 3: Start Services

```bash
docker-compose up -d
```

### Step 4: Verify Deployment

```bash
# Check services are running
docker-compose ps

# View logs
docker-compose logs -f

# Access dashboard
open http://localhost:8050
```

---

## Configuration Methods

### 1. Docker Compose Deployment (Recommended)

**Use case**: Running services on a local server or VM

**Configuration file**: `.env` in the project root

**Example `.env`:**
```bash
S3_BUCKET=myinstitution-ephys
S3_PREFIX=ephys
AWS_PROFILE=myinstitution-prod
NRP_NAMESPACE=myinstitution-neural
SERVICE_ROOT=s3://myinstitution-ephys/services/mqtt_job_listener
PARAMETER_BUCKET=s3://myinstitution-ephys/services/mqtt_job_listener/params
```

**Start services:**
```bash
docker-compose up -d
```

### 2. Kubernetes Deployment

**Use case**: Running services in a Kubernetes cluster

**Configuration method**: ConfigMap + Environment Variables

**Example ConfigMap:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ephys-config
  namespace: your-namespace
data:
  S3_BUCKET: "myinstitution-ephys"
  S3_PREFIX: "ephys"
  SERVICE_ROOT: "s3://myinstitution-ephys/services/mqtt_job_listener"
  PARAMETER_BUCKET: "s3://myinstitution-ephys/services/mqtt_job_listener/params"
  NRP_NAMESPACE: "myinstitution-neural"
```

**Example Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dashboard
spec:
  template:
    spec:
      containers:
      - name: dashboard
        image: surygeng/dashboard:latest
        envFrom:
        - configMapRef:
            name: ephys-config
```

### 3. Direct Environment Variables

**Use case**: Local development or testing

**Set environment variables:**
```bash
export S3_BUCKET=myinstitution-ephys
export S3_PREFIX=ephys
export AWS_PROFILE=myinstitution-dev

# Run service locally
cd Services/MaxWell_Dashboard/src
python app.py
```

### 4. YAML Configuration File (Optional)

**Use case**: Complex configuration with multiple environments

**Create** `/app/config/pipeline.yaml`:
```yaml
bucket: myinstitution-ephys
prefix: ephys
input_prefix: ephys/raw
output_prefix: ephys/derived
region: us-west-2
```

**Note**: Environment variables override YAML settings.

---

## Using Configuration in Code

### For Service Developers (Dashboard, Listener, Scanner)

Services can import across the Services/ directory and read env vars directly.

#### Method 1: Direct Environment Variables (Simplest)

```python
import os

# Read configuration
s3_bucket = os.getenv("S3_BUCKET")
s3_prefix = os.getenv("S3_PREFIX", "ephys")  # default "ephys"
service_root = os.getenv("SERVICE_ROOT")

# Build paths
if s3_bucket:
    default_bucket = f"s3://{s3_bucket}/{s3_prefix.rstrip('/')}/"
    data_path = f"{default_bucket}{uuid}/original/data/"
    output_path = f"{default_bucket}{uuid}/derived/kilosort2/"
else:
    raise ValueError("S3_BUCKET not configured")

# Service paths
if service_root:
    csv_path = f"{service_root}/csvs/"
    params_path = f"{service_root}/params/"
```

#### Method 2: Using Config Helper (Advanced)

```python
from Services.common.config import load_config

# Load configuration (caches automatically)
cfg = load_config()

# Get root S3 path
root = cfg.root()
# Returns: "s3://myinstitution-ephys/ephys/"

# Build standardized paths
data_path = cfg.s3_uri(uuid, 'original', 'data', 'recording.raw.h5')
# Returns: "s3://myinstitution-ephys/ephys/{uuid}/original/data/recording.raw.h5"

output_path = cfg.s3_uri(uuid, 'derived', 'kilosort2')
# Returns: "s3://myinstitution-ephys/ephys/{uuid}/derived/kilosort2/"

# Access configuration values
bucket = cfg.bucket
prefix = cfg.prefix
region = cfg.region
```

#### Example: Dashboard Usage

```python
# Services/MaxWell_Dashboard/src/values.py
import os

# Read from environment
_s3_bucket = os.getenv("S3_BUCKET")
_s3_prefix = os.getenv("S3_PREFIX", "ephys")

# Build default bucket path
if _s3_bucket:
    DEFAULT_BUCKET = f"s3://{_s3_bucket}/{_s3_prefix.rstrip('/')}/"
else:
    DEFAULT_BUCKET = None

# Service paths
SERVICE_ROOT = os.getenv("SERVICE_ROOT")
if SERVICE_ROOT:
    CSV_BUCKET = os.getenv("SERVICE_BUCKET", f"{SERVICE_ROOT}/csvs")
    PARAMETER_BUCKET = os.getenv("PARAMETER_BUCKET", f"{SERVICE_ROOT}/params")
elif _s3_bucket:
    CSV_BUCKET = f"s3://{_s3_bucket}/services/mqtt_job_listener/csvs"
    PARAMETER_BUCKET = f"s3://{_s3_bucket}/services/mqtt_job_listener/params"
else:
    CSV_BUCKET = None
    PARAMETER_BUCKET = None
```

### For Algorithm Developers (Containerized Processors)

Algorithms run in isolated containers and receive configuration via environment variables injected by the Listener.

#### Reading Configuration

```python
import os
import braingeneers.utils.s3wrangler as s3

# Environment variables are automatically injected by the Listener
s3_bucket = os.getenv("S3_BUCKET")
s3_prefix = os.getenv("S3_PREFIX", "ephys")
endpoint_url = os.getenv("ENDPOINT_URL")

# AWS credentials are also available (if configured)
aws_region = os.getenv("AWS_REGION")
aws_profile = os.getenv("AWS_PROFILE")

# Build paths
input_path = f"s3://{s3_bucket}/{s3_prefix}/{uuid}/original/data/recording.raw.h5"
output_path = f"s3://{s3_bucket}/{s3_prefix}/{uuid}/derived/kilosort2/"
```

#### Using with S3 Wrangler

```python
import braingeneers.utils.s3wrangler as s3
import os

# Configuration automatically used by s3wrangler
bucket = os.getenv("S3_BUCKET")
prefix = os.getenv("S3_PREFIX", "ephys")

# Load data (credentials from environment)
data = s3.load(f"s3://{bucket}/{prefix}/{uuid}/original/data/recording.raw.h5")

# Process data
result = process_data(data)

# Save output
output_path = f"s3://{bucket}/{prefix}/{uuid}/derived/kilosort2/output_phy.zip"
s3.save(result, output_path)
```

#### Example: Kilosort2 Algorithm

```python
# Algorithms/kilosort2_simplified/src/kilosort2_simplified.py
import os
import sys
import braingeneers.utils.s3wrangler as s3

def main(input_path, params_path):
    # Get S3 configuration from environment
    s3_bucket = os.getenv("S3_BUCKET")
    s3_prefix = os.getenv("S3_PREFIX", "ephys")
    
    print(f"Using S3 bucket: {s3_bucket}")
    print(f"Using S3 prefix: {s3_prefix}")
    
    # Load input data
    data = s3.load(input_path)
    params = s3.load(params_path)
    
    # Run spike sorting
    results = run_kilosort2(data, params)
    
    # Build output path
    uuid = extract_uuid(input_path)
    output_path = f"s3://{s3_bucket}/{s3_prefix}/{uuid}/derived/kilosort2/{uuid}_phy.zip"
    
    # Save results
    s3.save(results, output_path)
    print(f"Results saved to: {output_path}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

### For Listener Job Creation

The Listener automatically injects configuration into algorithm job specs.

#### How It Works

```python
# Services/Spike_Sorting_Listener/src/k8s_kilosort2.py

def create_job_object(self):
    # Build environment variables for the job
    job_env = [
        client.V1EnvVar(name="PYTHONUNBUFFERED", value='true'),
    ]
    
    # Inject S3 configuration
    if os.getenv("S3_BUCKET"):
        job_env.append(client.V1EnvVar(name="S3_BUCKET", value=os.getenv("S3_BUCKET")))
    if os.getenv("S3_PREFIX"):
        job_env.append(client.V1EnvVar(name="S3_PREFIX", value=os.getenv("S3_PREFIX")))
    
    # Inject S3 endpoint (for custom S3 providers)
    endpoint_url = os.getenv("ENDPOINT_URL", "https://s3.braingeneers.gi.ucsc.edu")
    s3_endpoint = os.getenv("S3_ENDPOINT", "s3.braingeneers.gi.ucsc.edu")
    job_env.extend([
        client.V1EnvVar(name="ENDPOINT_URL", value=endpoint_url),
        client.V1EnvVar(name="S3_ENDPOINT", value=s3_endpoint)
    ])
    
    # Inject AWS credentials (if present)
    for aws_var in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION",
                    "AWS_PROFILE", "AWS_ROLE_ARN", "AWS_SESSION_NAME"]:
        val = os.getenv(aws_var)
        if val:
            job_env.append(client.V1EnvVar(name=aws_var, value=val))
    
    # Create container with injected env vars
    container = client.V1Container(
        name="container",
        image=self.job_info["image"],
        env=job_env,  # Environment variables injected here
        # ... other container config
    )
```

**Result**: All algorithm containers automatically receive your S3 configuration without any code changes.

---

## Configuration Reference

### Core Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `S3_BUCKET` | **Yes** | None | Your institution's S3 bucket name (e.g., `ucdavis-neural`) |
| `S3_PREFIX` | No | `ephys` | Base path prefix within the bucket |
| `NRP_NAMESPACE` | No | `braingeneers` | Kubernetes namespace for algorithm jobs |

### AWS Credentials

Choose **ONE** authentication method:

#### Method 1: AWS Profile
- **Variables**: `AWS_PROFILE`
- **Setup**: Configure `~/.aws/credentials` on the host
- **Pros**: Multiple profile support, credentials outside code
- **Cons**: Requires volume mount of `~/.aws/` directory

#### Method 2: Access Keys
- **Variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- **Setup**: Add keys to `.env` file
- **Pros**: Simple to set up
- **Cons**: Keys in plaintext, manual rotation, security risk

### Service Storage Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_ROOT` | `s3://<S3_BUCKET>/services/mqtt_job_listener` | Base path for service data |
| `SERVICE_BUCKET` | `<SERVICE_ROOT>/csvs` | Job status CSV storage |
| `PARAMETER_BUCKET` | `<SERVICE_ROOT>/params` | Parameter file storage |

### S3 Endpoint Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENDPOINT_URL` | `https://s3.braingeneers.gi.ucsc.edu` | S3 API endpoint URL |
| `S3_ENDPOINT` | `s3.braingeneers.gi.ucsc.edu` | S3 endpoint hostname |

**Use cases**: MinIO, custom S3-compatible storage, private cloud

**Example for MinIO**:
```bash
ENDPOINT_URL=https://minio.myinstitution.edu
S3_ENDPOINT=minio.myinstitution.edu
```

### Algorithm Container Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KILOSORT_IMAGE` | `surygeng/kilosort_docker:v0.2` | Kilosort2 Docker image |
| `KILOSORT_RUN_ARGS` | None | Additional arguments for Kilosort |

### Resource Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `JOB_CPU_REQUEST` | `8` | CPU cores requested per job |
| `JOB_MEM_REQUEST` | `16Gi` | Memory requested per job |
| `JOB_EPHEMERAL_REQUEST` | `500Gi` | Ephemeral storage requested |
| `JOB_CPU_LIMIT` | `16` | Maximum CPU cores per job |
| `JOB_MEM_LIMIT` | `32Gi` | Maximum memory per job |
| `JOB_EPHEMERAL_LIMIT` | `1000Gi` | Maximum ephemeral storage |
| `JOB_GPU_LIMIT` | `1` | GPU allocation per job |

---

## Testing Your Configuration

### 1. Verify Environment Variables

```bash
# After starting with docker-compose
docker-compose exec dashboard env | grep S3_BUCKET
docker-compose exec listener env | grep S3_BUCKET
docker-compose exec scanner env | grep S3_BUCKET
```

### 2. Test S3 Access from Services

```bash
# Test from dashboard container
docker-compose exec dashboard python -c "
import os
import braingeneers.utils.s3wrangler as s3
bucket = os.getenv('S3_BUCKET')
prefix = os.getenv('S3_PREFIX', 'ephys')
print(f'Bucket: {bucket}')
print(f'Prefix: {prefix}')
# List UUIDs
try:
    uuids = s3.ls(f's3://{bucket}/{prefix}/')
    print(f'Found {len(uuids)} UUIDs')
except Exception as e:
    print(f'Error: {e}')
"
```

### 3. Check Configuration in Logs

```bash
# Dashboard startup should show configuration
docker-compose logs dashboard | grep -i "bucket\|s3"

# Listener should show S3 configuration
docker-compose logs listener | grep -i "s3_bucket"
```

### 4. Verify Algorithm Job Configuration

Submit a test job through the dashboard, then check if the algorithm job received configuration:

```bash
# List recent jobs
kubectl get jobs -n <your-namespace> --sort-by=.metadata.creationTimestamp

# Check environment variables in job pod
kubectl get pods -n <your-namespace> | grep <job-name>
kubectl logs -n <your-namespace> <pod-name> | grep -i "s3_bucket\|bucket:"

# Describe job to see env vars
kubectl describe job -n <your-namespace> <job-name> | grep -A 20 "Environment:"
```

### 5. End-to-End Test

1. **Prepare test data** in your S3 bucket:
   ```bash
   aws s3 cp test_recording.raw.h5 s3://your-bucket/ephys/test-uuid/original/data/
   ```

2. **Submit job** via dashboard:
   - Select the test UUID
   - Choose Kilosort2
   - Submit job

3. **Monitor job execution**:
   ```bash
   kubectl logs -f -n <your-namespace> <job-pod-name>
   ```

4. **Verify output** in S3:
   ```bash
   aws s3 ls s3://your-bucket/ephys/test-uuid/derived/kilosort2/
   ```

---

## Troubleshooting

### Issue: Dashboard shows no UUIDs

**Symptoms**: Dashboard dropdown is empty or shows error

**Causes**:
1. `S3_BUCKET` not set in `.env`
2. AWS credentials invalid or missing
3. No data in the bucket
4. Incorrect S3 prefix

**Solutions**:
```bash
# 1. Check configuration
docker-compose exec dashboard env | grep S3_BUCKET

# 2. Test S3 access manually
docker-compose exec dashboard python -c "
import braingeneers.utils.s3wrangler as s3
import os
bucket = os.getenv('S3_BUCKET')
prefix = os.getenv('S3_PREFIX', 'ephys')
try:
    result = s3.ls(f's3://{bucket}/{prefix}/')
    print(f'Success! Found: {result}')
except Exception as e:
    print(f'Error: {e}')
    print('Check bucket name, credentials, and network access')
"

# 3. Check dashboard logs for errors
docker-compose logs dashboard | tail -50
```

### Issue: Algorithm jobs fail with S3 access errors

**Symptoms**: Job logs show "NoCredentialsError" or "Access Denied"

**Causes**:
1. Listener not injecting credentials properly
2. Kubernetes cluster can't reach S3
3. Access keys expired

**Solutions**:
```bash
# 1. Verify listener has credentials
docker-compose exec listener env | grep AWS_

# 2. Check job received env vars
kubectl describe job -n <namespace> <job-name> | grep -A 30 "Environment:"

# 3. Test S3 access from a test pod in the cluster
kubectl run test-s3 --rm -it --image=amazon/aws-cli -- s3 ls s3://your-bucket/

# 4. Review listener injection code
docker-compose logs listener | grep -i "inject\|env"
```

### Issue: Configuration changes not taking effect

**Symptoms**: After editing `.env`, services still use old values

**Solution**:
```bash
# Restart services to reload .env
docker-compose restart

# Or recreate containers
docker-compose down
docker-compose up -d

# Verify new values loaded
docker-compose exec dashboard env | grep S3_BUCKET
```

### Issue: Permission denied errors

**Symptoms**: "403 Forbidden" or "Access Denied" in logs

**Causes**:
1. S3 permissions too restrictive
2. Wrong AWS credentials
3. Bucket policy blocks access

**Solutions**:
```bash
# 1. Test with AWS CLI using same credentials
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
aws s3 ls s3://your-bucket/ephys/

# 2. Check S3 permissions:
# - s3:GetObject
# - s3:PutObject
# - s3:ListBucket

# 3. Verify bucket policy allows your access
```

### Issue: Jobs submit but don't start

**Symptoms**: Job appears in dashboard but no Kubernetes pod created

**Causes**:
1. kubectl not configured in listener container
2. Wrong Kubernetes namespace
3. Insufficient cluster resources
4. RBAC permissions missing

**Solutions**:
```bash
# 1. Check listener can access Kubernetes
docker-compose exec listener kubectl get nodes

# 2. Verify namespace exists
kubectl get namespace <NRP_NAMESPACE>

# 3. Check job status
kubectl get jobs -n <NRP_NAMESPACE>
kubectl describe job -n <NRP_NAMESPACE> <job-name>

# 4. Review listener logs
docker-compose logs listener | grep -i "kubernetes\|job\|error"
```

### Issue: MinIO or custom S3 endpoint not working

**Symptoms**: "Unable to locate credentials" or connection timeout

**Solutions**:
```bash
# 1. Verify endpoint configuration in .env
ENDPOINT_URL=https://minio.example.com
S3_ENDPOINT=minio.example.com

# 2. Test endpoint accessibility
curl https://minio.example.com

# 3. Test with s3wrangler
docker-compose exec dashboard python -c "
import os
os.environ['ENDPOINT_URL'] = 'https://minio.example.com'
import braingeneers.utils.s3wrangler as s3
s3.ls('s3://your-bucket/')
"
```

---

## Configuration Examples

### Example 1: UC Davis Deployment

```bash
# .env
S3_BUCKET=ucdavis-neural-data
S3_PREFIX=ephys
AWS_PROFILE=ucdavis-production
AWS_REGION=us-west-2
NRP_NAMESPACE=ucdavis-neural-lab
SERVICE_ROOT=s3://ucdavis-neural-data/services/mqtt_job_listener
PARAMETER_BUCKET=s3://ucdavis-neural-data/services/mqtt_job_listener/params
JOB_CPU_REQUEST=12
JOB_MEM_REQUEST=24Gi
JOB_GPU_LIMIT=1
```

### Example 2: MinIO Private Cloud

```bash
# .env
S3_BUCKET=ephys-data
S3_PREFIX=ephys
ENDPOINT_URL=https://minio.institution.edu
S3_ENDPOINT=minio.institution.edu
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin-password
NRP_NAMESPACE=ephys-processing
SERVICE_ROOT=s3://ephys-data/services
PARAMETER_BUCKET=s3://ephys-data/services/params
```

### Example 3: AWS with Access Keys

**Environment**: Running on AWS with access keys

```bash
# .env
S3_BUCKET=institution-ephys-prod
S3_PREFIX=ephys
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_REGION=us-east-1
NRP_NAMESPACE=ephys-prod
```

### Example 4: Development Environment

```bash
# .env
S3_BUCKET=dev-ephys-bucket
S3_PREFIX=ephys-dev
AWS_PROFILE=dev-profile
AWS_REGION=us-west-2
NRP_NAMESPACE=dev-namespace
SERVICE_ROOT=s3://dev-ephys-bucket/services
JOB_CPU_REQUEST=4
JOB_MEM_REQUEST=8Gi
JOB_GPU_LIMIT=0  # No GPU for dev
```

---

## Best Practices

### Security
1. **Rotate credentials** regularly
2. **Restrict S3 permissions** to minimum required (GetObject, PutObject, ListBucket)
3. **Keep `.env` secure** - add to `.gitignore`, use chmod 600
4. **Use separate buckets** for production vs. development

### Configuration Management
1. **Document your configuration** - keep notes on what each value means for your setup
2. **Version control `.env.template`** but never `.env` (contains secrets)
3. **Use consistent naming** - follow the same prefix convention across all institutions
4. **Test configuration changes** in development before production

### Deployment
1. **Validate configuration** before starting services
2. **Monitor logs** on first deployment to catch configuration errors early
3. **Start with one test job** before processing large datasets
4. **Keep backups** of working `.env` files

### Maintenance
1. **Review logs regularly** for configuration-related warnings
2. **Update documentation** when adding new configuration options
3. **Test disaster recovery** - can you redeploy from your `.env` backup?

---

## Additional Resources

- **Main README**: `README.md` - General pipeline documentation
- **Docker Compose Template**: `docker-compose.yml` - Service orchestration
- **Configuration Template**: `.env.template` - All available options
- **Config Helper Source**: `Services/common/config.py` - Advanced configuration API
- **Listener Source**: `Services/Spike_Sorting_Listener/src/k8s_kilosort2.py` - Job creation and env injection

---

## Support

If you encounter issues not covered in this guide:

1. **Check logs**: `docker-compose logs <service-name>`
2. **Review test results**: Run the testing commands in the "Testing Your Configuration" section
3. **GitHub Issues**: Report bugs or request features
4. **Community**: Braingeneers Slack or GitHub Discussions

---

**Last Updated**: November 25, 2025
