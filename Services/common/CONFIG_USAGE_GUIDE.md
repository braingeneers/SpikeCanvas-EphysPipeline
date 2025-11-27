# External Configuration System - Usage Guide

## Overview

The external configuration system allows you to deploy the EphysPipeline with institution-specific S3 bucket configurations without modifying code. It supports both YAML configuration files and environment variables.

## Quick Start

### Method 1: Environment Variables Only (Simplest)

This is the current default method - no files needed:

```bash
docker run \
  -e S3_BUCKET=my-institution-bucket \
  -e S3_PREFIX=ephys \
  -p 8050:8050 \
  surygeng/maxwell_dashboard:latest
```

### Method 2: YAML Configuration File (Recommended for Complex Setups)

1. Create a `pipeline.yaml` file:

```yaml
# pipeline.yaml
bucket: my-institution-bucket
prefix: neuroscience/ephys
input_prefix: raw-data
output_prefix: processed-results
region: us-west-2
```

2. Mount it into the container:

```bash
docker run \
  -v /path/to/pipeline.yaml:/app/config/pipeline.yaml \
  -p 8050:8050 \
  surygeng/maxwell_dashboard:latest
```

### Method 3: Hybrid (YAML + Environment Overrides)

Environment variables always override YAML settings:

```bash
docker run \
  -v /path/to/pipeline.yaml:/app/config/pipeline.yaml \
  -e S3_BUCKET=override-bucket \
  -p 8050:8050 \
  surygeng/maxwell_dashboard:latest
```

## Configuration Options

### YAML Configuration File

```yaml
# S3 Bucket Configuration
bucket: my-bucket-name           # Required: S3 bucket name (without s3:// prefix)
prefix: ephys                    # Optional: Root prefix within bucket (default: "ephys")
input_prefix: raw-data           # Optional: Override for input data location
output_prefix: processed-data    # Optional: Override for output data location

# AWS Credentials (optional)
region: us-west-2                # AWS region
profile: my-aws-profile          # AWS profile name
role_arn: arn:aws:iam::...       # AWS role ARN for cross-account access
session_name: pipeline-session   # Session name for assumed role
```

### Environment Variables

All YAML options can be set via environment variables:

| Environment Variable | Description | Example |
|---------------------|-------------|---------|
| `S3_BUCKET` | S3 bucket name | `my-institution-bucket` |
| `S3_PREFIX` | Root prefix | `ephys` |
| `S3_INPUT_PREFIX` | Input data prefix | `raw-data` |
| `S3_OUTPUT_PREFIX` | Output data prefix | `processed-data` |
| `AWS_REGION` | AWS region | `us-west-2` |
| `AWS_PROFILE` | AWS profile | `default` |
| `AWS_ROLE_ARN` | Role ARN | `arn:aws:iam::123456789:role/...` |
| `AWS_SESSION_NAME` | Session name | `pipeline-session` |
| `PIPELINE_CONFIG` | Custom config file path | `/custom/path/pipeline.yaml` |

### Configuration Priority (Highest to Lowest)

1. **Environment variables** - Always take precedence
2. **YAML file at `$PIPELINE_CONFIG`** - Custom path if specified
3. **YAML file at `/app/config/pipeline.yaml`** - Standard container location
4. **YAML file at `/config/pipeline.yaml`** - Alternative location
5. **Built-in defaults** - If nothing else is configured

## Programming API

### In Python Code

```python
from Services.common.config import load_config, s3_uri

# Load configuration (cached after first call)
cfg = load_config()

# Get the root S3 path
root_path = cfg.root()
# Returns: "s3://my-bucket/ephys/"

# Build S3 URIs with path components
data_path = cfg.s3_uri("uuid-123", "experiment-1", "data.h5")
# Returns: "s3://my-bucket/ephys/uuid-123/experiment-1/data.h5"

# Use different base prefixes
input_path = cfg.s3_uri("uuid-123", "raw.h5", base="input")
# Returns: "s3://my-bucket/raw-data/uuid-123/raw.h5"

output_path = cfg.s3_uri("uuid-123", "results", base="output")
# Returns: "s3://my-bucket/processed-data/uuid-123/results"

# Access individual config values
print(f"Bucket: {cfg.bucket}")
print(f"Prefix: {cfg.prefix}")
print(f"Region: {cfg.region}")
```

### Convenience Function

```python
from Services.common.config import s3_uri

# Shorthand - automatically loads config
path = s3_uri("uuid-123", "data.h5", base="root")
```

### Force Reload Configuration

```python
from Services.common.config import load_config

# Force reload (useful if config file changes)
cfg = load_config(force_reload=True)
```

## Real-World Examples

### Example 1: University Deployment

**Scenario:** University of XYZ wants to use their own S3 bucket with separate input/output locations.

Create `pipeline.yaml`:
```yaml
bucket: xyz-neuroscience-data
prefix: ephys-pipeline
input_prefix: raw-recordings
output_prefix: analysis-results
region: us-east-1
```

Deploy:
```bash
docker-compose.yml:
  dashboard:
    image: surygeng/maxwell_dashboard:latest
    volumes:
      - ./pipeline.yaml:/app/config/pipeline.yaml
    ports:
      - "8050:8050"
```

### Example 2: Multi-Institution Shared Bucket

