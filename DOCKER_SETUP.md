# Docker & Database Setup Guide

## Sprint 1 — PostgreSQL Integration

This guide covers setting up and running the PostgreSQL database with Docker for the AI Consulting Copilot.

### Prerequisites

- Docker & Docker Compose installed ([Download](https://www.docker.com/products/docker-desktop))
- Python 3.9+
- Git

### Quick Start

#### 1. Environment Configuration

Copy the example environment file:

```bash
cp backend/.env.example backend/.env
```

Update `backend/.env` with your API keys if needed:

```
GEMINI_API_KEY=your_key_here
NEXUS_API_KEY=your_nexus_key_here
DB_USER=copilot_user
DB_PASSWORD=copilot_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=copilot_db
```

#### 2. Start PostgreSQL with Docker

```bash
docker-compose up -d postgres
```

This will:
- Pull the PostgreSQL 16-Alpine image
- Create a container named `copilot-postgres`
- Initialize the database schema from `init_db.sql`
- Listen on `localhost:5432`

Verify the container is healthy:

```bash
docker-compose ps
```

Expected output:
```
NAME               STATUS              PORTS
copilot-postgres   Up (healthy)        5432/tcp
```

#### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `asyncpg==0.29.0` — PostgreSQL async driver
- `websockets` — For WebSocket support
- `requests` — For weather/sports API calls

#### 4. Run the Backend

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Database Schema Overview

#### Tables Created:

1. **sessions** — Session metadata and workshop data
   - TTL: No expiration (persistent across sessions)
   - Triggers: Auto-update `updated_at` timestamp

2. **company_dna** — Extracted company information
   - TTL: 30 days (can be refreshed manually by host)
   - Confidence flags: `complete`, `partial`, `fallback`
   - Indexed by: session_id, expires_at, company_name

3. **participants** — Participant profiles (confirmed fields only)
   - TTL: 7 days (shorter than company data for privacy)
   - Confidence flags: `complete`, `partial`, `fallback`
   - Source: `linkedin` or `manual` (self-entry)
   - Indexed by: session_id, expires_at

4. **participant_extras** — Fun facts and local context
   - Linked 1:1 with participants table
   - Stores: fun_fact (text), local_context (JSON)

5. **phase_data** — All phase submissions
   - Supports flexible phase_key naming
   - Indexed by: session_id, phase_key

### Key Architecture Decisions

#### Memory vs. Persistence

- **In-Memory Cache** (`sessions`, `participants` dicts in main.py)
  - Used for real-time agent logic and WebSocket broadcasting
  - Loaded from DB on session retrieval
  - Lost if server restarts (acceptable for 2-hour sessions)

- **PostgreSQL Persistence**
  - Company DNA (30-day TTL)
  - Participant profiles (7-day TTL)
  - All phase submissions
  - Session metadata

#### Confidence Flags

Every extraction now includes a confidence level:

- **complete**: Key fields successfully extracted (4+ of 5)
- **partial**: Some fields extracted (2-3 of 5)
- **fallback**: Minimal extraction (<2 fields) — triggers manual entry form

#### TTL (Time-To-Live) Enforcement

- Scraping Agent automatically sets `expires_at` timestamp
- Database queries filter to `expires_at > NOW()` to exclude stale data
- Host can manually trigger re-scrape via `/session/{code}/dna` endpoint

### Common Commands

#### View Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U copilot_user -d copilot_db

# List tables
\dt

# View sessions
SELECT code, company, industry, created_at FROM sessions;

# View participants
SELECT name, role, confidence, source FROM participants WHERE is_active = TRUE;

# Exit
\q
```

#### Reset Database

```bash
# Delete all data (keep schema)
docker-compose exec postgres psql -U copilot_user -d copilot_db -c "TRUNCATE sessions CASCADE;"

# Or recreate entirely
docker-compose down -v
docker-compose up postgres
```

#### View Logs

```bash
docker-compose logs -f postgres
docker-compose logs -f  # all services
```

#### Stop Services

```bash
docker-compose down  # stop containers, keep volumes
docker-compose down -v  # stop and delete data
```

### Testing the Pipeline

#### 1. Create a Session (with company URL)

```bash
curl -X POST http://localhost:8000/session/create \
  -H "Content-Type: application/json" \
  -d '{
    "host_name": "Alice",
    "company": "TechCorp",
    "industry": "Technology",
    "participant_count": 5,
    "duration_mins": 90,
    "company_url": "https://www.example.com"
  }'
```

Response:
```json
{
  "code": "ABC123",
  "id": "uuid...",
  "company_dna": {
    "company_name": "Example Inc.",
    "vision": "...",
    "confidence": "complete",
    "scraped_at": "2026-04-04T..."
  }
}
```

#### 2. Retrieve Session

```bash
curl http://localhost:8000/session/ABC123
```

#### 3. Join a Participant

```bash
curl -X POST http://localhost:8000/participant/join \
  -H "Content-Type: application/json" \
  -d '{
    "session_code": "ABC123",
    "name": "Bob",
    "role": "Engineering Lead",
    "department": "Engineering",
    "top_challenge": "Scaling infrastructure",
    "daily_work": "Reviewing PRs, mentoring",
    "ai_confidence": 3,
    "linkedin_url": "https://www.linkedin.com/in/bob/"
  }'
