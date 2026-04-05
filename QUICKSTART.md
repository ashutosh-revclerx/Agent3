# 🚀 Quick Start — Sprint 1 PostgreSQL Setup

## 5-Minute Setup

### Step 1: Start PostgreSQL

```bash
docker-compose up -d postgres
```

Wait for health check:
```bash
docker-compose ps  # Should show "healthy"
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY and NEXUS_API_KEY
```

### Step 4: Run Backend

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
✅ Database connection pool initialized
Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Test It

```bash
# Create a session
curl -X POST http://localhost:8000/session/create \
  -H "Content-Type: application/json" \
  -d '{
    "host_name": "Test Host",
    "company": "TestCorp",
    "industry": "Technology",
    "participant_count": 5,
    "company_url": "https://www.google.com"
  }'

# Copy the session code from response and check database:
docker-compose exec postgres psql -U copilot_user -d copilot_db -c "SELECT code, company FROM sessions;"
```

## What Just Happened?

✅ PostgreSQL running in Docker
✅ Database schema initialized (5 tables with TTL)
✅ FastAPI backend connected to DB
✅ Scraping Agent ready to extract company DNA
✅ Session created and stored persistently

## Next: Test Scraping

1. Wait ~10 seconds for company scrape to complete (async background task)
2. Check for company_dna:
   ```bash
   docker-compose exec postgres psql -U copilot_user -d copilot_db -c \
     "SELECT company_name, confidence, expires_at FROM company_dna LIMIT 1;"
   ```

3. Verify WebSocket broadcast received at frontend

## Architecture Overview

```
Frontend (React)  ←→  FastAPI Backend  ←→  PostgreSQL DB
                       ↓
                  Nexus API (Scraping)
                  Gemini (Extraction)
                  Pydantic (Validation)
```

## Stopping Services

```bash
# Stop database
docker-compose down

# Stop and delete all data
docker-compose down -v
```

## Troubleshooting

- **DB won't start?** → `docker-compose up postgres` and wait for health check
- **Connection refused?** → Check `.env` credentials match `docker-compose.yml`
- **Backend not connecting?** → Ensure DB is `healthy`, then restart backend

## Full Documentation

See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for complete guide with schema details, testing, and troubleshooting.
