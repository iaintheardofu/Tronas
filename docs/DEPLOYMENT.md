# Deployment Guide

This guide covers deploying the Texas PIA Request Automation System in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Azure Deployment](#azure-deployment)
- [Database Migrations](#database-migrations)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- Docker 20.10+ and Docker Compose 2.0+
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- PostgreSQL 15+ (for local development without Docker)
- Redis 7+ (for local development without Docker)

### Required Accounts and Credentials

1. **Azure AD Application**
   - Register an application in Azure Active Directory
   - Configure API permissions for Microsoft Graph:
     - `Mail.Read` (Application)
     - `Files.Read.All` (Application)
     - `Sites.Read.All` (Application)
     - `User.Read.All` (Application)
   - Generate a client secret

2. **OpenAI API Key**
   - Obtain from https://platform.openai.com
   - Ensure GPT-4 access is enabled

## Local Development

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example .env
# Edit .env with your credentials

# Start PostgreSQL and Redis (if not using Docker)
# ... or use Docker for just the databases:
docker-compose up -d db redis

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Running with Docker Compose (Recommended)

```bash
# From project root
cp .env.example .env
# Edit .env with your credentials

# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Docker Deployment

### Building Images

```bash
# Build backend image
docker build -t pia-backend:latest ./backend

# Build frontend image
docker build -t pia-frontend:latest ./frontend
```

### Production Docker Compose

Create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    image: pia-backend:latest
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEBUG=false
    ports:
      - "8000:8000"
    restart: always
    depends_on:
      - db
      - redis

  celery-worker:
    image: pia-backend:latest
    command: celery -A app.worker worker --loglevel=info
    environment:
      # Same as backend
    restart: always
    depends_on:
      - db
      - redis

  celery-beat:
    image: pia-backend:latest
    command: celery -A app.worker beat --loglevel=info
    environment:
      # Same as backend
    restart: always
    depends_on:
      - redis

  frontend:
    image: pia-frontend:latest
    ports:
      - "80:80"
      - "443:443"
    restart: always

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=pia_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: always

volumes:
  postgres_data:
  redis_data:
```

## Azure Deployment

### Azure Container Apps

1. **Create Resource Group**
   ```bash
   az group create --name pia-rg --location eastus
   ```

2. **Create Container Registry**
   ```bash
   az acr create --resource-group pia-rg --name piacr --sku Basic
   az acr login --name piacr
   ```

3. **Push Images**
   ```bash
   docker tag pia-backend:latest piacr.azurecr.io/pia-backend:latest
   docker tag pia-frontend:latest piacr.azurecr.io/pia-frontend:latest
   docker push piacr.azurecr.io/pia-backend:latest
   docker push piacr.azurecr.io/pia-frontend:latest
   ```

4. **Create Container Apps Environment**
   ```bash
   az containerapp env create \
     --name pia-env \
     --resource-group pia-rg \
     --location eastus
   ```

5. **Deploy Backend**
   ```bash
   az containerapp create \
     --name pia-backend \
     --resource-group pia-rg \
     --environment pia-env \
     --image piacr.azurecr.io/pia-backend:latest \
     --target-port 8000 \
     --ingress external \
     --registry-server piacr.azurecr.io \
     --env-vars "DATABASE_URL=secretref:database-url" "SECRET_KEY=secretref:secret-key"
   ```

### Azure PostgreSQL

```bash
az postgres flexible-server create \
  --resource-group pia-rg \
  --name pia-postgres \
  --admin-user adminuser \
  --admin-password <secure-password> \
  --sku-name Standard_B1ms \
  --version 15
```

### Azure Redis Cache

```bash
az redis create \
  --resource-group pia-rg \
  --name pia-redis \
  --sku Basic \
  --vm-size C0
```

## Database Migrations

### Creating Migrations

```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new field to document model"

# Review the generated migration in migrations/versions/
# Then apply:
alembic upgrade head
```

### Rolling Back

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Migration Best Practices

1. Always review auto-generated migrations before applying
2. Test migrations on a staging database first
3. Keep migrations small and focused
4. Never edit a migration that has been deployed to production

## Monitoring

### Logging

The application uses structured logging with Loguru. In production, configure log aggregation:

```python
# Example: Send logs to external service
logger.add(
    "https://logs.example.com/ingest",
    format="{time} {level} {message}",
    level="INFO"
)
```

### Health Checks

- **Backend Health:** `GET /health`
- **API Status:** `GET /`

### Recommended Monitoring Stack

1. **Application Performance:** Azure Application Insights or Datadog
2. **Infrastructure:** Azure Monitor or Prometheus + Grafana
3. **Log Aggregation:** Azure Log Analytics or ELK Stack
4. **Alerting:** PagerDuty or Azure Alerts

### Key Metrics to Monitor

- API response times (p50, p95, p99)
- Error rates by endpoint
- Database connection pool usage
- Redis memory usage
- Celery task queue length
- Classification throughput
- Deadline compliance rate

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check PostgreSQL is running
docker-compose ps db

# Check connection string format
# Should be: postgresql+asyncpg://user:pass@host:5432/dbname
```

**Redis Connection Errors**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

**Celery Workers Not Processing**
```bash
# Check worker logs
docker-compose logs celery-worker

# Verify Redis connection
celery -A app.worker inspect ping
```

**Microsoft Graph API Errors**
1. Verify Azure AD credentials in .env
2. Check API permissions are granted
3. Ensure admin consent is provided for application permissions

**Classification Errors**
1. Verify OpenAI API key is valid
2. Check API quota and rate limits
3. Review document content for extraction issues

### Getting Help

- Review application logs in `docker-compose logs`
- Check the `/api/v1/docs` endpoint for API documentation
- Contact the development team for support
