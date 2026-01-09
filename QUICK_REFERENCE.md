# Standalone Deployment - Quick Reference Card

**Save this for quick access to common commands and configurations**

---

## 🚀 Quick Start (4 Commands)

```bash
cp .env.template .env && nano .env    # Configure S3 and K8s
docker-compose up -d                   # Start all services
docker-compose ps                      # Verify services are running
open http://localhost:8050             # Access dashboard
```

---

## 📋 Essential Environment Variables

**Minimum Required in `.env`:**

```bash
# S3 Storage
S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Kubernetes
NRP_NAMESPACE=your-k8s-namespace

# For MinIO/Ceph (not AWS S3):
ENDPOINT_URL=https://storage.yourlab.edu
```

---

## 🔧 Common Commands

### Service Management
```bash
docker-compose up -d              # Start services
docker-compose down               # Stop services
docker-compose restart            # Restart all
docker-compose restart listener   # Restart one service
docker-compose ps                 # Check status
```

### View Logs
```bash
docker-compose logs -f            # All services
docker-compose logs -f dashboard  # Dashboard only
docker-compose logs -f listener   # Listener only
docker-compose logs -f scanner    # Scanner only
docker-compose logs -f mqtt       # MQTT broker
docker-compose logs -f redis      # Redis
```

### Update Services
```bash
docker-compose pull               # Pull latest images
docker-compose up -d              # Apply updates
```

### Access Containers
```bash
docker-compose exec dashboard sh  # Shell in dashboard
docker-compose exec listener sh   # Shell in listener
docker-compose exec mqtt sh       # Shell in MQTT broker
docker-compose exec redis sh      # Shell in Redis
```

---

## 🧪 Quick Tests

### Test MQTT
```bash
# Subscribe to test topic
docker-compose exec mqtt mosquitto_sub -t test -C 1 &

# Publish to test topic
docker-compose exec mqtt mosquitto_pub -t test -m "hello"
```

### Test Redis
```bash
docker-compose exec redis redis-cli ping
# Expected: PONG
```

### Test Dashboard
```bash
curl http://localhost:8050
# OR open in browser
```

### Test kubectl Access
```bash
docker-compose exec listener kubectl get nodes
docker-compose exec listener kubectl get pods -n your-namespace
```

### Test S3 Access
```bash
docker-compose exec dashboard aws s3 ls s3://your-bucket/
docker-compose exec listener aws s3 ls s3://your-bucket/
```

---

## 🌐 Service Endpoints

| Service | Internal URL | External Port |
|---------|-------------|---------------|
| Dashboard | http://dashboard:8050 | 8050 |
| MQTT Broker | mqtt://mqtt:1883 | 1883 |
| MQTT WebSocket | ws://mqtt:9001 | 9001 |
| Redis | redis://redis:6379 | 6379 |

**Access Dashboard from Browser:**
- Local: http://localhost:8050
- Remote: http://your-server-ip:8050

---

## 📊 Health Checks

```bash
# Quick health check all services
docker-compose ps

# Detailed health status
docker inspect maxwell-mqtt | grep -A 5 "Health"
docker inspect maxwell-redis | grep -A 5 "Health"

# Service-specific checks
docker-compose exec mqtt mosquitto_sub -t "$$SYS/#" -C 1
docker-compose exec redis redis-cli ping
curl http://localhost:8050/health  # If implemented
```

---

## 🐛 Quick Troubleshooting

### No UUIDs in Dashboard
```bash
# Check S3 access
docker-compose exec dashboard aws s3 ls s3://your-bucket/ephys/

# Check logs
docker-compose logs dashboard | grep -i error
```

### Jobs Not Creating
```bash
# Check kubectl access
docker-compose exec listener kubectl get nodes

# Check listener logs
docker-compose logs listener | grep -i error

# Check MQTT connection
docker-compose logs listener | grep -i "mqtt"
```

### Service Won't Start
```bash
# Check logs
docker-compose logs service-name

# Check port conflicts
sudo netstat -tuln | grep -E "1883|9001|6379|8050"

# Restart individual service
docker-compose restart service-name
```

### View Recent Errors
```bash
docker-compose logs --tail=50 | grep -i error
docker-compose logs --tail=50 listener | grep -i error
```

