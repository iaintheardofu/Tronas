# Supabase Setup for Tronas PIA Platform

## Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Sign in with GitHub
3. Click "New Project"
4. Enter:
   - **Name:** tronas-pia
   - **Database Password:** (save this!)
   - **Region:** Central US (Iowa) - closest to San Antonio
5. Click "Create new project"

## Step 2: Get Connection String

1. Go to Project Settings → Database
2. Copy the **Connection string (URI)**
3. Replace `[YOUR-PASSWORD]` with your database password

Your connection string will look like:
```
postgresql://postgres.[project-ref]:[password]@aws-0-us-central-1.pooler.supabase.com:6543/postgres
```

## Step 3: Configure for Async Python

For SQLAlchemy async, modify the connection string:
- Change `postgresql://` to `postgresql+asyncpg://`
- Add `?sslmode=require` at the end

Final format:
```
postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-us-central-1.pooler.supabase.com:6543/postgres?sslmode=require
```
