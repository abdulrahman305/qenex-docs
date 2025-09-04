# QENEX Production Deployment Guide

## Executive Summary

QENEX is a comprehensive banking operating system designed for financial institutions, providing enterprise-grade infrastructure for modern banking operations. This guide covers the complete deployment process for production environments.

## System Architecture

```
┌─────────────────────────────────────────────────┐
│              Load Balancer (HA)                  │
├─────────────────────────────────────────────────┤
│         API Gateway Cluster (3 nodes)            │
├──────────┬──────────┬──────────┬────────────────┤
│ Banking  │   DeFi   │  Token   │  Compliance    │
│   Core   │ Protocol │  System  │    Engine      │
├──────────┴──────────┴──────────┴────────────────┤
│        Distributed Consensus Layer               │
│            (PBFT / Raft)                         │
├─────────────────────────────────────────────────┤
│         Database Cluster (Primary + Replicas)    │
├─────────────────────────────────────────────────┤
│        Hardware Security Module (HSM)            │
└─────────────────────────────────────────────────┘
```

## Prerequisites

### Hardware Requirements

#### Minimum Production Setup
- **Nodes**: 5 servers (3 application + 2 database)
- **CPU**: 16 cores per node
- **RAM**: 64GB per node
- **Storage**: 2TB NVMe SSD per node
- **Network**: 10Gbps interconnect
- **HSM**: FIPS 140-2 Level 3 certified

#### Recommended Production Setup
- **Nodes**: 9 servers (5 application + 3 database + 1 management)
- **CPU**: 32 cores per node
- **RAM**: 128GB per node
- **Storage**: 4TB NVMe SSD RAID 10
- **Network**: 25Gbps interconnect with redundancy
- **HSM**: Network-attached HSM cluster

### Software Requirements
```bash
# Operating System
Ubuntu 22.04 LTS Server (hardened)
RHEL 8.6+ (alternative)

# Runtime Dependencies
Docker 24.0+
Kubernetes 1.28+
PostgreSQL 15+
Redis 7.2+
Nginx 1.24+
```

## Installation Steps

### 1. System Preparation

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install essential packages
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    htop \
    iotop \
    net-tools \
    software-properties-common

# Configure kernel parameters
cat << EOF | sudo tee /etc/sysctl.d/99-qenex.conf
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
vm.swappiness = 10
fs.file-max = 2097152
EOF

sudo sysctl -p /etc/sysctl.d/99-qenex.conf
```

### 2. Security Hardening

```bash
# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 443/tcp # HTTPS
sudo ufw allow 8080/tcp # API
sudo ufw allow 6443/tcp # Kubernetes API
sudo ufw enable

# Install and configure fail2ban
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Disable root SSH login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### 3. Docker Installation

```bash
# Add Docker repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Configure Docker
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker
```

### 4. Kubernetes Setup

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Initialize cluster (on master node)
sudo kubeadm init --pod-network-cidr=10.244.0.0/16

# Configure kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install network plugin
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
```

### 5. Database Cluster

```bash
# Install PostgreSQL
sudo apt-get install -y postgresql-15 postgresql-contrib-15

# Configure PostgreSQL for replication
sudo -u postgres psql << EOF
CREATE USER qenex WITH ENCRYPTED PASSWORD 'secure_password';
CREATE DATABASE qenex_production OWNER qenex;
GRANT ALL PRIVILEGES ON DATABASE qenex_production TO qenex;
EOF

# Configure primary server
cat << EOF | sudo tee -a /etc/postgresql/15/main/postgresql.conf
listen_addresses = '*'
wal_level = replica
max_wal_senders = 3
wal_keep_segments = 64
synchronous_commit = on
EOF

# Setup replication
sudo systemctl restart postgresql
```

### 6. Deploy QENEX Core

```bash
# Clone repositories
git clone https://github.com/abdulrahman305/qenex-os.git
git clone https://github.com/abdulrahman305/qenex-defi.git
git clone https://github.com/abdulrahman305/qxc-token.git

# Build Docker images
cd qenex-os
docker build -t qenex/core:latest .

cd ../qenex-defi
docker build -t qenex/defi:latest .

cd ../qxc-token
docker build -t qenex/token:latest .

# Deploy with Docker Compose
docker-compose -f docker-compose.production.yml up -d
```

### 7. Kubernetes Deployment

```yaml
# qenex-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qenex-core
  namespace: qenex
spec:
  replicas: 3
  selector:
    matchLabels:
      app: qenex-core
  template:
    metadata:
      labels:
        app: qenex-core
    spec:
      containers:
      - name: qenex-core
        image: qenex/core:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: qenex-secrets
              key: database-url
        - name: HSM_ENABLED
          value: "true"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
---
apiVersion: v1
kind: Service
metadata:
  name: qenex-core-service
  namespace: qenex
spec:
  selector:
    app: qenex-core
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

Deploy to Kubernetes:
```bash
kubectl create namespace qenex
kubectl apply -f qenex-deployment.yaml
kubectl get pods -n qenex
```

## Configuration

