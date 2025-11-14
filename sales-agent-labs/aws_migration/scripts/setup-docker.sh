#!/bin/bash
# This script installs Docker and Docker Compose on the Lightsail instance
# Run this via AWS Systems Manager or browser-based SSH

set -e

echo "🚀 Setting up Docker on Lightsail instance..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
echo "✅ Verifying installations..."
docker --version
docker-compose --version

# Enable Docker to start on boot
sudo systemctl enable docker
sudo systemctl start docker

echo "✅ Docker installation complete!"
echo "ℹ️  Log out and log back in for group changes to take effect"
