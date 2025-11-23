# DateNow Deployment Guide

## Overview

This guide covers deploying DateNow to production environments.

## Prerequisites

- Docker & Docker Compose
- Domain name configured
- SSL certificates (Let's Encrypt recommended)
- Google Gemini API Key
- Server with minimum specs:
  - 2 CPU cores
  - 4GB RAM
  - 20GB storage
  - Ubuntu 22.04 LTS (recommended)

## Production Environment Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Create app directory
sudo mkdir -p /opt/datenow
sudo chown $USER:$USER /opt/datenow
cd /opt/datenow
```

### 2. Clone Repository

```bash
git clone https://github.com/yourusername/datenow.git .
```

### 3. Environment Configuration

Create production `.env` file:

```bash
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://datenow:CHANGE_THIS_PASSWORD@postgres:5432/datenow

# Redis
REDIS_URL=redis://redis:6379

# AI Configuration
GEMINI_API_KEY=your_production_gemini_api_key

# Security - CHANGE THESE!
JWT_SECRET_KEY=generate_secure_random_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
ENVIRONMENT=production
DEBUG=False
API_V1_STR=/api/v1
PROJECT_NAME=DateNow

# CORS - Update with your domain
BACKEND_CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]

# Frontend
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
EOF
```

Generate secure secrets:
```bash
# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate strong database password
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

### 4. SSL/TLS Configuration

Using Let's Encrypt with Nginx:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 5. Nginx Configuration

Create `/etc/nginx/sites-available/datenow`:

```nginx
# Frontend
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend API
server {
    listen 80;
    listen [::]:80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable configuration:
```bash
sudo ln -s /etc/nginx/sites-available/datenow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Production Docker Compose

Update `docker-compose.yml` for production:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: datenow_postgres
    restart: always
    environment:
      POSTGRES_USER: datenow
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: datenow
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - datenow_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U datenow"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: datenow_redis
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - datenow_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: datenow_backend
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - datenow_network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    container_name: datenow_frontend
    restart: always
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - datenow_network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  datenow_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

### 7. Production Dockerfiles

**backend/Dockerfile.prod**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

**frontend/Dockerfile.prod**:
```dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 8. Deploy Application

```bash
# Build and start services
docker-compose -f docker-compose.yml up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Run database migrations (if using Alembic)
docker-compose exec backend alembic upgrade head

# Seed initial data
docker-compose exec backend python seed_data.py
```

## Monitoring & Maintenance

### Database Backups

Create backup script `/opt/datenow/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/datenow/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="datenow_backup_$DATE.sql"

docker-compose exec -T postgres pg_dump -U datenow datenow > "$BACKUP_DIR/$FILENAME"
gzip "$BACKUP_DIR/$FILENAME"

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $FILENAME.gz"
```

Setup cron job:
```bash
chmod +x /opt/datenow/backup.sh
crontab -e
# Add: 0 2 * * * /opt/datenow/backup.sh
```

### Log Management

```bash
# View application logs
docker-compose logs backend
docker-compose logs frontend

# Follow logs in real-time
docker-compose logs -f backend

# Export logs
docker-compose logs backend > backend.log
```

### Health Monitoring

Create health check script:

```bash
#!/bin/bash
# health-check.sh

API_URL="https://api.yourdomain.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✓ API is healthy"
else
    echo "✗ API health check failed (HTTP $RESPONSE)"
    # Send alert (email, Slack, etc.)
fi
```

### Performance Monitoring

Recommended tools:
- **Application**: Sentry for error tracking
- **Infrastructure**: Prometheus + Grafana
- **Uptime**: UptimeRobot or Pingdom
- **Logs**: ELK Stack or Loki

### Scaling

#### Horizontal Scaling

Update docker-compose.yml to scale backend:

```yaml
backend:
  deploy:
    replicas: 3
```

Add load balancer (nginx upstream):

```nginx
upstream backend_servers {
    least_conn;
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}
```

#### Database Scaling

For production workloads:
1. Use managed PostgreSQL (AWS RDS, Digital Ocean Managed DB)
2. Implement read replicas
3. Use connection pooling (PgBouncer)
4. Optimize queries and add indexes

### Security Checklist

- [ ] SSL/TLS certificates installed and auto-renewing
- [ ] Strong passwords for all services
- [ ] JWT secret keys are cryptographically secure
- [ ] Database not exposed to public internet
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Regular security updates
- [ ] Firewall configured (UFW)
- [ ] Fail2ban installed for SSH protection
- [ ] Regular backups tested
- [ ] Secrets not in version control
- [ ] User input sanitized
- [ ] API authentication required

### Firewall Configuration

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Updates & Maintenance

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Clean up unused images
docker system prune -a
```

### Rollback Procedure

```bash
# Revert to previous version
git checkout <previous-commit>
docker-compose down
docker-compose up -d --build

# Restore database backup if needed
gunzip < backups/datenow_backup_DATE.sql.gz | \
  docker-compose exec -T postgres psql -U datenow datenow
```

## Cloud Platform Deployment

### AWS Deployment

- Use ECS/Fargate for containers
- RDS for PostgreSQL
- ElastiCache for Redis
- S3 for file storage
- CloudFront for CDN
- Route53 for DNS

### Google Cloud Platform

- Use Cloud Run for containers
- Cloud SQL for PostgreSQL
- Memorystore for Redis
- Cloud Storage for files
- Cloud CDN

### Digital Ocean

- Use App Platform (easiest)
- Or Droplets with Docker
- Managed PostgreSQL
- Managed Redis
- Spaces for storage

## Cost Optimization

1. Use managed services for database/cache
2. Implement CDN for static assets
3. Enable compression (gzip)
4. Optimize images
5. Use appropriate instance sizes
6. Monitor API costs (Gemini)
7. Implement caching strategies

## Troubleshooting Production Issues

### High CPU Usage
```bash
docker stats
# Scale backend or optimize code
```

### Memory Issues
```bash
docker-compose restart backend
# Add memory limits in docker-compose
```

### Database Connection Issues
```bash
docker-compose logs postgres
# Check connection pool settings
```

### SSL Certificate Renewal
```bash
sudo certbot renew --dry-run
sudo certbot renew
```

## Support & Monitoring

- Set up uptime monitoring
- Configure error alerting (Sentry)
- Monitor API rate limits
- Track database performance
- Monitor disk usage

---

For issues or questions, contact: support@datenow.app
