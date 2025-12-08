# Standalone Deployment - Setup Checklist

Use this checklist to ensure your standalone deployment is configured correctly.

## Pre-Deployment Checklist

### Infrastructure Requirements

- [ ] **Docker** installed (version 20.10+)
  ```bash
  docker --version
  ```

- [ ] **Docker Compose** installed (version 1.29+)
  ```bash
  docker-compose --version
  ```

- [ ] **Kubernetes cluster** accessible
  ```bash
  kubectl get nodes
  ```

- [ ] **kubectl** configured with correct context
  ```bash
  kubectl config current-context
  kubectl get namespaces
  ```

- [ ] **S3-compatible storage** available (AWS S3, MinIO, or Ceph)
  ```bash
  aws s3 ls  # Test AWS credentials
  ```

### Configuration Files

- [ ] **`.env` file** created from template
  ```bash
  cp .env.template .env
  ```

- [ ] **S3_BUCKET** configured in .env
  ```bash
  grep "^S3_BUCKET=" .env
  ```

- [ ] **AWS credentials** configured (access keys OR profile)
  ```bash
  # Either these:
  grep "^AWS_ACCESS_KEY_ID=" .env
  grep "^AWS_SECRET_ACCESS_KEY=" .env
  # Or this:
  grep "^AWS_PROFILE=" .env
  ```

- [ ] **NRP_NAMESPACE** set to your Kubernetes namespace
  ```bash
  grep "^NRP_NAMESPACE=" .env
  kubectl get namespace $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2)
  ```

- [ ] **ENDPOINT_URL** set (if using MinIO or Ceph, not AWS S3)
  ```bash
  grep "^ENDPOINT_URL=" .env
  ```

### Network Requirements

- [ ] **Port 1883** available (MQTT)
  ```bash
  sudo netstat -tuln | grep 1883
  # Should show nothing if port is free
  ```

- [ ] **Port 9001** available (MQTT WebSocket)
  ```bash
  sudo netstat -tuln | grep 9001
  ```

- [ ] **Port 6379** available (Redis)
  ```bash
  sudo netstat -tuln | grep 6379
  ```

- [ ] **Port 8050** available (Dashboard)
  ```bash
  sudo netstat -tuln | grep 8050
  ```

- [ ] **Firewall configured** (if accessing remotely)
  ```bash
  # Example for Ubuntu/Debian
  sudo ufw status
  sudo ufw allow 8050/tcp  # Dashboard
  ```

### Data Requirements

- [ ] **S3 bucket exists**
  ```bash
  aws s3 ls s3://your-bucket/
  ```

- [ ] **S3 bucket has data** (or ready to upload)
  ```bash
  aws s3 ls s3://your-bucket/ephys/
  ```

- [ ] **Parameter files uploaded** to S3
  ```bash
  aws s3 sync Services/parameters/ s3://your-bucket/services/mqtt_job_listener/params/
  aws s3 ls s3://your-bucket/services/mqtt_job_listener/params/
  ```

## Deployment Checklist

### Start Services

- [ ] **Start all services**
  ```bash
  docker-compose up -d
  ```

- [ ] **Verify all services are running**
  ```bash
  docker-compose ps
  # Expected: 5 services (mqtt, redis, dashboard, listener, scanner)
  # All should show "Up" status
  ```

- [ ] **Check health status**
  ```bash
  docker-compose ps
  # mqtt and redis should show "healthy"
  ```

### Service Validation

- [ ] **MQTT broker is accessible**
  ```bash
  docker-compose exec mqtt mosquitto_sub -t test -C 1 &
  docker-compose exec mqtt mosquitto_pub -t test -m "hello"
  ```

- [ ] **Redis is accessible**
  ```bash
  docker-compose exec redis redis-cli ping
  # Expected: PONG
  ```

- [ ] **Dashboard is accessible**
  ```bash
  curl http://localhost:8050
  # OR open in browser: http://localhost:8050
  ```

