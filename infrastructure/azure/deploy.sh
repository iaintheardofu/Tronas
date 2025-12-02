#!/bin/bash
# Tronas PIA Platform - Azure Deployment Script
# Usage: ./deploy.sh <environment> [resource-group]

set -e

# Configuration
ENVIRONMENT=${1:-prod}
RESOURCE_GROUP=${2:-tronas-${ENVIRONMENT}-rg}
LOCATION=${LOCATION:-southcentralus}

echo "======================================"
echo "Tronas PIA Platform - Azure Deployment"
echo "======================================"
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""

# Check for Azure CLI
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed"
    exit 1
fi

# Check login status
if ! az account show &> /dev/null; then
    echo "Please log in to Azure..."
    az login
fi

# Get current subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
echo "Using subscription: $SUBSCRIPTION"
echo ""

# Create resource group if it doesn't exist
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION --output none

# Prompt for secrets if not set
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Enter PostgreSQL admin password:"
    read -s POSTGRES_PASSWORD
fi

if [ -z "$REDIS_PASSWORD" ]; then
    echo "Enter Redis password:"
    read -s REDIS_PASSWORD
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Enter OpenAI API key:"
    read -s OPENAI_API_KEY
fi

# Optional Azure AD credentials
if [ -z "$AZURE_AD_CLIENT_ID" ]; then
    AZURE_AD_CLIENT_ID=""
fi

if [ -z "$AZURE_AD_CLIENT_SECRET" ]; then
    AZURE_AD_CLIENT_SECRET=""
fi

# Optional Form Recognizer credentials
if [ -z "$FORM_RECOGNIZER_ENDPOINT" ]; then
    FORM_RECOGNIZER_ENDPOINT=""
fi

if [ -z "$FORM_RECOGNIZER_KEY" ]; then
    FORM_RECOGNIZER_KEY=""
fi

echo ""
echo "Deploying infrastructure..."

# Deploy Bicep template
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters \
        environmentName=$ENVIRONMENT \
        postgresPassword="$POSTGRES_PASSWORD" \
        redisPassword="$REDIS_PASSWORD" \
        openAiApiKey="$OPENAI_API_KEY" \
        azureAdClientId="$AZURE_AD_CLIENT_ID" \
        azureAdClientSecret="$AZURE_AD_CLIENT_SECRET" \
        formRecognizerEndpoint="$FORM_RECOGNIZER_ENDPOINT" \
        formRecognizerKey="$FORM_RECOGNIZER_KEY" \
    --output table

# Get outputs
echo ""
echo "======================================"
echo "Deployment Outputs"
echo "======================================"

ACR_SERVER=$(az deployment group show -g $RESOURCE_GROUP -n main --query properties.outputs.acrLoginServer.value -o tsv)
BACKEND_URL=$(az deployment group show -g $RESOURCE_GROUP -n main --query properties.outputs.backendUrl.value -o tsv)
FRONTEND_URL=$(az deployment group show -g $RESOURCE_GROUP -n main --query properties.outputs.frontendUrl.value -o tsv)

echo "Container Registry: $ACR_SERVER"
echo "Backend API URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"

echo ""
echo "======================================"
echo "Next Steps"
echo "======================================"
echo "1. Log in to ACR: az acr login --name ${ACR_SERVER%%.*}"
echo "2. Build and push images:"
echo "   docker build -t $ACR_SERVER/tronas-api:latest ./backend"
echo "   docker build -t $ACR_SERVER/tronas-frontend:latest ./frontend"
echo "   docker push $ACR_SERVER/tronas-api:latest"
echo "   docker push $ACR_SERVER/tronas-frontend:latest"
echo "3. Configure custom domain DNS for tronas.ai"
echo ""
echo "Deployment complete!"
