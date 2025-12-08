# MQTT Configuration

This directory contains the MQTT broker (Mosquitto) configuration for SpikeCanvas services.

## Files

- `mosquitto.conf` - Main Mosquitto configuration file
- `passwords.txt` - User passwords (created when authentication is enabled)
- `acl.txt` - Access control lists (optional)
- `certs/` - SSL/TLS certificates (for production)

## Quick Start

The default configuration allows anonymous connections for easy development setup.

## Production Security Setup

### 1. Enable Authentication

Create a password file:

```bash
# Create first user (creates the file)
docker-compose exec mqtt mosquitto_passwd -c /mosquitto/config/passwords.txt admin

# Add additional users (without -c to avoid overwriting)
docker-compose exec mqtt mosquitto_passwd /mosquitto/config/passwords.txt dashboard
docker-compose exec mqtt mosquitto_passwd /mosquitto/config/passwords.txt listener
docker-compose exec mqtt mosquitto_passwd /mosquitto/config/passwords.txt scanner
```

Edit `mosquitto.conf`:
```
allow_anonymous false
password_file /mosquitto/config/passwords.txt
```

Restart MQTT broker:
```bash
docker-compose restart mqtt
```

### 2. Access Control Lists (ACL)

Create `acl.txt` to control topic access:

```
# Admin has full access
user admin
topic readwrite #

# Dashboard can publish job requests
user dashboard
topic write jobs/+/request
topic read jobs/+/status
topic read jobs/+/results

# Listener can read requests and write status
user listener
topic read jobs/+/request
topic write jobs/+/status
topic write jobs/+/results

# Scanner can write status updates
user scanner
topic write jobs/+/status
```

Enable in `mosquitto.conf`:
```
acl_file /mosquitto/config/acl.txt
```

### 3. SSL/TLS Encryption

Generate certificates:

```bash
# Create certs directory
mkdir -p mosquitto/config/certs

# Generate CA certificate
openssl req -new -x509 -days 3650 -extensions v3_ca \
    -keyout mosquitto/config/certs/ca.key \
    -out mosquitto/config/certs/ca.crt \
    -subj "/CN=MQTT-CA"

# Generate server certificate
openssl genrsa -out mosquitto/config/certs/server.key 2048
openssl req -new -key mosquitto/config/certs/server.key \
    -out mosquitto/config/certs/server.csr \
    -subj "/CN=mqtt.local"
openssl x509 -req -in mosquitto/config/certs/server.csr \
    -CA mosquitto/config/certs/ca.crt \
    -CAkey mosquitto/config/certs/ca.key \
    -CAcreateserial -out mosquitto/config/certs/server.crt \
    -days 3650

# Set permissions
chmod 644 mosquitto/config/certs/*.crt
chmod 600 mosquitto/config/certs/*.key
```

Enable SSL in `mosquitto.conf`:
```
listener 8883
protocol mqtt
cafile /mosquitto/config/certs/ca.crt
certfile /mosquitto/config/certs/server.crt
keyfile /mosquitto/config/certs/server.key
require_certificate false
```

Update docker-compose.yml to expose port 8883:
```yaml
ports:
  - "8883:8883"  # MQTT with SSL
```

## Testing

Test MQTT connection:

```bash
# Subscribe to test topic
docker-compose exec mqtt mosquitto_sub -h localhost -t test

# Publish to test topic (in another terminal)
docker-compose exec mqtt mosquitto_pub -h localhost -t test -m "Hello MQTT"
```

With authentication:
```bash
mosquitto_sub -h localhost -u admin -P password -t test
mosquitto_pub -h localhost -u admin -P password -t test -m "Hello MQTT"
```

## Monitoring

View MQTT logs:
```bash
docker-compose logs -f mqtt
```

Check active connections:
```bash
docker-compose exec mqtt sh -c 'cat /mosquitto/log/mosquitto.log | grep "New connection"'
```

## Troubleshooting

1. **Connection refused**: Check if MQTT container is running
   ```bash
   docker-compose ps mqtt
   ```

2. **Authentication failed**: Verify password file exists and is readable
   ```bash
   docker-compose exec mqtt cat /mosquitto/config/passwords.txt
   ```

3. **Permission denied**: Check file permissions in mosquitto/config/

4. **Port conflicts**: Ensure ports 1883 and 9001 are not in use
   ```bash
   netstat -tuln | grep -E '1883|9001'
   ```

## References

- [Mosquitto Documentation](https://mosquitto.org/documentation/)
- [MQTT Protocol](https://mqtt.org/)
- [Mosquitto Docker Image](https://hub.docker.com/_/eclipse-mosquitto)