- [ ] **Dashboard can list UUIDs** (if you have data in S3)
  - Open http://localhost:8050
  - Check if UUIDs appear in dropdown

- [ ] **Listener can connect to MQTT**
  ```bash
  docker-compose logs listener | grep -i "connected to mqtt"
  ```

- [ ] **Scanner can connect to MQTT**
  ```bash
  docker-compose logs scanner | grep -i "connected to mqtt"
  ```

### Kubernetes Integration

- [ ] **Listener has kubectl access**
  ```bash
  docker-compose exec listener kubectl get nodes
  # Should list your cluster nodes
  ```

- [ ] **Listener can access target namespace**
  ```bash
  docker-compose exec listener kubectl get pods -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2)
  ```

- [ ] **Listener can create jobs**
  ```bash
  docker-compose exec listener kubectl auth can-i create jobs -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2)
  # Expected: yes
  ```

### S3 Integration

- [ ] **Dashboard can access S3**
  ```bash
  docker-compose exec dashboard aws s3 ls s3://$(grep "^S3_BUCKET=" .env | cut -d= -f2)/
  ```

- [ ] **Listener can access S3**
  ```bash
  docker-compose exec listener aws s3 ls s3://$(grep "^S3_BUCKET=" .env | cut -d= -f2)/
  ```

- [ ] **Scanner can access S3**
  ```bash
  docker-compose exec scanner aws s3 ls s3://$(grep "^S3_BUCKET=" .env | cut -d= -f2)/
  ```

## Test Job Submission

### Submit a Test Job

- [ ] **Open dashboard** at http://localhost:8050

- [ ] **Select a UUID** from dropdown (requires data in S3)

- [ ] **Configure job** (select algorithms, set parameters)

- [ ] **Submit job**

- [ ] **Job appears in MQTT logs**
  ```bash
  docker-compose logs -f listener | grep "Received job request"
  ```

- [ ] **Kubernetes job is created**
  ```bash
  kubectl get jobs -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2)
  ```

- [ ] **Job completes successfully**
  ```bash
  kubectl get jobs -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2) --watch
  ```

- [ ] **Results appear in S3**
  ```bash
  aws s3 ls s3://$(grep "^S3_BUCKET=" .env | cut -d= -f2)/ephys/<uuid>/derived/
  ```

- [ ] **Dashboard shows completed status**
  - Refresh dashboard page
  - Check job status

## Troubleshooting Checklist

If something doesn't work, check these common issues:

### Services Won't Start

- [ ] Check Docker daemon is running
  ```bash
  sudo systemctl status docker
  ```

- [ ] Check docker-compose.yml syntax
  ```bash
  docker-compose config
  ```

- [ ] Check .env file has no syntax errors
  ```bash
  cat .env | grep -v "^#" | grep -v "^$"
  ```

- [ ] Check port conflicts
  ```bash
  sudo netstat -tuln | grep -E "1883|9001|6379|8050"
  ```

- [ ] View service logs
  ```bash
  docker-compose logs
  ```

### Dashboard Shows No UUIDs

- [ ] Verify S3_BUCKET is correct in .env

- [ ] Check AWS credentials are valid
  ```bash
  docker-compose exec dashboard aws s3 ls s3://$(grep "^S3_BUCKET=" .env | cut -d= -f2)/
  ```

- [ ] Check data exists in S3 at correct path
  ```bash
  aws s3 ls s3://$(grep "^S3_BUCKET=" .env | cut -d= -f2)/ephys/
  ```

- [ ] Check dashboard logs for errors
  ```bash
  docker-compose logs dashboard
  ```

### Jobs Not Creating on Kubernetes

- [ ] Verify kubectl is configured
  ```bash
  docker-compose exec listener kubectl get nodes
  ```

- [ ] Check namespace exists
  ```bash
  kubectl get namespace $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2)
  ```

- [ ] Check RBAC permissions
  ```bash
  docker-compose exec listener kubectl auth can-i create jobs -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2)
  ```