**Scenario:** Multiple institutions share one bucket but use different prefixes.

Institution A:
```bash
docker run \
  -e S3_BUCKET=shared-neuroscience \
  -e S3_PREFIX=institution-a/ephys \
  -p 8050:8050 \
  surygeng/maxwell_dashboard:latest
```

Institution B:
```bash
docker run \
  -e S3_BUCKET=shared-neuroscience \
  -e S3_PREFIX=institution-b/ephys \
  -p 8051:8050 \
  surygeng/maxwell_dashboard:latest
```

### Example 3: Development vs Production

**Development** (`dev-pipeline.yaml`):
```yaml
bucket: dev-ephys-data
prefix: test-runs
```

**Production** (`prod-pipeline.yaml`):
```yaml
bucket: prod-ephys-data
prefix: ephys
input_prefix: validated-inputs
output_prefix: curated-outputs
region: us-west-2
```

Deploy with different configs:
```bash
# Development
docker run -v ./dev-pipeline.yaml:/app/config/pipeline.yaml ...

# Production
docker run -v ./prod-pipeline.yaml:/app/config/pipeline.yaml ...
```

### Example 4: Cross-Account S3 Access

**Scenario:** Access S3 bucket in a different AWS account.

```yaml
bucket: other-account-bucket
prefix: ephys
region: us-west-2
role_arn: arn:aws:iam::987654321:role/CrossAccountS3Access
session_name: ephys-pipeline-session
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  dashboard:
    image: surygeng/maxwell_dashboard:latest
    ports:
      - "8050:8050"
    volumes:
      # Mount config file
      - ./config/pipeline.yaml:/app/config/pipeline.yaml
      # Optional: Mount AWS credentials
      - ~/.aws:/root/.aws:ro
    environment:
      # Optional: Override specific settings
      - S3_BUCKET=${S3_BUCKET:-my-default-bucket}
      - AWS_REGION=us-west-2
    restart: unless-stopped
```

Run with:
```bash
# Use default config
docker-compose up

# Override bucket via environment
S3_BUCKET=my-other-bucket docker-compose up
```

## Kubernetes ConfigMap Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pipeline-config
data:
  pipeline.yaml: |
    bucket: k8s-ephys-data
    prefix: ephys
    input_prefix: raw-data
    output_prefix: processed-data
    region: us-west-2
---
apiVersion: v1
kind: Pod
metadata:
  name: dashboard
spec:
  containers:
  - name: dashboard
    image: surygeng/maxwell_dashboard:latest
    ports:
    - containerPort: 8050
    volumeMounts:
    - name: config
      mountPath: /app/config
      readOnly: true
    env:
    - name: AWS_REGION
      value: "us-west-2"
  volumes:
  - name: config
    configMap:
      name: pipeline-config
```

## Troubleshooting

### Check What Configuration is Loaded

The configuration system prints a log message on startup:

```
[pipeline-config] bucket=my-bucket prefix=ephys input=raw-data output=processed-data
```

Look for this in your container logs:
```bash
docker logs <container-id> | grep pipeline-config
```

### Verify Configuration in Python

```python
from Services.common.config import load_config

cfg = load_config()
print(f"Bucket: {cfg.bucket}")
print(f"Root URI: {cfg.root()}")
print(f"Raw config: {cfg.raw}")
```

### Common Issues

**1. Config file not found**
- Ensure the file is mounted at `/app/config/pipeline.yaml`
- Check file permissions (must be readable)
- Verify the mount path in `docker run -v` or docker-compose.yml

**2. Environment variables not working**
- Check variable names (case-sensitive: `S3_BUCKET` not `s3_bucket`)
- Verify variables are exported in shell
- Check docker-compose environment section

**3. Bucket access denied**
- Verify AWS credentials are available (mount ~/.aws or use IAM role)
- Check bucket permissions and IAM policies
- Ensure region is correct if bucket has region restrictions

**4. Wrong bucket being used**
- Check configuration priority (env vars override YAML)
- Look for the startup log message to see what's actually loaded
- Use `force_reload=True` if config changed at runtime

## Migration from Hardcoded Values

### Before (Hardcoded)
```python
# Old code
bucket = "s3://braingeneers/ephys"
uuids = wr.list_directories(bucket)
```

### After (Configurable)
```python
# New code
from Services.common.config import load_config

cfg = load_config()
bucket = cfg.root()
uuids = wr.list_directories(bucket)
```

### Backward Compatibility

The system maintains backward compatibility:
- If no config is provided, falls back to `DEFAULT_BUCKET` (from env vars)
- Existing deployments continue to work without changes
- Config system is opt-in, not mandatory

## Best Practices

1. **Use YAML for Production** - Easier to version control and review
2. **Use Environment Variables for Development** - Quick testing and overrides
3. **Don't Commit Secrets** - Keep AWS credentials out of YAML files
4. **Validate Config Early** - Check logs for the configuration loaded message
5. **Use Separate Input/Output Prefixes** - Keeps raw and processed data organized
6. **Document Your Config** - Add comments to YAML files explaining choices

## Support

For issues or questions:
- Check container logs: `docker logs <container>`
- Review this guide
- Open an issue on GitHub: https://github.com/braingeneers/EphysPipeline/issues