### Environment Variables
```bash
# Create .env.production file
cat << EOF > .env.production
# Database
DATABASE_URL=postgresql://qenex:password@localhost:5432/qenex_production
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379
REDIS_POOL_SIZE=10

# Security
HSM_ENABLED=true
HSM_SLOT=0
HSM_PIN=secure_pin
ENCRYPTION_KEY=base64_encoded_key

# Banking
SWIFT_ENABLED=true
SEPA_ENABLED=true
ACH_ENABLED=true

# Compliance
KYC_PROVIDER=comply_advantage
AML_THRESHOLD=10000
SANCTIONS_API=https://api.sanctions.io

# Performance
MAX_CONCURRENT_TRANSACTIONS=10000
CACHE_TTL=3600
WORKER_THREADS=16
EOF
```

### SSL/TLS Configuration

```bash
# Generate SSL certificates (production should use CA-signed certs)
sudo certbot certonly --standalone -d api.qenex.ai

# Configure Nginx
cat << EOF | sudo tee /etc/nginx/sites-available/qenex
server {
    listen 443 ssl http2;
    server_name api.qenex.ai;

    ssl_certificate /etc/letsencrypt/live/api.qenex.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.qenex.ai/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/qenex /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## High Availability Setup

### Load Balancer Configuration
```nginx
upstream qenex_backend {
    least_conn;
    server 10.0.1.10:8080 weight=5;
    server 10.0.1.11:8080 weight=5;
    server 10.0.1.12:8080 weight=5;
    keepalive 32;
}
```

### Database Replication
```sql
-- On replica server
CREATE SUBSCRIPTION qenex_sub
    CONNECTION 'host=primary-db port=5432 dbname=qenex_production user=replicator'
    PUBLICATION qenex_pub;
```

### Redis Sentinel
```bash
# Configure Redis Sentinel for HA
redis-sentinel /etc/redis/sentinel.conf
```

## Monitoring & Observability

### Prometheus Configuration
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'qenex-core'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
```

### Grafana Dashboard
Import dashboard ID: 12345 for QENEX monitoring

### Alert Rules
```yaml
groups:
- name: qenex_alerts
  rules:
  - alert: HighTransactionLatency
    expr: qenex_transaction_duration_seconds > 0.5
    for: 5m
    annotations:
      summary: "High transaction latency detected"
  
  - alert: LowDiskSpace
    expr: node_filesystem_free_bytes < 10737418240
    for: 10m
    annotations:
      summary: "Low disk space on node"
```

## Backup & Recovery

### Automated Backups
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backup/qenex/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U qenex qenex_production | gzip > $BACKUP_DIR/database.sql.gz

# Configuration backup
tar -czf $BACKUP_DIR/config.tar.gz /etc/qenex /opt/qenex/config

# Upload to S3
aws s3 sync $BACKUP_DIR s3://qenex-backups/$(date +%Y%m%d)/
```

### Disaster Recovery
```bash
# Restore from backup
gunzip < /backup/database.sql.gz | psql -h localhost -U qenex qenex_production
tar -xzf /backup/config.tar.gz -C /
```

## Performance Tuning

### Database Optimization
```sql
-- Analyze and vacuum
VACUUM ANALYZE;

-- Create indexes
CREATE INDEX idx_transactions_timestamp ON transactions(created_at);
CREATE INDEX idx_accounts_status ON accounts(status) WHERE status = 'active';
```

### Application Tuning
```bash
# JVM options for Java components
export JAVA_OPTS="-Xms4g -Xmx8g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"

# Node.js options
export NODE_OPTIONS="--max-old-space-size=8192"
```

## Security Checklist

- [ ] SSL/TLS certificates installed and configured
- [ ] Firewall rules configured
- [ ] SSH key-only authentication
- [ ] Fail2ban installed and configured
- [ ] Regular security updates scheduled
- [ ] HSM integration tested
- [ ] Encryption keys rotated
- [ ] Audit logging enabled
- [ ] Intrusion detection system active
- [ ] DDoS protection configured

## Maintenance

### Daily Tasks
- Monitor system metrics
- Check error logs
- Verify backup completion
- Review security alerts

### Weekly Tasks
- Performance analysis
- Capacity planning review
- Security patch assessment
- Database optimization

### Monthly Tasks
- Disaster recovery drill
- Security audit
- Performance baseline update
- Documentation review

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Clear cache if needed
sync && echo 3 > /proc/sys/vm/drop_caches
```

#### Transaction Failures
```bash
# Check logs
tail -f /var/log/qenex/transaction.log

# Verify database connectivity
psql -h localhost -U qenex -c "SELECT 1"
```

#### Performance Degradation
```bash
# Check system load
uptime
iostat -x 5

# Profile application
perf record -g -p $(pgrep qenex)
perf report
```

## Support

### Technical Support
- Email: support@qenex.ai
- Phone: +1-800-QENEX-AI
- Slack: qenex-support.slack.com

### Resources
- Documentation: https://docs.qenex.ai
- API Reference: https://api.qenex.ai/docs
- Status Page: https://status.qenex.ai
- Community Forum: https://forum.qenex.ai

## License

Copyright (c) 2024 QENEX AI. All rights reserved.

This deployment guide is proprietary and confidential.