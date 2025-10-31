#!/bin/bash
# ClassMate Server Setup Script for AWS EC2 Ubuntu
# This script installs all dependencies and sets up the environment

set -e  # Exit on error

echo "============================================"
echo "  ClassMate Server Setup - Starting..."
echo "============================================"

# Update system
echo "[1/10] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install basic dependencies
echo "[2/10] Installing basic dependencies..."
sudo apt-get install -y \
    git \
    curl \
    wget \
    vim \
    htop \
    build-essential \
    software-properties-common

# Install Python 3.10
echo "[3/10] Installing Python 3.10..."
sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Install Node.js (for React build)
echo "[4/10] Installing Node.js 18..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Neo4j
echo "[5/10] Installing Neo4j..."
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j

# Configure Neo4j
echo "[6/10] Configuring Neo4j..."
sudo sed -i 's/#dbms.default_listen_address=0.0.0.0/dbms.default_listen_address=127.0.0.1/' /etc/neo4j/neo4j.conf
sudo sed -i 's/#server.default_listen_address=0.0.0.0/server.default_listen_address=127.0.0.1/' /etc/neo4j/neo4j.conf

# Set Neo4j initial password
echo "[7/10] Setting Neo4j password..."
sudo neo4j-admin dbms set-initial-password classmate2025

# Start Neo4j
sudo systemctl enable neo4j
sudo systemctl start neo4j

# Install Nginx
echo "[8/10] Installing Nginx..."
sudo apt-get install -y nginx

# Create swap space (2GB) for memory optimization
echo "[9/10] Creating swap space (2GB)..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap space created successfully"
else
    echo "Swap space already exists"
fi

# Install PM2 (Process Manager)
echo "[10/10] Installing PM2..."
sudo npm install -g pm2

echo ""
echo "============================================"
echo "  ✅ Server setup completed!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Clone your repository"
echo "2. Run deploy.sh to deploy the application"
echo ""
echo "Neo4j Credentials:"
echo "  URL: bolt://localhost:7687"
echo "  Username: neo4j"
echo "  Password: classmate2025"
echo ""
