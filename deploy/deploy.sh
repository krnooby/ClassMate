#!/bin/bash
# ClassMate Deployment Script
# Run this script to deploy/update the application

set -e  # Exit on error

PROJECT_DIR="/home/ubuntu/ClassMate"
BACKEND_DIR="$PROJECT_DIR/src"
FRONTEND_DIR="$PROJECT_DIR/src/web"

echo "============================================"
echo "  ClassMate Deployment - Starting..."
echo "============================================"

# Navigate to project directory
cd $PROJECT_DIR

# Pull latest code (skip if not a git repo)
echo "[1/8] Checking for git repository..."
if [ -d .git ]; then
    echo "Git repository found, pulling latest code..."
    git pull origin main
else
    echo "Not a git repository, skipping git pull..."
fi

# Setup Python virtual environment
echo "[2/8] Setting up Python environment..."
cd $BACKEND_DIR
if [ ! -d ".venv" ]; then
    python3.10 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r ../requirements.txt

# Build React frontend
echo "[3/8] Building React frontend..."
cd $FRONTEND_DIR
npm install
npm run build

# Copy built files to nginx
echo "[4/8] Deploying frontend to Nginx..."
sudo rm -rf /var/www/classmate
sudo mkdir -p /var/www/classmate
sudo cp -r dist/* /var/www/classmate/

# Setup environment variables
echo "[5/8] Setting up environment variables..."
cd $PROJECT_DIR

if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=classmate2025
NEO4J_DB=neo4j

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Google Cloud (Document AI)
GCP_PROJECT=classmate-474107
DOC_OCR_PROCESSOR_ID=74048a4bb37671e9
DOC_LOCATION=us

# Embedding Model
EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B
EOF
    echo "⚠️  Please edit .env and add your API keys!"
fi

# Setup Neo4j indexes
echo "[6/8] Setting up Neo4j indexes..."
source $BACKEND_DIR/.venv/bin/activate
cd $BACKEND_DIR
PYTHONPATH=$BACKEND_DIR python utils/setup_neo4j_indexes.py || echo "Index setup skipped (may already exist)"

# Start/Restart Backend API with PM2
echo "[7/8] Starting/Restarting Backend API..."
cd $BACKEND_DIR
pm2 delete classmate-api 2>/dev/null || true
pm2 start $BACKEND_DIR/.venv/bin/python --name classmate-api --interpreter none -- -m uvicorn api.main:app --host 0.0.0.0 --port 8000

pm2 save
pm2 startup | tail -n 1 | sudo bash || true

# Configure Nginx
echo "[8/8] Configuring Nginx..."
sudo tee /etc/nginx/sites-available/classmate > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        root /var/www/classmate;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/classmate /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo ""
echo "============================================"
echo "  ✅ Deployment completed successfully!"
echo "============================================"
echo ""
echo "Application is now running:"
echo "  Frontend: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "  Backend API: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/api/docs"
echo ""
echo "Useful commands:"
echo "  pm2 logs classmate-api    # View backend logs"
echo "  pm2 restart classmate-api # Restart backend"
echo "  pm2 status                # Check status"
echo "  sudo systemctl status nginx  # Check Nginx"
echo ""
echo "⚠️  Don't forget to:"
echo "1. Edit .env file with your API keys"
echo "2. Restart: pm2 restart classmate-api"
echo ""
