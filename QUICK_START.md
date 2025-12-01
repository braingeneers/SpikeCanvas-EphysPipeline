# Quick Start - Run EphysPipeline on Your Desktop

Get the EphysPipeline dashboard running on your local machine in 5 minutes!

## Prerequisites

Before you start, make sure you have:

1. **Docker Desktop** installed and running
   - Windows/Mac: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Linux: [Install Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/)

2. **Internet connection** - to download Docker images and access S3

3. **AWS credentials** configured (for S3 access)
   - File at `~/.aws/credentials` with your AWS access keys
   - OR environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
   - OR IAM instance role (if running on EC2)

4. **S3 bucket** name where your ephys data is stored

## 5-Minute Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/braingeneers/EphysPipeline.git
cd EphysPipeline
```

### Step 2: Create Configuration

Run the interactive configuration script:

```bash
python3 configure.py
```

The script will guide you through 5 simple steps:
1. **S3 Storage** - Your bucket name and data folder
2. **AWS Credentials** - Access key and secret key
3. **S3 Endpoint** - Storage endpoint URL
4. **Service Configuration** - Automatically configured
5. **Kubernetes** - Namespace (if using NRP)

Your configuration will be saved to `.env` file with secure permissions.

> **Need more control?** See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for advanced configuration options including Kubernetes deployment, IAM roles, and multiple credential methods.

### Step 3: Start the Services

```bash
docker-compose up
```

The first time you run this, Docker will download the pre-built images (~2-3 GB). This takes a few minutes depending on your internet speed.

### Step 4: Access the Dashboard

Open your browser and go to:
```
http://localhost:8050
```

You should see the EphysPipeline dashboard!

## What Just Happened?

- ✅ Created `.env` configuration file with your S3 and AWS settings
- ✅ Downloaded pre-built Docker images from Docker Hub
- ✅ Started the Dashboard service
- ✅ Dashboard is now accessible at localhost:8050

## Stopping the Services

Press `Ctrl+C` in the terminal where docker-compose is running, then:

```bash
docker-compose down
```

## Restarting Later

Just run `docker-compose up` again. Docker will use cached images, so it starts instantly.

> **Note:** Your `.env` configuration file is preserved, so you don't need to run `configure.py` again.

## Configuration Options

The `configure.py` script creates a `.env` file with your settings. You can edit this file directly if needed.

**Example `.env` file:**
```bash
S3_BUCKET=my-bucket
S3_PREFIX=ephys
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-west-2
S3_ENDPOINT_URL=https://s3.us-west-2.amazonaws.com
```

**For advanced configuration:**
- Multiple credential methods (IAM roles, profiles)
- Kubernetes/NRP deployment
- Custom service paths
- See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

## Running in the Background

To run services in the background (detached mode):

```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f
```

Stop services:
```bash
docker-compose down
```

## Troubleshooting

### Error: "Cannot connect to Docker daemon"
- Make sure Docker Desktop is running
- On Linux: `sudo systemctl start docker`

### Error: "No such file or directory: ~/.aws/credentials"
- The interactive script will prompt you for AWS credentials
- Or set environment variables before running docker-compose:
  ```bash
  export AWS_ACCESS_KEY_ID="your-key"
  export AWS_SECRET_ACCESS_KEY="your-secret"
  docker-compose up
  ```

### Error: "Access Denied" when accessing S3
- Check your AWS credentials in `.env` are correct
- Verify your IAM user/role has S3 read permissions
- Confirm the bucket name in `.env` is correct

### Dashboard shows "No UUIDs found"
- Check that data exists in `s3://your-bucket/your-prefix/`
- Verify the `S3_PREFIX` in `.env` matches your data location
- Check container logs: `docker-compose logs dashboard`

### Port 8050 already in use
- Change the port in `docker-compose.yml`:
  ```yaml
  ports:
    - "8051:8050"  # Use 8051 instead
  ```
- Then access at `http://localhost:8051`

## Next Steps

- **Process your first dataset** - Use the Job Center to submit spike sorting jobs
- **Learn about all features** - Read the [main README.md](README.md)
- **Advanced configuration** - See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- **Deploy to a server** - See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Customize algorithms** - See [CUSTOM_BUILD_GUIDE.md](CUSTOM_BUILD_GUIDE.md)

## System Requirements

**Minimum:**
- 4 GB RAM
- 10 GB free disk space
- Modern CPU (2+ cores)

**Recommended:**
- 8+ GB RAM
- 20+ GB free disk space
- 4+ CPU cores
- SSD for better performance

## Desktop vs Server?

This quick start is perfect for:
- ✅ Learning the system
- ✅ Testing with small datasets
- ✅ Development work
- ✅ Small labs without servers

For production use or team access, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for server deployment.

## Getting Help

- Check the [Troubleshooting](#troubleshooting) section above
- Read the configuration guide: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- Read the deployment guide: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- Open an issue: [GitHub Issues](https://github.com/braingeneers/EphysPipeline/issues)
- Ask in Slack: #braingeneers-helpdesk channel

## Security Note

When running on a desktop:
- The dashboard is accessible to anyone on your local network
- Don't expose it to the internet without proper authentication
- Keep your AWS credentials secure (`.env` file has restricted permissions)
- Never commit `.env` to git (already in .gitignore)
- Use IAM roles with minimal required permissions

> **For production deployment:** See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for IAM role-based authentication (no keys needed).

## Updates

To get the latest version:

```bash
# Pull latest code
git pull

# Pull latest Docker images
docker-compose pull

# Restart services
docker-compose up
```

---

**That's it!** You now have a working EphysPipeline installation on your desktop. 🎉
