# Deployment Guide

Complete guide for deploying Project Atticus in various environments.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.10+
- Neo4j 5.x
- OpenAI API key (required)
- Anthropic API key (optional)

### Setup

```bash
# Clone repository
git clone https://github.com/adigo-tamu/NLP_Project_Atticus_Legal_Knowlegde_Graph.git
cd NLP_Project_Atticus_Legal_Knowlegde_Graph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings
```

### Running Locally

```bash
# Start Neo4j (separate terminal)
neo4j start  # Or use Neo4j Desktop

# Start API server
python scripts/run_api.py

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

---

## Docker Deployment

### Quick Start

```bash
# Set API keys in .env file
echo "OPENAI_API_KEY=your_key_here" >> .env
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Services

- **atticus-api**: REST API server on port 8000
- **atticus-neo4j**: Neo4j database on ports 7474 (HTTP) and 7687 (Bolt)

### Accessing Services

```bash
# API
curl http://localhost:8000/health

# Neo4j Browser
open http://localhost:7474
# Username: neo4j
# Password: password

# API Documentation
open http://localhost:8000/docs
```

### Custom Configuration

Edit `docker-compose.yml` to customize:

```yaml
services:
  atticus:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - NEO4J_URI=bolt://neo4j:7687
    volumes:
      - ./data:/app/data          # Mount data directory
      - ./output:/app/output      # Mount output directory
      - ./config:/app/config      # Mount custom config
```

### Building Custom Image

```bash
# Build for development
docker build -t atticus:dev --target development .

# Build for production
docker build -t atticus:prod --target production .

# Run custom image
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e NEO4J_URI=bolt://host:7687 \
  atticus:prod
```

---

## Production Deployment

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Load Balancer                     │
│                   (nginx/HAProxy)                    │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
┌────────▼────────┐         ┌────────▼────────┐
│  Atticus API 1  │         │  Atticus API 2  │
│   (Container)   │         │   (Container)   │
└────────┬────────┘         └────────┬────────┘
         │                           │
         └─────────────┬─────────────┘
                       │
              ┌────────▼────────┐
              │   Neo4j Cluster │
              │   (HA Setup)    │
              └─────────────────┘
```

### Deployment Checklist

- [ ] Configure environment variables securely
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up logging and monitoring
- [ ] Configure backup strategy
- [ ] Set resource limits (CPU, memory)
- [ ] Enable health checks
- [ ] Configure auto-restart policies
- [ ] Set up alerting
- [ ] Document runbooks

### Environment Variables

**Required:**
```bash
OPENAI_API_KEY=sk-...
NEO4J_URI=bolt://neo4j-host:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=secure_password
```

**Optional:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

### Security Considerations

1. **API Keys**: Use secrets management (AWS Secrets Manager, HashiCorp Vault)
2. **Authentication**: Add API key authentication for production
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Implement rate limiting to prevent abuse
5. **CORS**: Configure allowed origins appropriately
6. **Network**: Use private networks for database connections
7. **Monitoring**: Enable comprehensive logging and monitoring

### nginx Configuration

```nginx
upstream atticus_api {
    server atticus-api-1:8000;
    server atticus-api-2:8000;
}

server {
    listen 80;
    server_name api.atticus.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.atticus.example.com;

    ssl_certificate /etc/ssl/certs/atticus.crt;
    ssl_certificate_key /etc/ssl/private/atticus.key;

    location / {
        proxy_pass http://atticus_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        proxy_pass http://atticus_api/health;
        access_log off;
    }
}
```

---

## Cloud Deployment

### AWS Deployment

#### Using ECS (Elastic Container Service)

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

docker build -t atticus:latest .
docker tag atticus:latest <account>.dkr.ecr.us-east-1.amazonaws.com/atticus:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/atticus:latest

# Deploy to ECS using task definition
aws ecs update-service --cluster atticus-cluster \
  --service atticus-api --force-new-deployment
```

#### Infrastructure as Code (Terraform)

```hcl
# terraform/main.tf
resource "aws_ecs_cluster" "atticus" {
  name = "atticus-cluster"
}

resource "aws_ecs_task_definition" "atticus_api" {
  family                   = "atticus-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"

  container_definitions = jsonencode([{
    name  = "atticus"
    image = "<account>.dkr.ecr.us-east-1.amazonaws.com/atticus:latest"
    
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    
    environment = [
      { name = "NEO4J_URI", value = "bolt://neo4j:7687" }
    ]
    
    secrets = [
      { name = "OPENAI_API_KEY", valueFrom = "arn:aws:secretsmanager:..." }
    ]
  }])
}
```

### Google Cloud Platform (GCP)

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/atticus

# Deploy to Cloud Run
gcloud run deploy atticus-api \
  --image gcr.io/PROJECT_ID/atticus \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars NEO4J_URI=bolt://neo4j:7687 \
  --set-secrets OPENAI_API_KEY=openai-key:latest
```

### Azure

```bash
# Build and push to ACR
az acr build --registry myregistry --image atticus:latest .

# Deploy to Azure Container Instances
az container create \
  --resource-group atticus-rg \
  --name atticus-api \
  --image myregistry.azurecr.io/atticus:latest \
  --dns-name-label atticus-api \
  --ports 8000 \
  --environment-variables \
    NEO4J_URI=bolt://neo4j:7687 \
  --secure-environment-variables \
    OPENAI_API_KEY=$OPENAI_API_KEY
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# API health check
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "neo4j_connected": true,
#   "llm_available": true,
#   "version": "1.0.0"
# }
```

### Logging

**Application Logs:**
```bash
# Docker
docker-compose logs -f atticus

# Systemd
journalctl -u atticus -f

# Log rotation
cat > /etc/logrotate.d/atticus << EOF
/var/log/atticus/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 atticus atticus
}
