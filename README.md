🚀 Server Monitoring System with WhatsApp & Teams Alerts

https://img.shields.io/badge/Status-Production%2520Ready-brightgreen
https://img.shields.io/badge/Python-3.9+-blue
https://img.shields.io/badge/Docker-%E2%9C%93-blue
https://img.shields.io/badge/WhatsApp-%E2%9C%93-green
https://img.shields.io/badge/Teams-%E2%9C%93-blue

A comprehensive, production-ready monitoring system that tracks server availability and sends instant alerts via WhatsApp and Microsoft Teams. Features a modern web dashboard, REST API, and Docker containerization.
📋 Table of Contents

    🌟 Features

    🏗️ Architecture

    🚀 Quick Start

    ⚙️ Configuration

    📡 Monitoring Setup

    📱 Alert System

    🌐 Web Dashboard

    🔌 API Reference

    🐳 Docker Deployment

    🔧 Troubleshooting

    📈 Production Deployment

    🤝 Contributing

🌟 Features
🔍 Monitoring Capabilities

    Multi-protocol Support: Monitor TCP, HTTP, and HTTPS services

    Real-time Detection: Instant status change detection (down/up)

    Configurable Intervals: Adjustable check intervals (default: 60 seconds)

    Timeout Handling: Configurable connection timeouts

    Bulk Monitoring: Monitor unlimited hosts simultaneously

📱 Alert System

    WhatsApp Notifications: Via Twilio API

    Microsoft Teams Integration: Webhook-based alerts

    Separate Channels: Different messages for users and administrators

    Customizable Messages: Fully configurable alert templates

    Multi-recipient Support: Send to multiple WhatsApp numbers

    Email Backups: Optional email notifications (Gmail/SMTP)

🖥️ Management Interface

    Modern Dashboard: Real-time web interface with charts

    REST API: Full API for integration with other systems

    Status Filtering: Filter by up/down/unknown status

    Manual Checks: Force immediate host verification

    Responsive Design: Mobile-friendly interface

🏗️ Infrastructure

    Docker Containerized: Easy deployment and scaling

    Configuration Files: YAML-based host configuration

    Environment Variables: Secure credential management

    Logging: Comprehensive log system with rotation

    Health Checks: Built-in monitoring of the monitor itself

🏗️ Architecture

graph TB
    A[Monitoring Server] --> B[Host Monitor]
    B --> C[TCP Checks]
    B --> D[HTTP Checks]
    B --> E[HTTPS Checks]
    
    A --> F[Alert Notifier]
    F --> G[WhatsApp via Twilio]
    F --> H[Microsoft Teams]
    F --> I[Email Backup]
    
    A --> J[REST API]
    A --> K[Web Dashboard]
    
    L[Configuration] --> B
    L --> F
    
    M[External Services] --> C
    M --> D
    M --> E
    
    N[Admin Users] --> G
    N --> H
    N --> I
    
    O[End Users] --> K
    O --> P[Web Browser]

🚀 Quick Start
Prerequisites

    Docker and Docker Compose

    Python 3.9+ (for development)

    Twilio account (for WhatsApp alerts)

    Microsoft Teams (optional, for Teams alerts)

Installation

    Clone and Setup

bash

git clone <repository-url>
cd server-monitoring-system

    Configure Environment

bash

cp .env.example .env
# Edit .env with your credentials

    Configure Hosts

bash

cp config/hosts.yaml.example config/hosts.yaml
# Edit config/hosts.yaml with your servers

    Deploy with Docker

bash

docker-compose up -d

    Verify Installation

bash

# Check service health
curl http://localhost:8080/health

# Access dashboard
# Open: http://localhost:8080/dashboard

⚙️ Configuration
Environment Variables (.env)
env

# Twilio Configuration (WhatsApp)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886

# WhatsApp Numbers (comma-separated)
ADMIN_WHATSAPP_NUMBERS=+1234567890,+1234567891
USER_WHATSAPP_NUMBERS=+1234567892,+1234567893

# Microsoft Teams Webhooks
TEAMS_ADMIN_WEBHOOK=https://yourcompany.webhook.office.com/...
TEAMS_USER_WEBHOOK=https://yourcompany.webhook.office.com/...

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
ADMIN_EMAILS=admin@company.com
USER_EMAILS=notifications@company.com

