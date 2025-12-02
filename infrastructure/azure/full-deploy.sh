#!/bin/bash
# ============================================================================
# TRONAS PIA PLATFORM - FULL AZURE DEPLOYMENT SCRIPT
# ============================================================================
# This script deploys the complete Tronas infrastructure to Azure including:
# - Resource Group
# - Azure Container Registry (ACR)
# - Azure Container Apps Environment
# - PostgreSQL Flexible Server
# - Redis Cache
# - Storage Account
# - Frontend, Backend API, and Worker containers
# - Custom domain configuration for tronas.ai
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="tronas-prod-rg"
LOCATION="southcentralus"
ENVIRONMENT="prod"
PREFIX="tronas"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                   TRONAS PIA PLATFORM DEPLOYMENT                      ║"
echo "║                    Azure Container Apps Setup                         ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================================
# STEP 1: Verify Azure CLI Login
# ============================================================================
echo -e "\n${YELLOW}[Step 1/12] Verifying Azure CLI login...${NC}"

if ! az account show &> /dev/null; then
    echo -e "${RED}Not logged in to Azure. Please run: az login${NC}"
    exit 1
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
echo -e "${GREEN}✓ Logged in to Azure${NC}"
echo "  Subscription: $SUBSCRIPTION"
echo "  Tenant ID: $TENANT_ID"

# ============================================================================
# STEP 2: Create Resource Group
# ============================================================================
echo -e "\n${YELLOW}[Step 2/12] Creating resource group...${NC}"

az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none

echo -e "${GREEN}✓ Resource group created: $RESOURCE_GROUP${NC}"

# ============================================================================
# STEP 3: Create Azure Container Registry
# ============================================================================
echo -e "\n${YELLOW}[Step 3/12] Creating Azure Container Registry...${NC}"

ACR_NAME="${PREFIX}acr$(openssl rand -hex 4)"

az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true \
    --output none

ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

echo -e "${GREEN}✓ Container Registry created: $ACR_LOGIN_SERVER${NC}"

# ============================================================================
# STEP 4: Create Log Analytics Workspace
# ============================================================================
echo -e "\n${YELLOW}[Step 4/12] Creating Log Analytics workspace...${NC}"

LOG_ANALYTICS_NAME="${PREFIX}-logs-$(openssl rand -hex 4)"

az monitor log-analytics workspace create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name $LOG_ANALYTICS_NAME \
    --location $LOCATION \
    --output none

LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
    --resource-group $RESOURCE_GROUP \
    --workspace-name $LOG_ANALYTICS_NAME \
    --query customerId -o tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
    --resource-group $RESOURCE_GROUP \
    --workspace-name $LOG_ANALYTICS_NAME \
    --query primarySharedKey -o tsv)

echo -e "${GREEN}✓ Log Analytics workspace created${NC}"

# ============================================================================
# STEP 5: Create Container Apps Environment
# ============================================================================
echo -e "\n${YELLOW}[Step 5/12] Creating Container Apps environment...${NC}"

az containerapp env create \
    --name "${PREFIX}-env" \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --logs-workspace-id $LOG_ANALYTICS_ID \
    --logs-workspace-key $LOG_ANALYTICS_KEY \
    --output none

echo -e "${GREEN}✓ Container Apps environment created${NC}"

# ============================================================================
# STEP 6: Create PostgreSQL Flexible Server
# ============================================================================
echo -e "\n${YELLOW}[Step 6/12] Creating PostgreSQL database...${NC}"

POSTGRES_NAME="${PREFIX}-postgres-$(openssl rand -hex 4)"
POSTGRES_ADMIN="tronas_admin"
POSTGRES_PASSWORD="Tronas$(openssl rand -hex 12)!"

az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_NAME \
    --location $LOCATION \
    --admin-user $POSTGRES_ADMIN \
    --admin-password "$POSTGRES_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 15 \
    --yes \
    --output none

# Create database
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $POSTGRES_NAME \
    --database-name tronas \
    --output none

# Allow Azure services
az postgres flexible-server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_NAME \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    --output none

POSTGRES_HOST="${POSTGRES_NAME}.postgres.database.azure.com"
DATABASE_URL="postgresql+asyncpg://${POSTGRES_ADMIN}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/tronas?sslmode=require"

echo -e "${GREEN}✓ PostgreSQL created: $POSTGRES_HOST${NC}"

# ============================================================================
# STEP 7: Create Redis Cache
# ============================================================================
echo -e "\n${YELLOW}[Step 7/12] Creating Redis Cache...${NC}"

REDIS_NAME="${PREFIX}-redis-$(openssl rand -hex 4)"

az redis create \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --location $LOCATION \
    --sku Basic \
    --vm-size c0 \
    --output none

