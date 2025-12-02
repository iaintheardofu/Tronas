# Tronas PIA Platform - Deployment Guide

## Quick Deploy Options

Choose the platform that works best for you:

| Platform | Complexity | Cost/mo | Best For |
|----------|-----------|---------|----------|
| Railway | ⭐ Easy | $20-50 | Quick deployment |
| Render | ⭐ Easy | $25-60 | Free tier available |
| Fly.io | ⭐⭐ Medium | $30-60 | Global edge network |
| DigitalOcean | ⭐⭐ Medium | $40-80 | Full control |
| Vercel + Railway | ⭐⭐ Medium | $20-40 | Best frontend perf |

---

## Option 1: Railway (Recommended)

Railway is the fastest way to deploy. No complex CLI setup required.

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended)

### Step 2: Deploy from GitHub
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose `iaintheardofu/Tronas`
4. Railway will auto-detect the Dockerfile

### Step 3: Add Services
Click "New" → "Database" and add:
- **PostgreSQL** - Select PostgreSQL
- **Redis** - Select Redis

### Step 4: Configure Environment Variables
Click on your API service → Variables → Add:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<generate-random-64-char-string>
OPENAI_API_KEY=<your-openai-key>
ENVIRONMENT=production
DEBUG=false
```

### Step 5: Add Custom Domain
1. Go to Settings → Domains
2. Add `api.tronas.ai` for the API
3. Add `tronas.ai` for the frontend
4. Copy the CNAME value to your DNS provider

---

## Option 2: Render

Render offers a free tier and easy deployment.

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub

### Step 2: Deploy with Blueprint
1. Click "New" → "Blueprint"
2. Connect your GitHub repo
3. Select `render.yaml` as the blueprint
4. Render will create all services automatically

### Step 3: Add Secrets
Go to each service and add:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - Generate a random 64-character string

### Step 4: Custom Domain
1. Go to your frontend service → Settings → Custom Domains
2. Add `tronas.ai`
3. Add the DNS records shown

---

## Option 3: Fly.io

Fly.io offers a global edge network.

### Step 1: Install Fly CLI
```bash
# macOS
brew install flyctl

# Or direct install
curl -L https://fly.io/install.sh | sh
```

### Step 2: Login and Launch
```bash
fly auth login
fly launch --no-deploy
```

### Step 3: Create PostgreSQL
```bash
fly postgres create --name tronas-db
fly postgres attach tronas-db
```

### Step 4: Create Redis
```bash
fly redis create --name tronas-redis
```

### Step 5: Set Secrets
```bash
fly secrets set \
  OPENAI_API_KEY="your-key" \
  SECRET_KEY="$(openssl rand -hex 32)" \
  REDIS_URL="your-redis-url"
```

### Step 6: Deploy
```bash
fly deploy
```

### Step 7: Custom Domain
```bash
fly certs create tronas.ai
fly certs create api.tronas.ai
```

---

## Option 4: Vercel (Frontend) + Railway (Backend)

Best performance for the React frontend.

### Frontend on Vercel
1. Go to [vercel.com](https://vercel.com)
2. Import from GitHub
3. Set root directory to `frontend`
4. Add environment variable:
   - `VITE_API_URL` = Your Railway API URL

### Backend on Railway
Follow the Railway instructions above, but only deploy the backend.

---

## DNS Configuration for tronas.ai

After deployment, add these DNS records:

| Type | Name | Value |
|------|------|-------|
| CNAME | @ | Your frontend URL from platform |
| CNAME | www | Your frontend URL from platform |
| CNAME | api | Your API URL from platform |

**Note:** Some DNS providers don't support CNAME on root (@). Use ALIAS or A record instead.

---

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| REDIS_URL | Redis connection string | Yes |
| SECRET_KEY | JWT signing key (64 chars) | Yes |
| OPENAI_API_KEY | OpenAI API key for classification | Yes |
| ENVIRONMENT | `production` or `development` | Yes |
| DEBUG | `false` for production | Yes |
| AZURE_AD_CLIENT_ID | Microsoft 365 integration | Optional |
| AZURE_AD_CLIENT_SECRET | Microsoft 365 integration | Optional |
| AZURE_AD_TENANT_ID | Microsoft 365 integration | Optional |

---

## Post-Deployment Checklist

- [ ] Verify API health: `https://api.tronas.ai/health`
- [ ] Verify frontend loads: `https://tronas.ai`
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Create admin user
- [ ] Test login flow
- [ ] Test document upload
- [ ] Configure Microsoft 365 integration (if needed)

---

## Troubleshooting

### Database Connection Issues
- Ensure DATABASE_URL uses `postgresql://` not `postgres://`
- Check if SSL is required: add `?sslmode=require` to URL

### Redis Connection Issues
- Use `rediss://` (with double s) for SSL connections
- Check firewall/IP allowlist settings

### Frontend Can't Reach API
- Verify CORS settings in backend
- Check VITE_API_URL is set correctly
- Ensure API is deployed and healthy

---

## Support

For deployment help:
- Railway: [docs.railway.app](https://docs.railway.app)
- Render: [render.com/docs](https://render.com/docs)
- Fly.io: [fly.io/docs](https://fly.io/docs)

For Tronas platform issues:
- GitHub: https://github.com/iaintheardofu/Tronas/issues
- Contact: https://www.tronas.ai