# Monitoring Settings
CHECK_INTERVAL=60      # Check every 60 seconds
TIMEOUT=10            # Connection timeout in seconds

Host Configuration (config/hosts.yaml)
yaml

hosts:
  # Example: HTTP Web Server
  - name: "Production Web Server"
    hostname: "web.example.com"
    ip_address: "192.168.1.100"
    port: 443
    check_type: "https"  # Options: tcp, http, https
    
  # Example: Database Server
  - name: "Database Cluster"
    hostname: "db.example.com"
    ip_address: "192.168.1.101"
    port: 5432
    check_type: "tcp"
    
  # Example: API Gateway
  - name: "API Gateway"
    hostname: "api.example.com"
    ip_address: "192.168.1.102"
    port: 8080
    check_type: "http"

alert_messages:
  user:
    downtime: "We are aware of the downtime and we are working on it. It will be fixed within the next 15 minutes."
    resolved: "The downtime has been resolved. Thank you for your patience."
  
  admin:
    downtime: "Server {hostname} ({ip_address}) is down at {timestamp}"
    resolved: "Host {hostname} ({ip_address}) is back online at {timestamp}"

📡 Monitoring Setup
Supported Check Types
Type	Description	Example Ports
tcp	Basic TCP port connectivity	22 (SSH), 53 (DNS), 3306 (MySQL)
http	HTTP service with status codes	80 (HTTP), 8080 (HTTP Alt)
https	HTTPS service with SSL/TLS	443 (HTTPS)
Adding New Hosts

    Edit the configuration file:

bash

nano config/hosts.yaml

    Add a new host entry:

yaml

- name: "New Server"
  hostname: "server.example.com"
  ip_address: "192.168.1.200"
  port: 22
  check_type: "tcp"

    Apply changes:

bash

docker-compose restart monitoring-server

Validation Rules

    Port: Must be between 1-65535

    Check Type: Must be tcp, http, or https

    Required Fields: name, hostname, ip_address, port, check_type

📱 Alert System
WhatsApp Setup

    Create a Twilio Account

        Visit Twilio Console

        Sign up for a free account

        Note your Account SID and Auth Token

    Configure WhatsApp Sandbox

        Navigate to Messaging → Try it out → Send a WhatsApp message

        Join the sandbox by sending the code to the provided number

        Use the sandbox number as TWILIO_WHATSAPP_NUMBER

    Add Recipients

        Add phone numbers to ADMIN_WHATSAPP_NUMBERS and USER_WHATSAPP_NUMBERS

        Format: +1234567890 (with country code)

        Separate multiple numbers with commas

Microsoft Teams Setup

    Create Incoming Webhook

        Open Teams and navigate to your channel

        Click "⋯" (More options) → "Connectors"

        Search for "Incoming Webhook" and add it

        Configure and copy the webhook URL

    Configure Webhooks

        Add admin webhook to TEAMS_ADMIN_WEBHOOK

        Add user webhook to TEAMS_USER_WEBHOOK

Alert Messages

User Messages (Non-technical):

    Downtime: "We are aware of the downtime and we are working on it. It will be fixed within the next 15 minutes."

    Resolved: "The downtime has been resolved. Thank you for your patience."

Admin Messages (Technical):

    Downtime: "Server {hostname} ({ip_address}) is down at {timestamp}"

    Resolved: "Host {hostname} ({ip_address}) is back online at {timestamp}"

Variables Available:

    {hostname}: Server hostname

    {ip_address}: Server IP address

    {timestamp}: Time of status change

    {name}: Server display name

    {port}: Server port number

Testing Alerts
bash

# Test downtime alert
curl http://localhost:8080/test-alert/downtime

# Test resolved alert
curl http://localhost:8080/test-alert/resolved

🌐 Web Dashboard
Features

    Real-time Status

        Live updates every 30 seconds

        Color-coded status indicators

        Last check timestamps

    Visual Analytics

        Doughnut chart showing status distribution

        Summary cards with counts

        Historical status tracking

    Interactive Controls

        Manual check buttons

        Status filtering (All/Up/Down/Unknown)

        Auto-refresh toggle

    Responsive Design

        Mobile-friendly interface

        Adaptive layout for different screen sizes

        Touch-friendly controls

