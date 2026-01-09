# Standalone Deployment - Implementation Summary

## What Was Created

This standalone deployment package allows any lab to run the SpikeCanvas services independently, without depending on Braingeneers infrastructure.

### New Files Created

1. **docker-compose.yml** (400+ lines)
   - Complete service orchestration configuration
   - Services: MQTT broker, Redis, Dashboard, Listener, Scanner
   - Health checks, dependencies, volumes, networking
   - Production-ready with extensive documentation

2. **.env.template** (250+ lines)
   - Comprehensive configuration template
   - Examples for AWS S3, MinIO, and Ceph
   - Security best practices and warnings
   - Troubleshooting tips

3. **mosquitto/config/mosquitto.conf**
   - MQTT broker configuration
   - Development settings (anonymous access)
   - Production security guidelines (commented)

4. **mosquitto/config/README.md**
   - Complete MQTT setup guide
   - Authentication and SSL/TLS configuration
   - Testing and monitoring procedures

5. **STANDALONE_DEPLOYMENT.md** (800+ lines)
   - Comprehensive deployment guide
   - Prerequisites and quick start
   - Detailed S3 setup (AWS, MinIO, Ceph)
   - Kubernetes configuration
   - Testing procedures
   - Troubleshooting (50+ common issues)
   - Production hardening
   - High availability setup
   - Monitoring and alerting
   - Backup and recovery
   - Scaling recommendations

6. **DOCKER_COMPOSE_README.md**
   - Quick reference guide
   - Common commands
   - Port configuration
   - Quick troubleshooting

### Updated Files

1. **README.md**
   - Updated maxtwo_splitter location (Services/ → Algorithms/)
   - Replaced old incomplete Docker Compose section with concise deployment options
   - Added clear references to new documentation
   - Split Quick Start into two deployment paths: Standalone vs Braingeneers

2. **.gitignore**
   - Added runtime files (mosquitto/data, mosquitto/log, .env)
   - Added Docker volume directories
   - Added log files

## Architecture Transformation

### Before: Braingeneers Mission Control (Complex)
```
mission_control docker-compose.yml (766 lines, 30+ services)
├── mqtt (external Braingeneers broker)
├── redis (external)
├── secret-fetcher (Braingeneers-specific)
├── nginx-proxy (SSL termination)
├── oauth2-proxy (Authentication layer)
├── letsencrypt (Certificate management)
├── service-proxy (Reverse proxy)
├── maxwell-dash
├── job-launcher
├── and 20+ other services...
```

### After: Standalone Deployment (Simple)
```
docker-compose.yml (400 lines, 5 services)
├── mqtt (local Mosquitto broker)
├── redis (local Redis)
├── dashboard (Maxwell Dashboard)
├── listener (Spike Sorting Listener)
└── scanner (Job Scanner)
```

**Key Simplifications:**
- ✅ Removed secret-fetcher (use .env instead)
- ✅ Removed oauth2-proxy (simplified for lab use)
- ✅ Removed nginx-proxy (direct port access)
- ✅ Removed letsencrypt (optional SSL in production)
- ✅ Added local MQTT broker (no external dependency)
- ✅ Added local Redis (optional, for state persistence)
- ✅ Self-contained configuration (all in .env)

## Service Communication

```
User
  ↓
Maxwell Dashboard (localhost:8050)
  ↓ (publishes job requests)
MQTT Broker (port 1883)
  ↓ (listens for jobs)
Spike Sorting Listener
  ↓ (creates K8s jobs)
Kubernetes Cluster
  ↓ (runs algorithms)
Algorithm Containers (Kilosort, Curation, etc.)
  ↓ (read/write data)
S3 Storage (AWS, MinIO, or Ceph)
```

## Configuration Workflow

1. **User configures `.env`**
   - S3 bucket and credentials
   - Kubernetes namespace
   - Optional: MQTT/Redis settings

2. **Services start via docker-compose**
   - Health checks ensure MQTT and Redis are ready
   - Dashboard, Listener, Scanner wait for dependencies

3. **User submits job via Dashboard**
   - Dashboard publishes MQTT message
   - Listener receives message and creates K8s job
   - Scanner monitors job status

4. **Algorithm runs on Kubernetes**
   - Downloads data from S3
   - Processes data
   - Uploads results to S3

5. **Dashboard shows results**
   - Scanner updates job status
   - User views/downloads processed data

## Storage Options Supported

### AWS S3
```bash
S3_BUCKET=my-lab-data
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-west-2
```

### MinIO (Self-Hosted)
```bash
S3_BUCKET=ephys-data
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
ENDPOINT_URL=http://minio.mylab.edu:9000
S3_ENDPOINT=minio.mylab.edu:9000
```

### Ceph (Institutional Storage)
```bash
S3_BUCKET=lab-storage
AWS_ACCESS_KEY_ID=<ceph-access-key>
AWS_SECRET_ACCESS_KEY=<ceph-secret-key>
ENDPOINT_URL=https://storage.university.edu
S3_ENDPOINT=storage.university.edu
```

## Deployment Comparison