---

## 🔐 Security Quick Commands

### MQTT Authentication (Production)
```bash
# Create password file
docker-compose exec mqtt mosquitto_passwd -c /mosquitto/config/passwd admin

# Reload config
docker-compose restart mqtt
```

### Redis Password (Production)
```bash
# Edit docker-compose.yml:
# redis:
#   command: redis-server --requirepass your-password

# Restart Redis
docker-compose restart redis
```

### Secure .env File
```bash
chmod 600 .env
```

---

## 📦 S3 Quick Operations

### List Data
```bash
aws s3 ls s3://your-bucket/ephys/
aws s3 ls s3://your-bucket/ephys/2024-01-15-e-12345/
```

### Upload Data
```bash
aws s3 cp recording.raw.h5 s3://your-bucket/ephys/uuid/original/data/
```

### Sync Parameters
```bash
aws s3 sync Services/parameters/ s3://your-bucket/services/mqtt_job_listener/params/
```

### Download Results
```bash
aws s3 cp s3://your-bucket/ephys/uuid/derived/kilosort2/ ./results/ --recursive
```

---

## ☸️ Kubernetes Quick Commands

### Check Jobs
```bash
kubectl get jobs -n your-namespace
kubectl get pods -n your-namespace
kubectl logs -n your-namespace job/job-name
```

### Delete Failed Jobs
```bash
kubectl delete job -n your-namespace job-name
```

### Check Job Status
```bash
kubectl get job -n your-namespace job-name -o yaml
```

---

## 📁 Important File Locations

| File | Purpose |
|------|---------|
| `.env` | Main configuration |
| `docker-compose.yml` | Service orchestration |
| `mosquitto/config/mosquitto.conf` | MQTT configuration |
| `Services/parameters/` | Algorithm parameters |
| `~/.kube/config` | Kubernetes credentials |

---

## 🔄 Update Configuration

```bash
# 1. Edit .env
nano .env

# 2. Restart services
docker-compose restart

# 3. Verify changes
docker-compose exec dashboard printenv | grep S3_BUCKET
```

---

## 📚 Documentation Links

- **Complete Guide**: [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md)
- **Quick Reference**: [DOCKER_COMPOSE_README.md](./DOCKER_COMPOSE_README.md)
- **MQTT Setup**: [mosquitto/config/README.md](./mosquitto/config/README.md)
- **Setup Checklist**: [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
- **Summary**: [DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md)

---

## 🆘 Getting Help

1. **Check logs**: `docker-compose logs`
2. **Review docs**: See links above
3. **Run health checks**: See Health Checks section
4. **Open issue**: https://github.com/braingeneers/SpikeCanvas-EphysPipeline/issues

---

## ⚡ Performance Tips

```bash
# Allocate more memory to Docker (edit Docker Desktop settings)
# Or for docker daemon:
# /etc/docker/daemon.json
{
  "default-shm-size": "2G"
}

# Clean up Docker resources
docker system prune -a
docker volume prune

# Monitor resource usage
docker stats
```

---

## 🎯 Common Workflows

### Process New Dataset
1. Upload to S3: `aws s3 cp data.raw.h5 s3://bucket/ephys/uuid/original/data/`
2. Open dashboard: http://localhost:8050
3. Select UUID from dropdown
4. Configure pipeline
5. Submit job
6. Monitor: `docker-compose logs -f listener`
7. Check results: `aws s3 ls s3://bucket/ephys/uuid/derived/`

### View Job Status
1. Open dashboard: http://localhost:8050
2. Or check Kubernetes: `kubectl get jobs -n namespace`
3. Or check logs: `docker-compose logs scanner`

### Restart After Configuration Change
1. Edit `.env`
2. Run: `docker-compose restart`
3. Verify: `docker-compose ps`

---

**Version**: 1.0 | **Last Updated**: January 2025  
**Repository**: https://github.com/braingeneers/SpikeCanvas-EphysPipeline

---

### 💡 Remember

- Always check logs first when troubleshooting
- Keep .env file secure (chmod 600)
- Test with small datasets first
- Monitor disk space for MQTT logs and Redis data
- Review STANDALONE_DEPLOYMENT.md for production hardening

---

**Print this page or bookmark for quick reference! 🔖**