Accessing the Dashboard

    Via Browser:
    text

    http://your-server:8080/dashboard

    Via API:
    bash

    # Get dashboard data as JSON
    curl http://localhost:8080/api/summary

Dashboard Components
javascript

// Example dashboard data structure
{
  "summary": {
    "total": 5,
    "up": 4,
    "down": 1,
    "unknown": 0
  },
  "hosts": [
    {
      "name": "Web Server",
      "status": "up",
      "last_check": "2024-01-30T10:30:45",
      "downtime_start": null
    }
  ]
}

🔌 API Reference
Base URL
text

http://localhost:8080

Endpoints
GET /

Description: Service information and API endpoints
Response:
json

{
  "service": "Server Monitoring System",
  "status": "running",
  "monitored_hosts": 5,
  "api_endpoints": {
    "status": "/status",
    "health": "/health",
    "hosts": "/hosts",
    "manual_check": "/check/<host_index>",
    "test_alert": "/test-alert/<alert_type>",
    "dashboard": "/dashboard",
    "api_summary": "/api/summary"
  }
}

GET /health

Description: Health check endpoint for load balancers
Response:
json

{
  "status": "healthy",
  "timestamp": "2024-01-30T10:30:45.123456"
}

GET /status

Description: Detailed status of all monitored hosts
Response:
json

{
  "timestamp": "2024-01-30T10:30:45.123456",
  "summary": {
    "total_hosts": 5,
    "up_hosts": 4,
    "down_hosts": 1,
    "unknown_hosts": 0
  },
  "hosts": [
    {
      "name": "Web Server",
      "hostname": "web.example.com",
      "ip_address": "192.168.1.100",
      "port": 443,
      "check_type": "https",
      "current_status": "up",
      "last_check": "2024-01-30T10:30:45",
      "last_status_change": "2024-01-30T09:15:30",
      "downtime_start": null,
      "check_count": 150
    }
  ]
}

GET /hosts

Description: List all configured hosts
Response: Array of host configurations
GET /check/<int:host_index>

Description: Manually check a specific host
Parameters: host_index (0-based index from hosts list)
Response:
json

{
  "host": "Web Server",
  "status": "up",
  "timestamp": "2024-01-30T10:30:45.123456"
}

GET /test-alert/<alert_type>

Description: Test alert functionality
Parameters: alert_type (downtime or resolved)
Response:
json

{
  "message": "Test downtime alert sent"
}

GET /api/summary

Description: Dashboard data in JSON format
Response: Summary and host details for dashboard
🐳 Docker Deployment
Docker Compose Configuration
yaml

version: '3.8'

services:
  monitoring-server:
    build: .
    container_name: server-monitoring
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
      - ./templates:/app/templates:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

Docker Commands
bash

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f monitoring-server

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild with changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check container status
docker-compose ps

# View resource usage
docker-compose stats

Dockerfile
dockerfile

FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create log directory
RUN mkdir -p logs

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "app.py"]

Volume Mounts
Host Path	Container Path	Purpose
./logs	/app/logs	Application logs
./config	/app/config	Configuration files
./templates	/app/templates	HTML templates
🔧 Troubleshooting
Common Issues
1. WhatsApp Alerts Not Received
bash

# Check Twilio configuration
docker-compose logs | grep -i "whatsapp\|twilio"

# Verify credentials are set
grep "TWILIO" .env

# Test Twilio connection
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/{AccountSID}/Messages.json" \
  --data-urlencode "Body=Test" \
  --data-urlencode "From=whatsapp:+14155238886" \
  --data-urlencode "To=whatsapp:+1234567890" \
  -u "{AccountSID}:{AuthToken}"

2. Hosts Showing as DOWN
bash

# Check connectivity manually
nc -zv 8.8.8.8 53
curl -I http://google.com

# Increase timeout in .env
echo "TIMEOUT=30" >> .env
docker-compose restart

# Check firewall
sudo ufw status

