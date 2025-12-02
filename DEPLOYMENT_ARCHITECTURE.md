# SpikeCanvas Deployment Architecture

Visual guide to deployment options and architecture for Maxwell SpikeCanvas.

---

## Deployment Options Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SpikeCanvas Deployment Options                     │
└─────────────────────────────────────────────────────────────────────────┘

     Desktop                Server               Custom Build         Cloud/K8s
    
    Individual Use          Team Access           Full Control          Enterprise Scale
    ├── Quick Start         ├── Linux Server      ├── Own Registry      ├── Kubernetes
    ├── 5 minutes           ├── 15-30 minutes     ├── 1-2 hours         ├── 2-4 hours
    ├── Pre-built images    ├── Docker Compose    ├── Custom images     ├── High availability
    ├── localhost:8050      ├── Shared access     ├── CI/CD pipeline    ├── Auto-scaling
    └── Perfect for:        └── Perfect for:      └── Perfect for:      └── Perfect for:
        • Testing               • Labs                • Institutions        • Consortiums
        • Development           • Small teams         • Custom code         • Multi-site
        • Learning              • Persistent          • Air-gapped          • Heavy workloads
        • Small datasets        • Production          • Compliance          • Cloud native
```

---

## Desktop Deployment (Tier 1)

```
┌─────────────────────────────────────────────────────────────────┐
│  Your Laptop/Desktop (macOS, Windows, or Linux)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📄 pipeline.yaml (Configuration)                               │
│      ↓                                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Docker Desktop                                           │  │
│  │                                                            │  │
│  │  ┌────────────────────┐                                   │  │
│  │  │ Dashboard Container│  Pre-built image                  │  │
│  │  │ surygeng/maxwell   │  from Docker Hub                  │  │
│  │  │ Port: 8050        │                                    │  │
│  │  └────────────────────┘                                   │  │
│  │         ↓                                                  │  │
│  │  Reads: pipeline.yaml                                     │  │
│  │  Mounts: ~/.aws/credentials                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Browser: http://localhost:8050 ────────────────────────┐      │
│                                                          ↓       │
│                                                    Dashboard UI  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                     Internet Connection
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│  AWS S3 (Your Institution's Bucket)                              │
│  s3://your-bucket/ephys/                                         │
│    ├── uuid-001/                                                 │
│    ├── uuid-002/                                                 │
│    └── ...                                                       │
└──────────────────────────────────────────────────────────────────┘
```

**Steps:**
1. Create `pipeline.yaml` with S3 bucket config
2. Run `docker-compose up`
3. Access `http://localhost:8050`
4. Dashboard lists UUIDs and submits jobs

**Pros:**  Instant setup,  No server needed,  Great for testing  
**Cons:**  Local resources only,  Not accessible to team

---

## Server Deployment (Tier 2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Linux Server (Ubuntu/CentOS/Debian)                                    │
│  IP: 192.168.1.100 or lab-server.university.edu                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📄 pipeline.yaml (Shared configuration for all services)               │
│      ↓                                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Docker / Docker Compose                                          │  │
│  │                                                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  │
│  │  │  Dashboard   │  │ Job Scanner  │  │ MQTT Listener│           │  │
│  │  │  Container   │  │  Container   │  │  Container   │           │  │
│  │  │  Port: 8050  │  │              │  │              │           │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │  │
│  │         ↓                 ↓                  ↓                     │  │
│  │         └─────────────────┴──────────────────┘                    │  │
│  │                  All read pipeline.yaml                           │  │
│  │                  All mount ~/.aws/credentials                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Firewall: Allow port 8050 ───────────────────────────┐                │
└───────────────────────────────────────────────────────┼────────────────┘
                                                         ↓
┌────────────────────────────────────────────────────────────────────┐
│  User Workstations (Lab Members)                                   │
│                                                                     │
│  Alice:   http://lab-server.university.edu:8050                    │
│  Bob:     http://192.168.1.100:8050                                │
│  Carol:   http://lab-server.university.edu:8050                    │
│                                                                     │
│  All access same Dashboard ──→ Same job queue ──→ Same S3 data     │
└────────────────────────────────────────────────────────────────────┘
                           ↓
                     Internet/VPN
                           ↓
┌──────────────────────────────────────────────────────────────────────┐
│  S3 + Kubernetes Cluster                                             │
│                                                                       │
│  S3: s3://university-neuroscience/ephys/                            │
│  K8s: Runs spike sorting jobs submitted from Dashboard              │
└──────────────────────────────────────────────────────────────────────┘
```

**Steps:**
1. Install Docker on Linux server
2. Create shared `pipeline.yaml`
3. Run `docker-compose up -d`
4. Configure firewall (port 8050)
5. Team accesses via server hostname/IP

**Pros:**  Team access,  Persistent,  Better resources,  Production-ready  
**Cons:**  Need server infrastructure,  Basic sysadmin required

---

## Custom Registry Deployment (Tier 3)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Development Machine                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Clone Repository                                                    │
│     git clone https://github.com/braingeneers/SpikeCanvas.git        │
│                                                                          │
│  2. Customize Code (optional)                                           │
│     Edit: Services/MaxWell_Dashboard/src/                               │
│                                                                          │
│  3. Build Custom Images                                                 │
│     ./build-all.sh                                                      │
│     ├── Reads Dockerfiles                                               │
│     ├── Builds images locally                                           │
│     └── Tags: your-registry.com/maxwell_dashboard:v1.0                  │
│                                                                          │
│  4. Push to Your Registry                                               │
│     ./push-all.sh                                                       │
│         ↓                                                                │
└─────────┼────────────────────────────────────────────────────────────────┘
          ↓
┌─────────┴────────────────────────────────────────────────────────────────┐
│  Your Docker Registry                                                     │
│  (Docker Hub, AWS ECR, Google GCR, or Private Registry)                 │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  your-registry.com/                                                      │
│    ├── maxwell_dashboard:v1.0                                           │
│    ├── job_scanner:v1.0                                                 │
│    ├── mqtt_listener:v1.0                                               │
│    └── ...                                                               │
│                                                                           │
└───────────────────────────────────────┬───────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  Production Server(s)                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  docker-compose.custom.yml:                                             │
│    image: your-registry.com/maxwell_dashboard:v1.0                      │
│                                                                          │
│  docker-compose up -d                                                   │
│  ├── Pulls from YOUR registry                                           │
│  ├── Uses YOUR custom images                                            │
│  └── Full control and customization                                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Steps:**
1. Clone and optionally customize code
2. Build images with `./build-all.sh`
3. Push to your registry with `./push-all.sh`
4. Deploy using `docker-compose.custom.yml`

**Pros:**  Full control,  Custom modifications,  Independent,  Compliant  
**Cons:**  Requires build infrastructure,  More maintenance,  Registry costs

---

## Kubernetes/Cloud Deployment (Tier 4)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (AWS EKS, Google GKE, Azure AKS, or On-Prem)       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Namespace: ephys-pipeline                                              │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  ConfigMap: pipeline-config                                       │  │
│  │  ┌──────────────────────────────────────────┐                    │  │
│  │  │ pipeline.yaml:                           │                    │  │
│  │  │   bucket: institution-bucket             │                    │  │
│  │  │   prefix: ephys                          │                    │  │
│  │  └──────────────────────────────────────────┘                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                           ↓                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Deployments (with replicas for HA)                              │  │
│  │                                                                    │  │
│  │  Dashboard Deployment (replicas: 2)                              │  │
│  │  ┌────────────┐  ┌────────────┐                                  │  │
│  │  │ Dashboard  │  │ Dashboard  │                                  │  │
│  │  │   Pod 1    │  │   Pod 2    │  ← Auto-scaling                 │  │
│  │  └────────────┘  └────────────┘                                  │  │
│  │         ↓              ↓                                          │  │
│  │  ┌─────────────────────────────┐                                 │  │
│  │  │    Service: dashboard       │                                 │  │
│  │  │    Type: LoadBalancer       │                                 │  │
│  │  │    External IP: x.x.x.x     │                                 │  │
│  │  └─────────────────────────────┘                                 │  │
│  │                                                                    │  │
│  │  Job Scanner Deployment (replicas: 1)                            │  │
│  │  ┌────────────┐                                                  │  │
│  │  │   Scanner  │                                                  │  │
│  │  │    Pod     │                                                  │  │
│  │  └────────────┘                                                  │  │
│  │                                                                    │  │
│  │  MQTT Listener Deployment (replicas: 1)                          │  │
│  │  ┌────────────┐                                                  │  │
│  │  │  Listener  │                                                  │  │
│  │  │    Pod     │                                                  │  │
│  │  └────────────┘                                                  │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Ingress (with TLS/HTTPS)                                        │  │
│  │  ┌────────────────────────────────────────┐                     │  │
│  │  │ https://ephys.institution.edu          │                     │  │
│  │  │   ↓                                     │                     │  │
│  │  │ cert-manager (Let's Encrypt)           │                     │  │
│  │  │   ↓                                     │                     │  │
│  │  │ Routes to Dashboard Service            │                     │  │
│  │  └────────────────────────────────────────┘                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Resource Limits & Requests:                                            │
│    • Dashboard: 2 CPU, 4GB RAM per pod                                 │
│    • Scanner:   1 CPU, 2GB RAM                                         │
│    • Listener:  1 CPU, 2GB RAM                                         │
│                                                                          │
│  Persistent Volumes:                                                    │
│    • Logs (EBS/PD volumes)                                              │
│    • Config (ConfigMaps)                                                │
│    • Secrets (K8s Secrets)                                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Users (Worldwide Access)                                             │
│                                                                        │
│  Research Group A ──→ https://ephys.institution.edu                  │
│  Research Group B ──→ https://ephys.institution.edu                  │
│  Remote Collaborators ──→ https://ephys.institution.edu              │
│                                                                        │
│  All access through:                                                  │
│    • Load balancer (high availability)                                │
│    • HTTPS with valid certificates                                   │
│    • Auto-scaling based on load                                      │
│    • Multi-region support (optional)                                 │
└──────────────────────────────────────────────────────────────────────┘
```

**Steps:**
1. Set up Kubernetes cluster
2. Create namespace and ConfigMap
3. Deploy with kubectl or Helm
4. Configure Ingress for HTTPS
5. Set up monitoring and auto-scaling

**Pros:**  High availability,  Auto-scaling,  Enterprise-grade,  Multi-region  
**Cons:**  Complex setup,  K8s expertise required,  Higher costs

---

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Configuration Priority (Highest to Lowest)                              │
└─────────────────────────────────────────────────────────────────────────┘

    1. Environment Variables          ← Always override everything
       ├── S3_BUCKET=my-bucket
       ├── S3_PREFIX=ephys
       └── AWS_REGION=us-west-2
                ↓
    2. YAML at $PIPELINE_CONFIG       ← Custom path if set
       └── /custom/path/config.yaml
                ↓
    3. YAML at /app/config/pipeline.yaml   ← Standard container location
       └── Mounted from host
                ↓
    4. YAML at /config/pipeline.yaml       ← Alternative location
       └── ConfigMap in Kubernetes
                ↓
    5. Built-in Defaults              ← Fallback (may not work)
       └── Hardcoded values


Example Configuration Hierarchy:
─────────────────────────────────

pipeline.yaml says:           Environment variable says:      Result:
bucket: dev-bucket            S3_BUCKET=prod-bucket          prod-bucket
prefix: ephys                 (not set)                      ephys
region: us-east-1            AWS_REGION=us-west-2           us-west-2
```

---

## Data Flow Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Complete SpikeCanvas Data Flow                                          │
└────────────────────────────────────────────────────────────────────────────┘

1. Data Upload
───────────────
  Lab Bench                      S3 Bucket
  ┌─────────┐                   ┌──────────────────┐
  │ Maxwell │  Upload via       │ s3://bucket/     │
  │ Device  │ ────────────────→ │   ephys/         │
  │         │  braingeneerspy   │     uuid-123/    │
  └─────────┘                   │       data.h5    │
                                └──────────────────┘

2. Job Submission
──────────────────
  User Browser                  Dashboard Container              MQTT Broker
  ┌──────────┐                 ┌───────────────────┐            ┌──────────┐
  │ UI       │  Submit Job     │ Validate params   │  Publish   │ Job      │
  │ localhost│ ──────────────→ │ Create CSV entry  │ ─────────→ │ Queue    │
  │ :8050    │                 │ Update S3         │            │          │
  └──────────┘                 └───────────────────┘            └──────────┘

3. Job Execution
─────────────────
  MQTT Listener                 Kubernetes Cluster              Processing Pod
  ┌──────────────┐             ┌────────────────────┐          ┌─────────────┐
  │ Subscribe to │  Create     │ Schedule pod       │  Run     │ Kilosort2   │
  │ job queue    │ ──────────→ │ Allocate resources │ ───────→ │ Algorithm   │
  │              │  K8s Job    │                    │          │             │
  └──────────────┘             └────────────────────┘          └─────────────┘
                                                                      ↓
4. Data Processing                                                    ↓
───────────────────                                                   ↓
  S3 Input                      Processing                    S3 Output
  ┌──────────────┐             ┌──────────┐                 ┌──────────────┐
  │ Raw data     │  Download   │ Process  │  Upload         │ Spike data   │
  │ uuid-123/    │ ──────────→ │ in pod   │ ──────────────→ │ uuid-123/    │
  │   data.h5    │             │          │                 │   spikes/    │
  └──────────────┘             └──────────┘                 └──────────────┘

5. Status Updates
──────────────────
  Job Scanner                   S3 Status CSV                Dashboard
  ┌─────────────┐              ┌───────────────┐           ┌──────────┐
  │ Poll K8s    │  Update      │ job_status    │  Read     │ Show     │
  │ job status  │ ───────────→ │ timestamps    │ ────────→ │ status   │
  │             │              │ completion    │           │ to user  │
  └─────────────┘              └───────────────┘           └──────────┘

6. Results Access
──────────────────
  User Browser                  Dashboard                   S3 Results
  ┌──────────────┐             ┌──────────┐               ┌─────────────┐
  │ View results │  Request    │ Generate │  Fetch        │ Processed   │
  │ Download     │ ──────────→ │ links    │ ────────────→ │ data and    │
  │ plots        │             │          │               │ plots       │
  └──────────────┘             └──────────┘               └─────────────┘
```

---

## Comparison Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Feature Comparison Across Deployment Options                               │
├──────────────────┬──────────┬──────────┬───────────────┬───────────────────┤
│ Feature          │ Desktop  │ Server   │ Custom Build  │ Kubernetes        │
├──────────────────┼──────────┼──────────┼───────────────┼───────────────────┤
│ Setup Time       │ 5 min    │ 15-30min │ 1-2 hours     │ 2-4 hours         │
│ Difficulty       │         │       │          │            │
│ Team Access      │         │         │              │                  │
│ High Availability│         │         │              │                  │
│ Auto-scaling     │         │         │              │                  │
│ Custom Code      │         │         │              │                  │
│ Air-gapped       │         │         │              │                  │
│ Resource Control │ Limited  │ Good     │ Full          │ Full              │
│ SSL/HTTPS        │         │ Manual   │ Manual        │ Easy (Ingress)    │
│ Monitoring       │ Basic    │ Docker   │ Docker        │ Advanced (K8s)    │
│ Cost             │ Free     │ Server   │ Server+Reg    │ Cloud+K8s         │
│ Best For         │ Learning │ Labs     │ Institutions  │ Enterprise        │
└──────────────────┴──────────┴──────────┴───────────────┴───────────────────┘

Legend:  = Easy,  = Expert level required
```

---

## Decision Tree

```
                    Start Here: Choose Your Deployment
                                  │
                                  ├── Just trying it out?
                                  │   Learning the system?
                                  │   Small dataset?
                                  │   └─→ YES ──→  DESKTOP (Tier 1)
                                  │              Quick Start Guide
                                  │              5 minutes
                                  │
                                  ├── Need team access?
                                  │   Have a server?
                                  │   Production use?
                                  │   └─→ YES ──→  SERVER (Tier 2)
                                  │              Deployment Guide
                                  │              15-30 minutes
                                  │
                                  ├── Need custom code?
                                  │   Have own registry?
                                  │   Air-gapped environment?
                                  │   Compliance requirements?
                                  │   └─→ YES ──→  CUSTOM BUILD (Tier 3)
                                  │              Custom Build Guide
                                  │              1-2 hours
                                  │
                                  └── Need high availability?
                                      Auto-scaling?
                                      Multi-region?
                                      Enterprise scale?
                                      └─→ YES ──→  KUBERNETES (Tier 4)
                                                 Deployment Guide (K8s section)
                                                 2-4 hours


Still not sure? Start with Desktop → Migrate to Server when ready → 
Scale to K8s if needed
```

---

## Migration Paths

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Upgrade Path: Start Simple, Scale as Needed                                │
└─────────────────────────────────────────────────────────────────────────────┘

Stage 1: Desktop              Stage 2: Server              Stage 3: Cloud/K8s
───────────────────           ────────────────             ───────────────────

 Individual Use               Team Access                 Enterprise Scale
│                              │                             │
├─ laptop:8050                 ├─ server.lab.edu:8050       ├─ ephys.institution.edu
├─ Local resources             ├─ Shared server              ├─ Load balanced
├─ Pre-built images            ├─ Docker Compose            ├─ Auto-scaling
└─ pipeline.yaml               ├─ Same pipeline.yaml        ├─ ConfigMap
                               └─ 24/7 availability         ├─ HTTPS
                                                             └─ Multi-region

Migration Steps:               Migration Steps:             Migration Steps:
─────────────────              ─────────────────            ─────────────────
1. Works on laptop             1. Copy pipeline.yaml        1. Create K8s cluster
2.  Validated                 2. Install Docker on server  2. Create ConfigMap
                               3. Run docker-compose up     3. Deploy with kubectl
                               4. Configure firewall        4. Set up Ingress
                               5.  Team can access         5. Configure monitoring

Time: Day 1                    Time: Week 1-2               Time: Month 1-3
Cost: $0                       Cost: $100-500/month         Cost: $500-5000/month
Effort: 5 minutes              Effort: 1-2 hours            Effort: 20-40 hours
```

---

## Shared Configuration Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  How All Services Share One Configuration                                   │
└─────────────────────────────────────────────────────────────────────────────┘

Host Machine:
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│  📄 pipeline.yaml (Single source of truth)                               │
│  ┌────────────────────────────────────────┐                             │
│  │ bucket: my-institution-bucket          │                             │
│  │ prefix: ephys                          │                             │
│  │ input_prefix: raw-recordings           │                             │
│  │ output_prefix: processed-results       │                             │
│  └────────────────────────────────────────┘                             │
│                        │                                                  │
│                        │ Mounted to all containers                       │
│                        ↓                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Container 1: Dashboard      Container 2: Scanner                  │ │
│  │  ┌─────────────────────┐    ┌─────────────────────┐              │ │
│  │  │ Mount:              │    │ Mount:              │              │ │
│  │  │ /app/config/        │    │ /app/config/        │              │ │
│  │  │   pipeline.yaml ─────────┼───pipeline.yaml     │              │ │
│  │  │                     │    │                     │              │ │
│  │  │ Reads:              │    │ Reads:              │              │ │
│  │  │ bucket=my-inst...   │    │ bucket=my-inst...   │              │ │
│  │  │ prefix=ephys        │    │ prefix=ephys        │              │ │
│  │  └─────────────────────┘    └─────────────────────┘              │ │
│  │                                                                    │ │
│  │  Container 3: MQTT Listener                                       │ │
│  │  ┌─────────────────────┐                                         │ │
│  │  │ Mount:              │                                         │ │
│  │  │ /app/config/        │                                         │ │
│  │  │   pipeline.yaml ◄───┘                                         │ │
│  │  │                     │                                         │ │
│  │  │ Reads:              │                                         │ │
│  │  │ bucket=my-inst...   │                                         │ │
│  │  │ prefix=ephys        │                                         │ │
│  │  └─────────────────────┘                                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  All services get same configuration ─→ Consistency guaranteed           │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘

Benefits:
 Single source of truth
 Easy to update (edit one file, restart containers)
 No configuration drift between services
 Version control friendly
 Works same way in all deployment scenarios
```

---

## See Also

- **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[CUSTOM_BUILD_GUIDE.md](CUSTOM_BUILD_GUIDE.md)** - Build your own images
- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Configuration reference
- **[Services/common/CONFIG_USAGE_GUIDE.md](Services/common/CONFIG_USAGE_GUIDE.md)** - Configuration API

---

**Choose your deployment path above and follow the corresponding guide!** 
