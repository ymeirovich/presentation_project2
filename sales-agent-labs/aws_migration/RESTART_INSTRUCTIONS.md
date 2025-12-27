# How to Restart Docker Services After Lightsail Restart

## Problem
When you stop and restart your Lightsail instance, the Docker containers don't automatically restart. This is why the web service is not responding.

## Solution Options

### Option 1: Automated Script (Recommended for Future Restarts)
Use the updated [start-lightsail.sh](scripts/start-lightsail.sh) script which now automatically restarts Docker services:

```bash
./aws_migration/scripts/start-lightsail.sh
```

This script will:
1. Start the Lightsail instance
2. Wait for it to be ready
3. SSH in and restart all Docker services
4. Verify the web service is responding

### Option 2: Manual Restart via AWS Console (Quick Fix for Now)

1. **Open Lightsail Console**:
   - Go to: https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect

2. **Connect via Browser SSH**:
   - Click the **"Connect using SSH"** button
   - This will open a browser-based terminal

3. **Run these commands**:
   ```bash
   cd /home/ubuntu/presgen/sales-agent-labs
   docker-compose down
   docker-compose up -d
   docker ps -a
   ```

4. **Wait and verify** (takes about 60 seconds):
   ```bash
   docker-compose logs -f presgen-nginx
   ```
   Press Ctrl+C to exit logs

5. **Test the service**:
   - Open http://35.175.156.231 in your browser
   - You should see the login prompt

### Option 3: Standalone Restart Script
If you just need to restart services (instance is already running):

```bash
./aws_migration/scripts/restart-services.sh
```

## Long-term Solution: Enable Auto-restart

To make Docker containers automatically restart when the instance boots, you can configure Docker's restart policy. This should be added to the instance startup:

```bash
# SSH into your instance first
ssh -i lightsail-key.pem ubuntu@35.175.156.231

# Add docker-compose to startup
cat << 'EOF' | sudo tee /etc/systemd/system/presgen-docker.service
[Unit]
Description=PresGen Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/presgen/sales-agent-labs
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=300
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable presgen-docker.service
sudo systemctl start presgen-docker.service
```

After this one-time setup, Docker services will automatically start when the instance boots.

## Current Status
- **Instance IP**: 35.175.156.231
- **Instance State**: Running
- **Docker Services**: Need to be restarted (not running)

## Troubleshooting

### If SSH key issues persist:
The SSH key may have format issues. Use the browser-based SSH from AWS Console instead (Option 2).

### If containers fail to start:
Check logs:
```bash
docker-compose logs --tail=100
```

### If service is still not responding after restart:
1. Check container status: `docker-compose ps`
2. Check nginx logs: `docker-compose logs presgen-nginx`
3. Check if ports are open: `docker-compose port presgen-nginx 80`
4. Verify firewall: `aws lightsail get-instance-port-states --instance-name presgen-prod`

## Quick Test
After restarting services, test the endpoint:
```bash
curl -I http://35.175.156.231/health
```

You should see a 200 or 401 response (401 means it's working but needs authentication).