3. Dashboard Not Loading
bash

# Check if service is running
curl http://localhost:8080/health

# Check container status
docker-compose ps

# Check port binding
netstat -tlnp | grep 8080

4. Configuration Not Loading
bash

# Check config file permissions
ls -la config/hosts.yaml

# Check Docker volume mount
docker exec server-monitoring ls -la /app/config

# View config loading logs
docker-compose logs | grep -i "config"

Log Files

    Container logs: docker-compose logs monitoring-server

    Application logs: logs/monitoring.log (inside container, mapped to host)

    Access logs: Automatic logging of all HTTP requests

Debug Mode

Enable debug logging by modifying config/settings.py:
python

LOGGING_CONFIG = {
    # ...
    'loggers': {
        'monitoring': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',  # Change from INFO to DEBUG
            'propagate': True
        }
    }
}

📈 Production Deployment
Security Recommendations

    Use HTTPS

bash

# Add reverse proxy (nginx example)
# nginx.conf:
server {
    listen 443 ssl;
    server_name monitor.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

    Secure Environment Variables

bash

# Set proper permissions
chmod 600 .env
chmod 700 config/

    Network Security

bash

# Configure firewall
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 22/tcp   # SSH
sudo ufw enable

High Availability

    Multiple Instances

yaml

# docker-compose.prod.yml
services:
  monitoring-server:
    deploy:
      replicas: 3
      restart_policy:
        condition: any

    Database Backend (for persistence)

yaml

services:
  monitoring-server:
    # ... existing config ...
    depends_on:
      - redis
    
  redis:
    image: redis:alpine
    volumes:
      - redis-data:/data

volumes:
  redis-data:

    Load Balancer

yaml

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - monitoring-server

Backup Strategy

    Configuration Backup

bash

# Backup script
#!/bin/bash
BACKUP_DIR="/backups/monitoring"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/config_$TIMESTAMP.tar.gz \
  config/ \
  .env \
  docker-compose.yml

# Keep last 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

    Log Rotation

python

# In config/settings.py
LOGGING_CONFIG = {
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'monitoring.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        }
    }
}

Monitoring the Monitor

Add self-monitoring to your config:
yaml

hosts:
  - name: "Monitoring System"
    hostname: "monitor.example.com"
    ip_address: "YOUR_SERVER_IP"
    port: 8080
    check_type: "http"

Performance Tuning

    Adjust Check Intervals

env

# For critical services
CHECK_INTERVAL=30

# For less critical services
CHECK_INTERVAL=300

    Connection Pooling

python

# In monitoring/monitor.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)

🤝 Contributing
Development Setup

    Clone Repository

bash

git clone https://github.com/yourusername/server-monitoring-system.git
cd server-monitoring-system

    Create Virtual Environment

bash

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

    Install Dependencies

bash

pip install -r requirements.txt

    Run in Development Mode

bash

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

# Run application
python app.py

Project Structure
text

server-monitoring-system/
├── config/                 # Configuration files
│   ├── settings.py        # Application settings
│   └── hosts.yaml         # Host configuration
├── monitoring/            # Core monitoring logic
│   ├── monitor.py         # Host monitoring
│   └── notifier.py        # Alert notifications
├── templates/             # HTML templates
│   └── dashboard.html     # Web dashboard
├── logs/                  # Application logs
├── tests/                 # Unit tests
├── docker-compose.yml     # Docker Compose
├── Dockerfile            # Docker configuration
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
└── app.py               # Main application

Testing
bash

# Run unit tests
python -m pytest tests/

# Test specific module
python -m pytest tests/test_monitor.py -v

# Run with coverage
python -m pytest --cov=monitoring tests/

Code Style
bash

# Format code with black
black .

# Check code style with flake8
flake8 .

# Sort imports with isort
isort

    Twilio for WhatsApp API

    Microsoft Teams for webhook integration

    Flask for web framework

    Docker for containerization

    Chart.js for dashboard charts

📞 Support

For support, please:

    Check the Troubleshooting section

    Review the GitHub Issues

    Create a new issue with detailed information

Happy Monitoring! 🚀

If you find this project useful, please consider giving it a star on GitHub!