- [ ] Check listener logs
  ```bash
  docker-compose logs listener | grep -i error
  ```

### Jobs Fail on Kubernetes

- [ ] Check job logs
  ```bash
  kubectl logs -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2) job/<job-name>
  ```

- [ ] Check S3 access from job pod
  ```bash
  kubectl exec -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2) <pod-name> -- aws s3 ls
  ```

- [ ] Verify environment variables passed to job
  ```bash
  kubectl get job -n $(grep "^NRP_NAMESPACE=" .env | cut -d= -f2) <job-name> -o yaml
  ```

### MQTT Issues

- [ ] Test MQTT connection
  ```bash
  docker-compose exec mqtt mosquitto_sub -t "$$SYS/#" -C 1
  ```

- [ ] Check MQTT logs
  ```bash
  docker-compose logs mqtt
  ```

- [ ] Verify MQTT port is accessible
  ```bash
  telnet localhost 1883
  ```

### Redis Issues

- [ ] Test Redis connection
  ```bash
  docker-compose exec redis redis-cli ping
  ```

- [ ] Check Redis logs
  ```bash
  docker-compose logs redis
  ```

- [ ] Verify Redis is persistent (optional)
  ```bash
  docker-compose exec redis redis-cli info persistence
  ```

## Production Hardening Checklist

Before using in production:

### Security

- [ ] **MQTT authentication enabled** (see mosquitto/config/README.md)
- [ ] **MQTT SSL/TLS configured** (see mosquitto/config/README.md)
- [ ] **Redis password set** (update docker-compose.yml and .env)
- [ ] **.env file secured** (chmod 600 .env)
- [ ] **Firewall rules configured** for dashboard access
- [ ] **VPN required** for remote access (recommended)

### Monitoring

- [ ] **Log aggregation** configured (e.g., ELK stack)
- [ ] **Metrics collection** enabled (e.g., Prometheus)
- [ ] **Alerting** configured (e.g., Grafana alerts)
- [ ] **Health checks** monitored
- [ ] **Disk space** monitored (MQTT logs, Redis data)

### Backup

- [ ] **S3 bucket versioning** enabled
- [ ] **Redis snapshots** automated
- [ ] **MQTT configuration** backed up
- [ ] **.env file** backed up securely
- [ ] **Kubernetes manifests** version controlled

### High Availability

- [ ] **External MQTT broker** configured (optional)
- [ ] **External Redis** configured (optional)
- [ ] **Dashboard load balancing** configured (if needed)
- [ ] **Automatic restart** enabled (check docker-compose restart policies)

### Performance

- [ ] **Resource limits** set in docker-compose.yml
- [ ] **Kubernetes resource limits** configured
- [ ] **Redis memory limit** set
- [ ] **MQTT message size limits** configured

## Success Criteria

Your deployment is production-ready when:

✅ All services start automatically on boot  
✅ Health checks pass consistently  
✅ Jobs complete successfully  
✅ Monitoring is in place  
✅ Backups are automated  
✅ Security measures are implemented  
✅ Team members can access dashboard  
✅ Performance is acceptable for your workload  

## Getting Help

If you encounter issues not covered by this checklist:

1. **Review logs**: `docker-compose logs` and `kubectl logs`
2. **Check documentation**: [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md)
3. **Consult troubleshooting guide**: [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md#troubleshooting)
4. **MQTT guide**: [mosquitto/config/README.md](./mosquitto/config/README.md)
5. **Open an issue**: https://github.com/braingeneers/maxwell_ephys_pipeline/issues

## Next Steps

After completing this checklist:

1. [ ] Review [STANDALONE_DEPLOYMENT.md](./STANDALONE_DEPLOYMENT.md) for advanced configuration
2. [ ] Set up monitoring and alerting
3. [ ] Configure backups
4. [ ] Harden security for production
5. [ ] Train team members on the dashboard
6. [ ] Process test datasets
7. [ ] Scale as needed

---

**Version**: 1.0  
**Last Updated**: January 2025
