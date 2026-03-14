# 🚀 Deployment Guide

How to deploy the AI Trading Agent Platform to a production server for 24/7 automated operation.

---

## Deployment Options

| Option | Best For | Cost | Complexity |
|--------|----------|------|-----------|
| **Local PC** | Development, testing | Free | Low |
| **VPS (DigitalOcean/AWS)** | Production deployment | $5–20/mo | Medium |
| **Docker** | Reproducible deployments | Free + hosting | Medium |
| **Cloud Run / Lambda** | Serverless | Pay-per-use | High |
| **Raspberry Pi** | Home server | $50 one-time | Medium |

---

## Option 1 — Local PC (Windows)

### Setup as a Windows Service

```bash
# Install as a scheduled task using Windows Task Scheduler
# 1. Open Task Scheduler
# 2. Create Basic Task → Name: "AI Trading Agent"
# 3. Trigger: Daily at 8:45 AM
# 4. Action: Start a program
#    Program: python
#    Arguments: -m ai_trading_agent.main --mode trade
#    Start in: D:\Trading
# 5. Settings: Stop task if runs longer than 8 hours
```

### Auto-start Script

Create `start_trading.bat`:

```batch
@echo off
cd /d D:\Trading
call venv\Scripts\activate
python -m ai_trading_agent.main --mode trade 2>&1 >> logs\startup.log
```

---

## Option 2 — VPS Deployment (Linux)

### Step 1 — Provision Server

Recommended specs:
- **CPU**: 2 vCPU
- **RAM**: 4 GB
- **Storage**: 20 GB SSD
- **OS**: Ubuntu 22.04 LTS
- **Provider**: DigitalOcean, AWS EC2, Linode, or Vultr

### Step 2 — Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.10 python3.10-venv python3-pip -y

# Clone repository
git clone <repository-url> /opt/ai-trading-agent
cd /opt/ai-trading-agent

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### Step 3 — Configure Environment

```bash
cp .env.example .env
nano .env   # Set your Flattrade + Telegram credentials
```

### Step 4 — Create systemd Service

```bash
sudo tee /etc/systemd/system/ai-trading.service > /dev/null <<EOF
[Unit]
Description=AI Trading Agent Platform
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ai-trading-agent
Environment=PATH=/opt/ai-trading-agent/venv/bin
ExecStart=/opt/ai-trading-agent/venv/bin/python -m ai_trading_agent.main --mode trade
Restart=on-failure
RestartSec=30

# Market hours only (IST 8:45 AM = UTC 3:15 AM)
# Use a timer instead for market-hours-only operation

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ai-trading
sudo systemctl start ai-trading

# Check status
sudo systemctl status ai-trading

# View logs
sudo journalctl -u ai-trading -f
```

### Step 5 — Market Hours Timer (optional)

```bash
sudo tee /etc/systemd/system/ai-trading.timer > /dev/null <<EOF
[Unit]
Description=Start AI Trading during market hours

[Timer]
OnCalendar=Mon..Fri 03:15 UTC
Unit=ai-trading.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl enable ai-trading.timer
```

---

## Option 3 — Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment variables
ENV EXECUTION_MODE=paper
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=60s --timeout=10s \
  CMD python -c "import requests; requests.get('http://localhost:8501')" || exit 1

# Default command
CMD ["python", "-m", "ai_trading_agent.main", "--mode", "trade"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  trading-agent:
    build: .
    container_name: ai-trading-agent
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./models/saved:/app/models/saved
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  dashboard:
    build: .
    container_name: ai-trading-dashboard
    command: streamlit run ai_trading_agent/dashboard/app.py --server.port=8501
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Run with Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f trading-agent

# Stop
docker-compose down
```

---

## Option 4 — Cloud Deployment (Google Cloud Run)

```bash
# Build container
gcloud builds submit --tag gcr.io/YOUR_PROJECT/ai-trading-agent

# Deploy to Cloud Run
gcloud run deploy ai-trading-agent \
  --image gcr.io/YOUR_PROJECT/ai-trading-agent \
  --platform managed \
  --region asia-south1 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars EXECUTION_MODE=paper \
  --no-allow-unauthenticated
```

---

## Monitoring in Production

### Log Management

```bash
# Application logs
tail -f logs/trading_agent.log

# System service logs
sudo journalctl -u ai-trading --since "today"

# Docker logs
docker logs -f ai-trading-agent --tail 100
```

### Alerts Setup

The Telegram bot already provides production monitoring:

| Alert Type | When |
|------------|------|
| 🚀 System Start | Agent initialised successfully |
| ⏹️ System Stop | Graceful shutdown |
| 🚨 Error | Any critical exception |
| 📋 Daily Summary | 3:30 PM IST with P&L |
| 🟢/🔴 Trade Signals | Every trade entry |
| 🎯/🛑 Trade Updates | Every trade exit |

### Health Checks

```bash
# Check if process is running
ps aux | grep ai_trading_agent

# Check log activity
tail -1 logs/trading_agent.log

# Check data freshness
ls -la data/paper_trading_state.json
```

---

## Backup Strategy

### Critical Files to Backup

```
data/paper_trading_state.json    # Trading state
data/performance_*.json          # Historical performance
models/saved/rl_agent.pkl        # RL agent checkpoint
models/saved/*.pkl               # ML model checkpoints
.env                             # Configuration (encrypted/secured)
logs/trading_agent.log           # Audit trail
```

### Automated Backup (cron)

```bash
# Daily backup at midnight
0 0 * * * tar czf /backup/ai-trading-$(date +\%Y\%m\%d).tar.gz /opt/ai-trading-agent/data /opt/ai-trading-agent/models/saved
```

---

## Security Considerations

1. **Never commit `.env`** — Add to `.gitignore`
2. **Restrict API access** — Use IP whitelisting on Flattrade if available
3. **Use HTTPS** — Ensure all API communication is encrypted
4. **Limit server access** — SSH keys only, no password auth
5. **Monitor unusual activity** — Set up alerts for unexpected trades or errors
6. **Regular updates** — Keep Python packages updated for security patches
