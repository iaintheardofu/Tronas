#!/bin/bash
# ============================================================================
# TRONAS PIA PLATFORM - RAILWAY DEPLOYMENT
# ============================================================================
# This script helps deploy Tronas to Railway with PostgreSQL and Redis
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                   TRONAS PIA PLATFORM - RAILWAY                       ║"
echo "║                      Quick Deploy Script                              ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for Railway CLI
if ! command -v railway &> /dev/null; then
    echo -e "${YELLOW}Installing Railway CLI...${NC}"
    npm install -g @railway/cli
fi

# Login to Railway
echo -e "\n${YELLOW}[Step 1/5] Logging in to Railway...${NC}"
railway login

# Create new project
echo -e "\n${YELLOW}[Step 2/5] Creating Railway project...${NC}"
railway init --name tronas-pia

# Add PostgreSQL
echo -e "\n${YELLOW}[Step 3/5] Adding PostgreSQL database...${NC}"
railway add --database postgres

# Add Redis
echo -e "\n${YELLOW}[Step 4/5] Adding Redis cache...${NC}"
railway add --database redis

# Set environment variables
echo -e "\n${YELLOW}[Step 5/5] Configuring environment...${NC}"
echo "Please enter your OpenAI API key:"
read -s OPENAI_KEY

railway variables set \
    ENVIRONMENT=production \
    DEBUG=false \
    SECRET_KEY=$(openssl rand -hex 32) \
    OPENAI_API_KEY="$OPENAI_KEY"

# Deploy
echo -e "\n${YELLOW}Deploying to Railway...${NC}"
railway up

# Get URLs
echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOYMENT COMPLETE!                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Your Tronas platform is deploying!"
echo ""
echo "Next steps:"
echo "1. Go to https://railway.app/dashboard"
echo "2. Click on your tronas-pia project"
echo "3. Go to Settings → Domains"
echo "4. Add custom domain: tronas.ai"
echo "5. Add the CNAME record to your DNS"
echo ""
