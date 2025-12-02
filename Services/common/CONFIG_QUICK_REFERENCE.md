# External Configuration - Quick Reference

## Three Ways to Configure

### 1. Environment Variables (Simplest)
```bash
docker run -e S3_BUCKET=my-bucket -e S3_PREFIX=ephys ...
```

### 2. YAML File (Recommended)
```bash
docker run -v ./pipeline.yaml:/app/config/pipeline.yaml ...
```

### 3. Hybrid (YAML + Env Override)
```bash
docker run -v ./pipeline.yaml:/app/config/pipeline.yaml -e S3_BUCKET=override ...
```

## Minimal YAML Configuration

```yaml
bucket: my-bucket-name
prefix: ephys
```

## Python API

```python
from Services.common.config import load_config, s3_uri

# Get root path
cfg = load_config()
root = cfg.root()  # "s3://bucket/prefix/"

# Build paths
path = cfg.s3_uri("uuid", "file.h5")  # "s3://bucket/prefix/uuid/file.h5"

# Use different bases
input_path = cfg.s3_uri("uuid", "data.h5", base="input")
output_path = cfg.s3_uri("uuid", "results", base="output")
```

## Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `S3_BUCKET` | Bucket name | `my-institution` |
| `S3_PREFIX` | Root prefix | `ephys` |
| `S3_INPUT_PREFIX` | Input override | `raw-data` |
| `S3_OUTPUT_PREFIX` | Output override | `processed` |
| `AWS_REGION` | AWS region | `us-west-2` |
| `PIPELINE_CONFIG` | Custom config path | `/custom/config.yaml` |

## Priority Order

1. Environment variables (highest)
2. YAML at `$PIPELINE_CONFIG`
3. YAML at `/app/config/pipeline.yaml`
4. YAML at `/config/pipeline.yaml`
5. Built-in defaults (lowest)

## Check Configuration

```bash
# View startup logs
docker logs <container> | grep pipeline-config

# Output example:
# [pipeline-config] bucket=my-bucket prefix=ephys input=None output=None
```

## Common Patterns

### University Deployment
```yaml
bucket: university-neuroscience
prefix: ephys-pipeline
input_prefix: raw-recordings
output_prefix: curated-results
```

### Shared Consortium Bucket
```yaml
bucket: consortium-data
prefix: institution-name/ephys
```

### Development/Production Split
```bash
# Dev
-e S3_BUCKET=dev-ephys -e S3_PREFIX=test

# Prod
-e S3_BUCKET=prod-ephys -e S3_PREFIX=ephys
```

## Troubleshooting

**Config not loading?**
- Check file mount path: `/app/config/pipeline.yaml`
- Verify file permissions (readable)
- Check logs for startup message

**Wrong bucket?**
- Remember: env vars override YAML
- Check which config source is active
- Look for `[pipeline-config]` log message

**Access denied?**
- Mount AWS credentials: `-v ~/.aws:/root/.aws:ro`
- Verify bucket permissions

## See Full Documentation

- `CONFIG_USAGE_GUIDE.md` - Complete usage guide
- `pipeline.yaml.example` - Example configuration file
- `config.py` - Source code with inline documentation