| Feature | Braingeneers Platform | Standalone Deployment |
|---------|----------------------|----------------------|
| **Setup Complexity** | Request access from admins | Configure .env and run docker-compose |
| **Infrastructure** | Shared with Braingeneers | Your own hardware/cloud |
| **Authentication** | OAuth2 (UCSC credentials) | None (local access) |
| **MQTT Broker** | mqtt.braingeneers.gi.ucsc.edu | Local Mosquitto |
| **S3 Storage** | s3.braingeneers.gi.ucsc.edu | Your own S3-compatible storage |
| **Kubernetes** | Nautilus/NRP cluster | Your own K8s cluster |
| **SSL/TLS** | Automatic (Let's Encrypt) | Optional (manual setup) |
| **Maintenance** | Managed by Braingeneers | You maintain |
| **Data Privacy** | Shared infrastructure | Complete control |
| **Cost** | Free (for collaborators) | Your infrastructure costs |

## Quick Start Commands

```bash
# 1. Clone repository
git clone https://github.com/braingeneers/SpikeCanvas-EphysPipeline.git
cd SpikeCanvas-EphysPipeline

# 2. Configure environment
cp .env.template .env
nano .env  # Edit S3_BUCKET, AWS credentials, etc.

# 3. Start services
docker-compose up -d

# 4. Verify services
docker-compose ps

# 5. View logs
docker-compose logs -f

# 6. Access dashboard
open http://localhost:8050

# 7. Stop services
docker-compose down
```

## Testing Checklist

- [ ] MQTT broker is accessible (port 1883)
- [ ] Redis is running (port 6379)
- [ ] Dashboard is accessible (http://localhost:8050)
- [ ] Listener can connect to MQTT
- [ ] Scanner can connect to MQTT and S3
- [ ] kubectl works from listener container
- [ ] S3 credentials are valid
- [ ] Can create test Kubernetes job
- [ ] Can list UUIDs in dashboard
- [ ] Can submit test job

## Production Hardening

Before deploying for production use, review:

1. **MQTT Security** (mosquitto/config/README.md)
   - Enable authentication
   - Configure ACLs
   - Enable SSL/TLS

2. **Redis Security**
   - Set Redis password
   - Bind to specific interface
   - Enable persistence

3. **Network Security**
   - Configure firewall rules
   - Restrict dashboard access
   - Use VPN for remote access

4. **Backup Strategy**
   - Redis data snapshots
   - S3 bucket versioning
   - MQTT configuration backup

5. **Monitoring**
   - MQTT broker metrics
   - Redis performance
   - Dashboard availability
   - Job success/failure rates

See [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md) for complete production recommendations.

## Support and Documentation

- **Quick Reference**: [DOCKER_COMPOSE_README.md](./DOCKER_COMPOSE_README.md)
- **Complete Guide**: [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md)
- **MQTT Setup**: [mosquitto/config/README.md](./mosquitto/config/README.md)
- **Main README**: [README.md](./README.md)

## Known Limitations

1. **No Built-in Authentication**: Unlike Braingeneers platform, standalone deployment has no OAuth2/authentication by default. Consider:
   - Using VPN for access
   - Setting up nginx with basic auth
   - Configuring MQTT authentication

2. **Manual Certificate Management**: SSL/TLS certificates must be manually configured (Let's Encrypt not included)

3. **No Automatic Scaling**: Unlike Braingeneers infrastructure, you must manually manage resources

4. **Single Point of Failure**: If the docker-compose host goes down, all services stop. For HA, see production deployment guide.

## Migration from Braingeneers

If you're currently using the Braingeneers platform and want to migrate:

1. **Export your data** from s3://braingeneers/ephys/
   ```bash
   aws s3 sync s3://braingeneers/ephys/ s3://your-bucket/ephys/
   ```

2. **Copy parameter files**
   ```bash
   aws s3 sync s3://braingeneers/services/mqtt_job_listener/params/ s3://your-bucket/services/mqtt_job_listener/params/
   ```

3. **Update job tracking CSVs** (optional)
   ```bash
   aws s3 sync s3://braingeneers/services/mqtt_job_listener/csvs/ s3://your-bucket/services/mqtt_job_listener/csvs/
   ```

4. **Configure .env** with your new S3 bucket

5. **Start services** and test with one dataset

## Success Criteria

Your standalone deployment is successful when:

✅ All 5 services are running and healthy
✅ Dashboard shows your datasets (UUIDs)
✅ You can submit a test job
✅ Listener creates Kubernetes job
✅ Algorithm container runs successfully
✅ Results appear in S3
✅ Dashboard shows completed job

## Next Steps

1. **Review** [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md) for detailed setup instructions
2. **Configure** your .env file with S3 and Kubernetes settings
3. **Start** services with `docker-compose up -d`
4. **Test** with a small dataset to validate configuration
5. **Monitor** logs and job status
6. **Harden** for production (authentication, SSL/TLS, monitoring)
7. **Scale** as needed based on usage patterns

---

**Created**: January 2025  
**Version**: 1.0  
**Repository**: https://github.com/braingeneers/SpikeCanvas-EphysPipeline  
**Branch**: beta
