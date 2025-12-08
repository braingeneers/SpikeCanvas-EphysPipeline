# SpikeCanvas Services - Docker Compose Setup

Quick start guide for running SpikeCanvas services using Docker Compose.

## What's Included

This docker-compose.yml provides a complete, self-contained setup with:

- **Maxwell Dashboard**: Web UI at http://localhost:8050
- **Spike Sorting Listener**: Job orchestration service
- **Job Scanner**: Kubernetes job monitor
- **MQTT Broker**: Message broker (Mosquitto)
- **Redis**: State persistence and caching

## Quick Start

```bash
# 1. Configure environment
cp .env.template .env
nano .env  # Edit with your settings

# 2. Start services
docker-compose up -d

# 3. Access dashboard
open http://localhost:8050
```

## Minimum Configuration

Edit `.env` with these required settings:

```bash
# Your S3 bucket
S3_BUCKET=your-bucket-name

# AWS credentials (choose one method)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
# OR
AWS_PROFILE=your-profile

# Kubernetes namespace
NRP_NAMESPACE=default

# For non-AWS S3 (MinIO, Ceph, etc)
ENDPOINT_URL=https://your-s3-endpoint
```

## Common Commands

```bash
# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart service
docker-compose restart dashboard

# Stop everything
docker-compose down

# Update images
docker-compose pull
docker-compose up -d
```

## Prerequisites

- Docker and Docker Compose installed
- Kubernetes cluster access (`~/.kube/config`)
- S3-compatible storage (AWS S3, MinIO, Ceph, etc.)
- AWS credentials configured

## Complete Documentation

See [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md) for:
- Detailed setup instructions
- Configuration options
- Troubleshooting guide
- Production deployment recommendations
- Security hardening steps

## Ports

- `8050` - Dashboard web interface
- `1883` - MQTT broker (MQTT protocol)
- `9001` - MQTT WebSocket
- `6379` - Redis

## Architecture

```
Browser → Dashboard (:8050)
            ↓
         MQTT Broker (:1883)
            ↓
         Listener → Kubernetes Jobs → S3 Storage
            ↓
         Scanner → Job Status Updates
```

## Troubleshooting

**Dashboard won't start**
```bash
docker-compose logs dashboard
# Check S3 credentials in .env
```

**Can't connect to Kubernetes**
```bash
kubectl get nodes  # Test kubectl access
# Verify ~/.kube/config is mounted correctly
```

**MQTT connection refused**
```bash
docker-compose ps mqtt  # Check MQTT is running
docker-compose restart mqtt
```

## Getting Help

1. Check logs: `docker-compose logs -f [service]`
2. View configuration: `docker-compose config`
3. See [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md)
4. GitHub Issues: https://github.com/braingeneers/maxwell_ephys_pipeline/issues

## Next Steps

1. Access dashboard at http://localhost:8050
2. Upload data to S3
3. Submit processing jobs
4. Monitor job progress
5. Download results

---

For production deployment, see [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md)