# Wait for Redis to be ready
echo "  Waiting for Redis to provision (this may take 5-10 minutes)..."
az redis show --resource-group $RESOURCE_GROUP --name $REDIS_NAME --query "provisioningState" -o tsv
while [ "$(az redis show --resource-group $RESOURCE_GROUP --name $REDIS_NAME --query 'provisioningState' -o tsv)" != "Succeeded" ]; do
    sleep 30
    echo "  Still provisioning..."
done

REDIS_HOST=$(az redis show --resource-group $RESOURCE_GROUP --name $REDIS_NAME --query hostName -o tsv)
REDIS_KEY=$(az redis list-keys --resource-group $RESOURCE_GROUP --name $REDIS_NAME --query primaryKey -o tsv)
REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_HOST}:6380/0"

echo -e "${GREEN}✓ Redis Cache created: $REDIS_HOST${NC}"

# ============================================================================
# STEP 8: Create Storage Account
# ============================================================================
echo -e "\n${YELLOW}[Step 8/12] Creating Storage Account...${NC}"

STORAGE_NAME="${PREFIX}storage$(openssl rand -hex 4)"

az storage account create \
    --resource-group $RESOURCE_GROUP \
    --name $STORAGE_NAME \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2 \
    --output none

STORAGE_KEY=$(az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_NAME --query "[0].value" -o tsv)
STORAGE_CONNECTION="DefaultEndpointsProtocol=https;AccountName=${STORAGE_NAME};AccountKey=${STORAGE_KEY};EndpointSuffix=core.windows.net"

# Create containers
az storage container create --name documents --account-name $STORAGE_NAME --account-key $STORAGE_KEY --output none
az storage container create --name exports --account-name $STORAGE_NAME --account-key $STORAGE_KEY --output none

echo -e "${GREEN}✓ Storage Account created: $STORAGE_NAME${NC}"

# ============================================================================
# STEP 9: Build and Push Docker Images
# ============================================================================
echo -e "\n${YELLOW}[Step 9/12] Building and pushing Docker images...${NC}"

# Login to ACR
az acr login --name $ACR_NAME

# Get the script directory to find the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Build and push backend
echo "  Building backend image..."
docker build -t "$ACR_LOGIN_SERVER/tronas-api:latest" "$PROJECT_ROOT/backend"
docker push "$ACR_LOGIN_SERVER/tronas-api:latest"

# Build and push frontend
echo "  Building frontend image..."
docker build -t "$ACR_LOGIN_SERVER/tronas-frontend:latest" "$PROJECT_ROOT/frontend"
docker push "$ACR_LOGIN_SERVER/tronas-frontend:latest"

echo -e "${GREEN}✓ Docker images built and pushed${NC}"

# ============================================================================
# STEP 10: Deploy Backend API Container App
# ============================================================================
echo -e "\n${YELLOW}[Step 10/12] Deploying Backend API...${NC}"

# Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)

az containerapp create \
    --name "${PREFIX}-api" \
    --resource-group $RESOURCE_GROUP \
    --environment "${PREFIX}-env" \
    --image "$ACR_LOGIN_SERVER/tronas-api:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 5 \
    --cpu 0.5 \
    --memory 1Gi \
    --env-vars \
        "DATABASE_URL=$DATABASE_URL" \
        "REDIS_URL=$REDIS_URL" \
        "SECRET_KEY=$SECRET_KEY" \
        "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION" \
        "ENVIRONMENT=production" \
        "DEBUG=false" \
    --output none

API_URL=$(az containerapp show --name "${PREFIX}-api" --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)
echo -e "${GREEN}✓ Backend API deployed: https://$API_URL${NC}"

# ============================================================================
# STEP 11: Deploy Celery Worker Container App
# ============================================================================
echo -e "\n${YELLOW}[Step 11/12] Deploying Celery Worker...${NC}"

az containerapp create \
    --name "${PREFIX}-worker" \
    --resource-group $RESOURCE_GROUP \
    --environment "${PREFIX}-env" \
    --image "$ACR_LOGIN_SERVER/tronas-api:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 1 \
    --memory 2Gi \
    --command "celery" "-A" "app.worker" "worker" "-l" "info" \
    --env-vars \
        "DATABASE_URL=$DATABASE_URL" \
        "REDIS_URL=$REDIS_URL" \
        "SECRET_KEY=$SECRET_KEY" \
        "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION" \
    --output none

echo -e "${GREEN}✓ Celery Worker deployed${NC}"

# ============================================================================
# STEP 12: Deploy Frontend Container App
# ============================================================================
echo -e "\n${YELLOW}[Step 12/12] Deploying Frontend...${NC}"

az containerapp create \
    --name "${PREFIX}-frontend" \
    --resource-group $RESOURCE_GROUP \
    --environment "${PREFIX}-env" \
    --image "$ACR_LOGIN_SERVER/tronas-frontend:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 80 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 0.25 \
    --memory 0.5Gi \
    --env-vars \
        "VITE_API_URL=https://$API_URL" \
    --output none