```

#### 4. Wait for Background Scrape

The scraping happens asynchronously. Monitor WebSocket or check DB:

```bash
docker-compose exec postgres psql -U copilot_user -d copilot_db << 'EOF'
SELECT p.name, p.confidence, pe.fun_fact, pe.local_context
FROM participants p
LEFT JOIN participant_extras pe ON p.id = pe.participant_id
WHERE p.is_active = TRUE;
EOF
```

### Troubleshooting

#### **Connection Refused on `localhost:5432`**

Ensure PostgreSQL container is running:

```bash
docker-compose ps postgres
```

If not, start it:

```bash
docker-compose up -d postgres
docker-compose exec postgres pg_isready -U copilot_user -d copilot_db
```

#### **Schema Not Applied**

The `init_db.sql` script runs automatically only on the first container creation. To re-apply:

```bash
docker-compose down -v
docker-compose up postgres
```

Or manually:

```bash
docker-compose exec postgres psql -U copilot_user -d copilot_db < backend/init_db.sql
```

#### **asyncpg.exceptions.CannotConnectNowError**

Backend can't connect to database. Check:

1. Database is running: `docker-compose ps`
2. Credentials in `.env` match `docker-compose.yml`
3. Network is correct: `docker-compose exec postgres psql -U copilot_user`

#### **Stale Data Not Filtered**

Ensure queries use `expires_at > NOW()` condition. Example query:

```sql
SELECT * FROM company_dna
WHERE session_id = $1
AND is_active = TRUE
AND expires_at > NOW()
ORDER BY created_at DESC
LIMIT 1;
```

### Next Steps (Deferred to Later Sprints)

- **Redis Caching** — Session context cache (TTL-based expiration)
- **Kubernetes Support** — Multi-pod PostgreSQL replication
- **Backup & Restore** — Automated DB backups to S3
- **Vector Store** — pgvector for semantic search on company docs

### Architecture Diagram

```
┌─────────────────┐
│  FastAPI Server │
│  ┌─────────────┐│
│  │ Sessions     ││ (in-memory cache)
│  │ Participants ││
│  └─────────────┘│
│        ↕        │
├─────────────────┤
│  PostgreSQL DB  │
│  ┌─────────────┐│
│  │ company_dna ││ (30-day TTL)
│  │ participants││ (7-day TTL)
│  │ phase_data   ││ (persistent)
│  │ sessions     ││ (persistent)
│  └─────────────┘│
└────────────────┘
   (via asyncpg)
```

---

**Questions?** Check the main development guide or the Sprint 1 plan in `backend/agents/plan.md`.
