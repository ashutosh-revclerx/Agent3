# PostgreSQL Terminal Guide

This guide explains how to check and interact with your PostgreSQL database using the terminal, especially when running in Docker.

---

## 1. Open a psql Shell in the Docker Container

```bash
docker-compose exec postgres psql -U copilot_user -d copilot_db
```
- `postgres` is the service name from your docker-compose.yml
- `copilot_user` is the database user
- `copilot_db` is the database name

---

## 2. List All Tables

```sql
\dt
```

---

## 3. View Table Data

Example: View all sessions
```sql
SELECT * FROM sessions;
```

Example: View company DNA (limit to 5 rows)
```sql
SELECT company_name, confidence, expires_at FROM company_dna LIMIT 5;
```

---

## 4. Describe a Table (Show Columns)

```sql
\d+ participants
```

---

## 5. Run Custom Queries

Example: Show all active participants
```sql
SELECT name, role, confidence, source FROM participants WHERE is_active = TRUE;
```

---

## 6. Exit the psql Shell

```sql
\q
```

---

## 7. Reset or Clean Database (Dangerous!)

Truncate all data (keep schema):
```bash
docker-compose exec postgres psql -U copilot_user -d copilot_db -c "TRUNCATE sessions, company_dna, participants, participant_extras, phase_data CASCADE;"
```

---

## 8. Troubleshooting

- **Connection refused?**
  - Make sure the container is running: `docker-compose ps`
  - Check credentials in `.env` and `docker-compose.yml`
- **Schema not found?**
  - The `init_db.sql` script runs only on first container creation. To re-apply:
    ```bash
    docker-compose down -v
    docker-compose up postgres
    ```
- **psql not found?**
  - Always run `psql` inside the container using `docker-compose exec` as above.

---

## 9. Useful psql Shortcuts

- `\l` — List all databases
- `\c dbname` — Connect to a database
- `\dt` — List tables
- `\d tablename` — Describe table
- `\x` — Toggle expanded output
- `\q` — Quit

---

For more, see the official [PostgreSQL psql documentation](https://www.postgresql.org/docs/current/app-psql.html).