FRONTEND_URL=$(az containerapp show --name "${PREFIX}-frontend" --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)
echo -e "${GREEN}✓ Frontend deployed: https://$FRONTEND_URL${NC}"

# ============================================================================
# DEPLOYMENT COMPLETE - SUMMARY
# ============================================================================
echo -e "\n${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOYMENT COMPLETE!                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}TRONAS PIA PLATFORM IS NOW LIVE!${NC}\n"

echo "═══════════════════════════════════════════════════════════════════════"
echo "                           ENDPOINTS"
echo "═══════════════════════════════════════════════════════════════════════"
echo -e "Frontend:     ${GREEN}https://$FRONTEND_URL${NC}"
echo -e "Backend API:  ${GREEN}https://$API_URL${NC}"
echo -e "API Docs:     ${GREEN}https://$API_URL/docs${NC}"
echo ""

echo "═══════════════════════════════════════════════════════════════════════"
echo "                      CUSTOM DOMAIN SETUP"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "To link tronas.ai to your deployment:"
echo ""
echo "1. Go to your DNS provider and add these records:"
echo ""
echo "   For tronas.ai (root domain):"
echo "   Type: CNAME or ALIAS"
echo "   Name: @"
echo "   Value: $FRONTEND_URL"
echo ""
echo "   For www.tronas.ai:"
echo "   Type: CNAME"
echo "   Name: www"
echo "   Value: $FRONTEND_URL"
echo ""
echo "   For api.tronas.ai:"
echo "   Type: CNAME"
echo "   Name: api"
echo "   Value: $API_URL"
echo ""
echo "2. After DNS propagates (5-30 minutes), add custom domains in Azure:"
echo ""
echo "   az containerapp hostname add \\"
echo "       --name ${PREFIX}-frontend \\"
echo "       --resource-group $RESOURCE_GROUP \\"
echo "       --hostname tronas.ai"
echo ""
echo "   az containerapp hostname add \\"
echo "       --name ${PREFIX}-frontend \\"
echo "       --resource-group $RESOURCE_GROUP \\"
echo "       --hostname www.tronas.ai"
echo ""
echo "   az containerapp hostname add \\"
echo "       --name ${PREFIX}-api \\"
echo "       --resource-group $RESOURCE_GROUP \\"
echo "       --hostname api.tronas.ai"
echo ""

echo "═══════════════════════════════════════════════════════════════════════"
echo "                      CREDENTIALS (SAVE THESE!)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "PostgreSQL:"
echo "  Host:     $POSTGRES_HOST"
echo "  Database: tronas"
echo "  Username: $POSTGRES_ADMIN"
echo "  Password: $POSTGRES_PASSWORD"
echo ""
echo "Redis:"
echo "  Host:     $REDIS_HOST"
echo "  Key:      $REDIS_KEY"
echo ""
echo "Storage Account:"
echo "  Name:     $STORAGE_NAME"
echo "  Key:      $STORAGE_KEY"
echo ""
echo "Container Registry:"
echo "  Server:   $ACR_LOGIN_SERVER"
echo "  Username: $ACR_USERNAME"
echo "  Password: $ACR_PASSWORD"
echo ""
echo "Secret Key: $SECRET_KEY"
echo ""

# Save credentials to file
CREDS_FILE="$PROJECT_ROOT/.azure-credentials"
cat > "$CREDS_FILE" << EOF
# TRONAS AZURE CREDENTIALS
# Generated: $(date)
# WARNING: Keep this file secure and never commit to git!

# Resource Group
RESOURCE_GROUP=$RESOURCE_GROUP
LOCATION=$LOCATION

# URLs
FRONTEND_URL=https://$FRONTEND_URL
API_URL=https://$API_URL

# PostgreSQL
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_DATABASE=tronas
POSTGRES_ADMIN=$POSTGRES_ADMIN
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=$DATABASE_URL

# Redis
REDIS_HOST=$REDIS_HOST
REDIS_KEY=$REDIS_KEY
REDIS_URL=$REDIS_URL

# Storage
STORAGE_NAME=$STORAGE_NAME
STORAGE_KEY=$STORAGE_KEY
STORAGE_CONNECTION=$STORAGE_CONNECTION

# Container Registry
ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER
ACR_USERNAME=$ACR_USERNAME
ACR_PASSWORD=$ACR_PASSWORD

# Application
SECRET_KEY=$SECRET_KEY
EOF

echo -e "${YELLOW}Credentials saved to: $CREDS_FILE${NC}"
echo -e "${RED}IMPORTANT: Add .azure-credentials to .gitignore!${NC}"
echo ""

echo "═══════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}Deployment successful! Your Tronas platform is now live.${NC}"
echo "═══════════════════════════════════════════════════════════════════════"
